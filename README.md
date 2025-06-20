## Quick start

```bash
# 1. Start fresh DB with sample data
docker compose down -v       # remove old volume
docker compose up -d         # restores hotel.dump

# 2. Set up Python env
python -m venv .venv
.\.venv\Scripts\activate      # Windows 11
pip install -r requirements.txt

# 3. Run a demo script
python src\main.py
