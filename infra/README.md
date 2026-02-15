# ClassMate Infrastructure

This directory contains all infrastructure configuration for the ClassMate application.

## Directory Structure

```
infra/
├── docker/           # Docker Compose configuration
├── k8s/             # Kubernetes manifests
├── terraform/       # Terraform IaC configuration
└── README.md         # This file
```

## Docker Compose (Local Development)

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available

### Quick Start
```bash
cd infra/docker
docker-compose up -d
```

### Services
- **API**: FastAPI backend on port 8000
- **PostgreSQL**: Database on port 5432
- **Redis**: Message broker on port 6379
- **MinIO**: Object storage on ports 9000/9001
- **Nginx**: Reverse proxy on port 80

### Environment Variables
Create a `.env` file:
```bash
DATABASE_URL=postgresql://classmate:classmate123@postgres:5432/classmate
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=classmate
MINIO_SECRET_KEY=classmate123
```

## Kubernetes (Production)

### Prerequisites
- kubectl configured
- Helm 3 installed

### Deploy to Kubernetes
```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Deploy database
kubectl apply -f k8s/postgres.yaml

# Deploy Redis
kubectl apply -f k8s/redis.yaml

# Deploy API
kubectl apply -f k8s/api.yaml

# Check deployment
kubectl get pods -n classmate
```

### Services
- **postgres**: PostgreSQL database with persistent storage
- **redis**: Redis for Celery message broker
- **classmate-api**: FastAPI backend with auto-scaling
- **nginx-ingress**: Load balancer and SSL termination

## Terraform (Cloud Infrastructure)

### Prerequisites
- Terraform >= 1.0
- AWS CLI configured
- AWS credentials configured

### Deploy to AWS
```bash
cd infra/terraform
terraform init
terraform plan -var="db_password=your_secure_password"
terraform apply -var="db_password=your_secure_password"
```

### Resources Created
- **VPC**: Isolated network environment
- **Subnets**: Public and private subnets
- **Security Groups**: Network access control
- **RDS PostgreSQL**: Managed database
- **ElastiCache Redis**: Managed cache
- **S3 Bucket**: Object storage for audio files
- **EC2 Instance**: API server with Docker

### Outputs
- API server public IP
- Database endpoint
- Redis endpoint
- S3 bucket name

## Monitoring and Logging

### Docker Compose
```bash
# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Monitor resources
docker stats
```

### Kubernetes
```bash
# View logs
kubectl logs -f deployment/classmate-api -n classmate

# Monitor resources
kubectl top pods -n classmate
```

### AWS
```bash
# CloudWatch metrics
aws logs get-log-group /aws/ec2/classmate-api
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --statistics Average \
  --period 300
```

## Security Considerations

### Docker
- Use non-root users in containers
- Limit container resources
- Use secrets for sensitive data
- Regular security updates

### Kubernetes
- Network policies for traffic control
- Pod security policies
- RBAC for access control
- Secrets management

### AWS
- IAM roles with least privilege
- VPC with private subnets
- Security groups with minimal ports
- Encrypted storage and data

## Backup and Recovery

### Database Backups
```bash
# Docker Compose
docker exec postgres pg_dump -U classmate classmate > backup.sql

# Kubernetes
kubectl exec -n classmate postgres -- pg_dump -U classmate classmate > backup.sql

# AWS RDS
aws rds create-db-snapshot \
  --db-instance-identifier classmate-postgres \
  --db-snapshot-identifier classmate-backup-$(date +%Y%m%d)
```

### File Storage
- Docker: Volume mounts to host
- Kubernetes: Persistent volumes
- AWS: S3 with versioning and lifecycle policies

## Scaling

### Horizontal Scaling
```bash
# Docker Compose
docker-compose up -d --scale api=3

# Kubernetes
kubectl scale deployment classmate-api --replicas=5 -n classmate

# AWS Auto Scaling
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name classmate-api-asg \
  --launch-configuration-name classmate-api-lc \
  --min-size 2 --max-size 10 --desired-capacity 3
```

### Vertical Scaling
- Increase instance types based on load
- Monitor CPU and memory usage
- Adjust resource limits in manifests

## Troubleshooting

### Common Issues
1. **Database connection failed**: Check network connectivity and credentials
2. **Redis connection refused**: Ensure Redis is running and accessible
3. **File upload failed**: Check storage permissions and disk space
4. **High memory usage**: Monitor and optimize resource usage

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Database connection
docker exec postgres psql -U classmate -d classmate -c "SELECT 1;"

# Redis connection
docker exec redis redis-cli ping
```

## Cost Optimization

### Docker Compose
- Use resource limits
- Optimize image sizes
- Reuse containers

### Kubernetes
- Right-size instances
- Use cluster autoscaling
- Implement resource quotas

### AWS
- Use spot instances for non-critical workloads
- Implement lifecycle policies for S3
- Use reserved instances for predictable workloads
- Monitor and optimize storage costs

## Maintenance

### Updates
```bash
# Docker Compose
docker-compose pull
docker-compose up -d --force-recreate

# Kubernetes
kubectl set image deployment/classmate-api classmate-api=new-image -n classmate

# AWS
aws ec2 create-image --instance-id i-1234567890abcdef0 --name classmate-api-v2
```

### Cleanup
```bash
# Docker Compose
docker-compose down -v

# Kubernetes
kubectl delete namespace classmate

# AWS Terraform
terraform destroy
```
