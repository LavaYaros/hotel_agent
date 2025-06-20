import random, textwrap, time
import psycopg2, openai
import os
from dotenv import load_dotenv

from db_helper import db_creds 


load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

SYS_PROMPT = (
    "You are a copywriter for a hotel website. "
    "Write a believable, warm-tone room description (max 80 words). "
    "If 'mention_pool' is 'yes', add one short sentence about the guest’s access to the pool and why this is a plus (e.g., perfect for a refreshing morning swim). "
    "If 'mention_pool' is 'no', add one short sentence noting there is no pool access and why that’s good (e.g., extra privacy and quiet). "
    "If 'mention_pool' is 'none', do not mention the pool at all. "
    "Do not invent amenities that are not provided."
)

def describe(row, mention_pool: str) -> str:
    _, rtype, area, beds, wifi, kitchen, bar = row

    extras = [
        ("room_area_sq_m", area),
        ("beds", beds),
        ("free_wifi", wifi),
        ("kitchen", kitchen),
        ("mini_bar", bar),
    ]
    random.shuffle(extras)
    extras = extras[:2]

    lines = [f"room_type: {rtype}"]
    for k, v in extras:
        lines.append(f"{k}: {v}")
    lines.append(f"mention_pool: {mention_pool}")

    user_prompt = "\n".join(lines) + "\n\n→ description:"

    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=120,
    )
    return resp.choices[0].message.content.strip()

conn = psycopg2.connect(**db_creds)
cur  = conn.cursor()
cur.execute("""
    SELECT id, room_type, room_area_sq_m, beds,
           free_wifi, kitchen, mini_bar
    FROM rooms;
""")
rows = cur.fetchall()

for row in rows:
    rid = row[0]
    r   = random.random()
    if r < 0.40:
        pool_flag, pool_state = "none", 0     # no mention
    elif r < 0.55:
        pool_flag, pool_state = "no",   2     # mentions no access
    else:
        pool_flag, pool_state = "yes",  1     # mentions access

    desc = describe(row, pool_flag)
    cur.execute(
        "UPDATE rooms SET description = %s, pool_state = %s WHERE id = %s;",
        (desc, pool_state, rid)
    )
    time.sleep(0.3)

conn.commit()
cur.close(); conn.close()
print("Done ✔")


