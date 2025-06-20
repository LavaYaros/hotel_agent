import random, psycopg2

from db_helper import db_creds

# ---------- 1. Connect ----------
conn = psycopg2.connect(**db_creds)
cur = conn.cursor()

# ---------- 2. Create table ----------
cur.execute("""
CREATE TABLE IF NOT EXISTS rooms (
    id              SERIAL PRIMARY KEY,
    room_type       TEXT,
    room_area_sq_m  REAL,
    beds            SMALLINT,
    free_wifi       BOOLEAN,
    kitchen         BOOLEAN,
    mini_bar        BOOLEAN,
    description     TEXT,
    access_to_pool  BOOLEAN
);
""")

# ---------- 3. Generate sample data ----------
specs = {
    "Single":       {"area": (12, 18), "beds": [1]},
    "Double":       {"area": (18, 25), "beds": [1, 2]},
    "Queen":        {"area": (22, 30), "beds": [1]},
    "King":         {"area": (25, 35), "beds": [1]},
    "Triple / Quad":{"area": (30, 42), "beds": [3, 4]},
    "Studio":       {"area": (28, 38), "beds": [1, 2]},
    "Suite":        {"area": (40, 70), "beds": [1, 2]},
    "Connecting":   {"area": (40, 55), "beds": [2, 3, 4]},
    "Apartment":    {"area": (60,120), "beds": [2, 3, 4, 5, 6]},
}

rows = []
for _ in range(70):
    rt = random.choice(list(specs))
    area = round(random.uniform(*specs[rt]["area"]), 1)
    beds = random.choice(specs[rt]["beds"])
    free_wifi = random.random() < 0.9          # 90 % offer Wi-Fi
    kitchen   = rt in {"Studio", "Suite", "Apartment"}
    mini_bar  = random.random() < 0.7          # 70 % have mini-bar
    rows.append((rt, area, beds, free_wifi, kitchen, mini_bar, "", None))

# ---------- 4. Insert ----------
cur.executemany("""
INSERT INTO rooms
    (room_type, room_area_sq_m, beds, free_wifi, kitchen, mini_bar, description, access_to_pool)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s);
""", rows)

conn.commit()
cur.close()
conn.close()
