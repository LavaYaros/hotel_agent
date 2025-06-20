import psycopg2
import sys
from pathlib import Path
from dotenv import load_dotenv
import os


load_dotenv()

db_creds = {
    "dbname":   os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host":     os.getenv("DB_HOST"),
    "port":     int(os.getenv("DB_PORT", 5432)),
}


def main(out_path: str = "rooms_dump.csv") -> None:
    out_file = Path(out_path).expanduser().resolve()

    conn = psycopg2.connect(
        **db_creds
    )

    with conn, conn.cursor() as cur, open(out_file, "w", newline="") as fh:
        cur.copy_expert(
            "COPY rooms TO STDOUT WITH (FORMAT CSV, HEADER TRUE)", fh
        )

    print(f"✅  Table exported → {out_file}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "rooms_dump.csv")

