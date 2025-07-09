import os, json, psycopg2, openai
from typing import List, Dict
from langchain.tools import Tool
from db_helper import db_creds
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

load_dotenv()
openai.api_key = os.getenv("AI_API_KEY")
DB_URL = "postgresql://" + \
          f"{db_creds['user']}:{db_creds['password']}@" + \
          f"{db_creds['host']}:{db_creds['port']}/{db_creds['dbname']}"

def recommend_rooms(
        preferences: str,
        *, top_k: int = 3
    ) -> List[Dict]:
    """
    Embed the guest text with OpenAI then pgvector <=> search.
    Returns [{'id':..,'room_type':..,'price_per_day':..,'short_description':..}, …]
    """

    # embed once on the client
    vec = openai.embeddings.create(
        model="text-embedding-3-small",
        input=preferences
    ).data[0].embedding                     # list[float] length 1536

    # query Postgres
    sql = """
    SELECT id,
           room_type,
           price_per_day,
           LEFT(description, 120)      AS short_description,
           room_area_sq_m AS area,
           beds,
           free_wifi,
           kitchen,
           mini_bar,
           access_to_pool
    FROM   rooms
    ORDER  BY embedding <=> %s::vector      -- pgvector cosine distance
    LIMIT  %s;
    """
    with psycopg2.connect(DB_URL) as conn, conn.cursor() as cur:
        cur.execute(sql, (vec, top_k))
        rows = cur.fetchall()

    return [
        dict(zip(
            ("id", "room_type", "price_per_day", "short_description",
             "area", "beds", "free_wifi", "kitchen", "mini_bar",
             "access_to_pool"),
            row
        )) for row in rows
    ]

recommend_tool = Tool(
    name="recommend_room",
    func=recommend_rooms,
    description="Input: guest preferences text. Output: top 3 matching rooms."
)
