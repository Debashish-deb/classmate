#!/bin/bash

# Update system
apt-get update
apt-get install -y docker.io docker-compose python3-pip git

# Start Docker service
systemctl start docker
systemctl enable docker

# Clone and build the application
git clone https://github.com/your-org/classmate.git /opt/classmate
cd /opt/classmate

# Build and start services
docker-compose -f infra/docker/docker-compose.yml up -d

# Setup nginx reverse proxy
apt-get install -y nginx
cp infra/docker/nginx.conf /etc/nginx/sites-available/default
ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/
systemctl restart nginx

# Setup log rotation
cat > /etc/logrotate.d/classmate << EOF
/opt/classmate/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
}
EOF

# Setup monitoring (basic)
apt-get install -y htop iotop

echo "ClassMate API server setup complete!"
