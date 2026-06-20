#!/bin/bash
# Research Graph Agent — Management Script
set -e

cd "$(dirname "$0")"

case "${1:-help}" in
  up|start)
    echo "🚀 Starting services..."
    docker compose up -d
    echo "✓ Frontend: http://localhost:3001"
    echo "✓ Backend:  http://localhost:8001"
    ;;
  down|stop)
    echo "🛑 Stopping services..."
    docker compose down
    ;;
  restart)
    echo "🔄 Restarting services..."
    docker compose down && docker compose up -d
    ;;
  build)
    echo "🔨 Rebuilding images..."
    docker compose build --no-cache
    docker compose up -d
    ;;
  logs)
    shift
    docker compose logs --tail="${1:-100}" -f
    ;;
  status|ps)
    docker compose ps
    ;;
  clean)
    echo "🧹 Removing containers, images, volumes..."
    docker compose down -v --rmi all
    rm -rf data/
    echo "✓ Cleaned"
    ;;
  *)
    echo "Usage: ./manage.sh {up|down|restart|build|logs|status|clean}"
    ;;
esac
