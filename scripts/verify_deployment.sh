#!/bin/bash

echo "🔍 Verifying ClassMate Deployment..."

# 1. Check Docker Containers
echo "\n📦 Checking Containers..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ Containers are running."
else
    echo "❌ No containers running. Run 'docker-compose up -d --build' first."
    exit 1
fi

# 2. Check Backend Health
echo "\n🏥 Checking Backend Health..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80/api/v1/public/health)

if [ "$HEALTH_STATUS" -eq 200 ]; then
    echo "✅ Backend is HEALTHY (200 OK)"
else
    echo "❌ Backend is UNHEALTHY (Status: $HEALTH_STATUS)"
    echo "   Check logs: docker-compose logs backend"
fi

# 3. Check Traefik Dashboard
echo "\n🚦 Checking Traefik Dashboard..."
TRAEFIK_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/dashboard/)

if [ "$TRAEFIK_STATUS" -eq 200 ]; then
    echo "✅ Traefik Dashboard is ACCESSIBLE"
else
    echo "⚠️  Traefik Dashboard might be inaccessible (Status: $TRAEFIK_STATUS)"
fi

# 4. Check Database Connection (via logs)
echo "\n🗄️  Checking Database Connection..."
if docker-compose logs backend | grep -q "Database tables created"; then
    echo "✅ Database connection verified (Logs)"
else
    echo "⚠️  Could not verify DB connection in recent logs. It might be fine if already initialized."
fi

echo "\n🎉 Verification Complete! Access the app at http://localhost"
