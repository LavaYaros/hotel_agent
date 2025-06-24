## Quick start

```bash
# 0. Clone and add secrets
git clone https://github.com/<you>/hotel_agent.git
cd hotel_agent
copy .env.example .env         # fill DB_USER, DB_PASSWORD, OPENAI_API_KEY, …

# 1. Bring up PostgreSQL with sample data
docker compose down -v         # optional: wipe old volume
docker compose up -d           # loads init/hotel.dump automatically

# (Option A) Run the bot inside its container
docker compose run --rm -it agent     # starts src/chat_agent_gpt_4o_mini.py