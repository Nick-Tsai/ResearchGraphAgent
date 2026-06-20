FROM python:3.14-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY app/ ./app/
COPY firecrawl_pool.json . 2>/dev/null || echo '{"instances":[]}' > firecrawl_pool.json

# Create data directory for SQLite
RUN mkdir -p /data
ENV DATABASE_URL=sqlite:////data/research_graph_agent.db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
