#!/bin/bash

# ClassMate Hybrid Launcher
# Run this from the project root: ./scripts/launch.sh

COMPOSE_FILE="docker-compose.prod.yml"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "🚀 ClassMate Hybrid Launcher"
echo "--------------------------------"
echo "1. Start Backend (Core: DB + Redis + API)"
echo "2. Start Full Stack (Core + Monitoring)"
echo "3. Run Mobile App (Flutter)"
echo "4. Open Web Dashboard"
echo "5. Stop All Servers"
echo "6. View Server Logs"
echo "7. Run Health Check"
echo "8. Restart Everything & Run App"
echo "--------------------------------"
read -p "Select an option [1-8]: " option

case $option in
    1)
        echo ""
        echo "🐳 Starting Core Backend Stack..."
        docker compose -f "$PROJECT_ROOT/$COMPOSE_FILE" up -d postgres redis minio api worker nginx
        echo ""
        echo "⏳ Waiting for services..."
        sleep 8
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ Backend is running and healthy."
        else
            echo "⚠️  Backend started but health check pending. Give it a few more seconds."
        fi
        echo ""
        echo "📊 Services:"
        echo "   API:    http://localhost:8000"
        echo "   MinIO:  http://localhost:9001"
        ;;
    2)
        echo ""
        echo "🐳 Starting Full Stack with Monitoring..."
        docker compose -f "$PROJECT_ROOT/$COMPOSE_FILE" up -d
        echo ""
        echo "⏳ Waiting for services..."
        sleep 12
        echo "✅ Full stack started."
        echo ""
        echo "📊 Services:"
        echo "   API:        http://localhost:8000"
        echo "   Grafana:    http://localhost:3000  (admin/classmate123)"
        echo "   Prometheus: http://localhost:9090"
        echo "   MinIO:      http://localhost:9001"
        echo "   Tempo:      http://localhost:3200"
        ;;
    3)
        # Check if backend is running
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            echo ""
            echo "✅ Backend is running."
        else
            echo ""
            echo "⚠️  Backend is NOT running."
            read -p "Start backend first? (y/n): " start_backend
            if [ "$start_backend" = "y" ]; then
                echo "🐳 Starting Core Backend..."
                docker compose -f "$PROJECT_ROOT/$COMPOSE_FILE" up -d postgres redis minio api
                echo "⏳ Waiting for services..."
                sleep 8
            fi
        fi

        echo ""
        echo "📱 Launching Mobile App..."
        cd "$PROJECT_ROOT/mobile_app" && flutter run
        ;;
    4)
        echo ""
        echo "🌐 Opening Web Dashboard..."
        open http://localhost:80 2>/dev/null || xdg-open http://localhost:80 2>/dev/null
        ;;
    5)
        echo ""
        echo "🛑 Stopping All Servers..."
        docker compose -f "$PROJECT_ROOT/$COMPOSE_FILE" down
        echo "✅ All services stopped."
        ;;
    6)
        echo ""
        echo "📄 Showing Logs (Ctrl+C to exit)..."
        docker compose -f "$PROJECT_ROOT/$COMPOSE_FILE" logs -f api worker
        ;;
    7)
        echo ""
        echo "🏥 Running Health Checks..."
        echo ""
        
        # API
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            echo "  ✅ API:        healthy"
        else
            echo "  ❌ API:        DOWN"
        fi
        
        # Postgres
        if docker exec classmate_postgres pg_isready -U classmate > /dev/null 2>&1; then
            echo "  ✅ PostgreSQL:  healthy"
        else
            echo "  ❌ PostgreSQL:  DOWN"
        fi
        
        # Redis
        if docker exec classmate_redis redis-cli ping > /dev/null 2>&1; then
            echo "  ✅ Redis:       healthy"
        else
            echo "  ❌ Redis:       DOWN"
        fi
        
        # Prometheus
        if curl -sf http://localhost:9090/-/healthy > /dev/null 2>&1; then
            echo "  ✅ Prometheus:  healthy"
        else
            echo "  ⚪ Prometheus:  not running"
        fi
        
        # Grafana
        if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
            echo "  ✅ Grafana:     healthy"
        else
            echo "  ⚪ Grafana:     not running"
        fi
        
        echo ""
        echo "📊 Metrics: http://localhost:8000/metrics"
        ;;
    8)
        echo ""
        echo "🔄 Restarting Everything & Launching App..."
        echo "🛑 Stopping all services..."
        docker compose -f "$PROJECT_ROOT/$COMPOSE_FILE" down
        
        echo ""
        echo "🐳 Starting Core Backend..."
        docker compose -f "$PROJECT_ROOT/$COMPOSE_FILE" up -d postgres redis minio api worker nginx
        echo "⏳ Waiting for services..."
        sleep 8
        echo "   Checking API health..."
        until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
            echo "   Still waiting for API..."
            sleep 2
        done
        echo "✅ Backend is ready."
        
        echo ""
        echo "📱 Launching Mobile App..."
        cd "$PROJECT_ROOT/mobile_app" && flutter run
        ;;
    *)
        echo "❌ Invalid option."
        ;;
esac
