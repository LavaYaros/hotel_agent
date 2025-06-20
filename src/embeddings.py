from sentence_transformers import SentenceTransformer
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extras import execute_values
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

from db_helper import db_creds


def embed_openai_3_small(texts):            # texts ≤ 8k tokens total
    client = OpenAI(api_key=os.getenv("AI_API_KEY"))
    return [e.embedding for e in client.embeddings.create(
        model="text-embedding-3-small", input=texts).data]


def embed_sentence_transformer(texts):
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")   # 384-D
    model = model.to("cpu")   
    return [v.tolist() for v in model.encode(texts, normalize_embeddings=True)]


def update_description_embeddings(embed) -> None:
    """Update embeddings for room descriptions."""

    conn = psycopg2.connect(**db_creds)
    cur  = conn.cursor()

    cur.execute("SELECT id, description FROM rooms WHERE embedding IS NULL")
    rows = cur.fetchall()

    BATCH = 100
    for i in range(0, len(rows), BATCH):
        ids, descs = zip(*rows[i:i+BATCH])
        vecs = embed(descs)
        cur.executemany(
            "UPDATE rooms SET embedding = %s WHERE id = %s",
            list(zip(vecs, ids))
        )
    conn.commit()
    cur.close(); conn.close()
    print("✅ embeddings stored")


pos_phrases = [
    "room includes access to the pool",
    "unlimited pool access",
    "guests may use the swimming pool",
    "unlimited access to hotel pool",
    "feel free to enjoy the pool",
    "room comes with pool privileges"
]


def update_pool_proto_pos(embed_fn, nd) -> None:
    """Refresh pool_proto with batched embeddings."""
    vecs = embed_fn(pos_phrases)
    rows = [(v,) for v in vecs]

    with psycopg2.connect(**db_creds) as conn, conn.cursor() as cur:
        register_vector(conn)
        cur.execute(f"CREATE TABLE IF NOT EXISTS pool_proto (vec vector({nd}));")
        cur.execute("TRUNCATE pool_proto;")
        execute_values(cur, "INSERT INTO pool_proto (vec) VALUES %s", rows)
    print("✅ pool_proto updated")



neg_phrases = [
    "without a pool",
    "pool is unavailable",
    "no swimming pool",
    "this room has no pool access",
    "guests cannot use the pool"
]


def update_pool_proto_neg(embed_fn, nd) -> None:
    """Refresh pool_proto_neg with batched embeddings."""
    vecs = embed_fn(neg_phrases)
    rows = [(v,) for v in vecs]

    with psycopg2.connect(**db_creds) as conn, conn.cursor() as cur:
        register_vector(conn)
        cur.execute(f"CREATE TABLE IF NOT EXISTS pool_proto_neg (vec vector({nd}));")
        cur.execute("TRUNCATE pool_proto_neg;")
        execute_values(cur,
            "INSERT INTO pool_proto_neg (vec) VALUES %s", rows)
    
    print("✅ pool_proto_neg updated")


nd = 1536  # 1536 OpenAI 3 Small, or 384 SentenceTransformer all-MiniLM-L6-v2
m = embed_openai_3_small # or embed_sentence_transformer


def redefine_embedding_columns(nd):
    """Recreate embedding columns with vector type."""
    with psycopg2.connect(**db_creds) as conn, conn.cursor() as cur:
        cur.execute("ALTER TABLE rooms DROP COLUMN IF EXISTS embedding;")
        cur.execute(f"ALTER TABLE rooms ADD COLUMN embedding vector({nd});")
        cur.execute("DROP TABLE IF EXISTS pool_proto, pool_proto_neg;")
        cur.execute(f"CREATE TABLE pool_proto (vec vector({nd}));")
        cur.execute(f"CREATE TABLE pool_proto_neg (vec vector({nd}));")
        register_vector(conn)
        print("✅ embedding column recreated.")
    
        
if __name__ == "__main__":
    redefine_embedding_columns(nd)
    update_description_embeddings(m)
    update_pool_proto_pos(m, nd)
    update_pool_proto_neg(m, nd)
