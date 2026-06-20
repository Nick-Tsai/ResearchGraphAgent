#!/bin/bash
# Research Graph Agent — Deployment Script (向导式)
set -e

cd "$(dirname "$0")"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Research Graph Agent Deployment ===${NC}\n"

# 1. Environment check
echo -e "${YELLOW}[1/5] Checking environment...${NC}"
command -v docker >/dev/null 2>&1 || { echo "❌ Docker not installed"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "❌ Git not installed"; exit 1; }
echo "✓ Docker $(docker --version | cut -d' ' -f3)"
echo "✓ Git $(git --version | cut -d' ' -f3)"

# 2. .env setup
echo -e "\n${YELLOW}[2/5] Setting up .env...${NC}"
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "✓ Created backend/.env from template"
    echo "⚠️  Edit backend/.env and add your DEEPSEEK_API_KEY before starting"
else
    echo "✓ backend/.env exists"
fi

# 3. Firecrawl pool check
echo -e "\n${YELLOW}[3/5] Checking firecrawl_pool.json...${NC}"
if [ ! -f backend/firecrawl_pool.json ]; then
    echo '{"instances":[]}' > backend/firecrawl_pool.json
    echo "⚠️  Created empty firecrawl_pool.json — add your instances"
else
    echo "✓ firecrawl_pool.json exists"
fi

# 4. Docker build
echo -e "\n${YELLOW}[4/5] Building Docker images...${NC}"
docker compose build --no-cache

# 5. Start
echo -e "\n${YELLOW}[5/5] Starting services...${NC}"
docker compose up -d

echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
echo "Frontend: http://localhost:3001"
echo "Backend:  http://localhost:8001"
echo ""
echo "Next steps:"
echo "  1. Configure Caddy to proxy /research/* → localhost:3001"
echo "  2. Configure Caddy to proxy /research/api/* → localhost:8001"
echo "  3. Run: caddy reload"
