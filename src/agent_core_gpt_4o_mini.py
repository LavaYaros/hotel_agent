import os, json, openai, psycopg2, psycopg2.extras
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from pgvector import Vector

from db_helper import db_creds


load_dotenv()

openai.api_key = os.getenv("AI_API_KEY")

def find_rooms(*, user_text: str,
               beds: int | None = None,
               pool_required: bool | None = None,
               kitchen_required: bool | None = None,
               wifi_required: bool | None = None,
               min_price: float | None = None,
               max_price: float | None = None,
               top_k: int = 5):
    """
    Search rooms by embedding similarity + optional hard filters.
    Returns a list of dicts ready for JSON.
    """
    # embed the guest’s text
    vec = openai.embeddings.create(
        model="text-embedding-3-small",
        input=user_text
    ).data[0].embedding

    # build WHERE clause
    conds, params = [], []
    if beds is not None:
        conds.append("beds = %s");             params.append(beds)
    if pool_required is not None:
        conds.append("access_to_pool = %s");   params.append(pool_required)
    if kitchen_required is not None:
        conds.append("kitchen = %s");           params.append(kitchen_required)
    if wifi_required is not None:
        conds.append("free_wifi = %s");               params.append(wifi_required)
    if min_price is not None:
        conds.append("price_per_day >= %s");           params.append(min_price)
    if max_price is not None:
        conds.append("price_per_day <= %s");           params.append(max_price)

    where_sql = " AND ".join(conds) or "TRUE"

    sql = f"""
    SELECT id, room_type, price_per_day, beds, access_to_pool, kitchen, free_wifi,
           description,
           embedding <=> %s AS dist          -- cosine distance
    FROM   rooms
    WHERE  {where_sql}
    ORDER  BY embedding <=> %s
    LIMIT  {top_k};
    """

    # query the rooms
    vec_pg = Vector(vec) 
    with psycopg2.connect(**db_creds) as conn:
        register_vector(conn)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, [vec_pg] + params + [vec_pg])
            return cur.fetchall()      # list[RealDictRow] → behaves like dict

# quick sanity-check
if __name__ == "__main__":
    rooms = find_rooms(user_text="cozy room with pool access around 70$", pool_required=True, max_price=70)
    print(json.dumps(rooms, indent=2, ensure_ascii=False, default=str))
