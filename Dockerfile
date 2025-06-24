# Use slim Python 3.12 as the base
FROM python:3.12-slim

# All following paths are inside the image
WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

# Copy your source code
COPY src ./src

# Start the agent when the container launches
ENTRYPOINT ["python", "src/chat_agent_gpt_4o_mini.py"]
