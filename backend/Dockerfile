FROM m.daocloud.io/docker.io/library/python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

COPY app/ ./app/
RUN test -f firecrawl_pool.json || echo '{"instances":[]}' > firecrawl_pool.json

RUN mkdir -p /data
ENV DATABASE_URL=sqlite:////data/research_graph_agent.db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--root-path", "/research"]
