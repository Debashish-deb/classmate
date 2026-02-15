terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  region = "us-west-2"
}

# VPC Configuration
resource "aws_vpc" "classmate" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "classmate-vpc"
    Environment = "production"
  }
}

# Subnets
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.classmate.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-west-2a"
  map_public_ip_on_launch = true

  tags = {
    Name = "classmate-public-subnet"
  }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.classmate.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-west-2b"

  tags = {
    Name = "classmate-private-subnet"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "classmate" {
  vpc_id = aws_vpc.classmate.id

  tags = {
    Name = "classmate-igw"
  }
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.classmate.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.classmate.id
  }

  tags = {
    Name = "classmate-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Security Groups
resource "aws_security_group" "api" {
  name        = "classmate-api-sg"
  description = "Security group for ClassMate API"
  vpc_id      = aws_vpc.classmate.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "classmate-api-sg"
  }
}

resource "aws_security_group" "postgres" {
  name        = "classmate-postgres-sg"
  description = "Security group for PostgreSQL"
  vpc_id      = aws_vpc.classmate.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "classmate-postgres-sg"
  }
}

# RDS PostgreSQL
resource "aws_db_subnet_group" "classmate" {
  name       = "classmate-db-subnet-group"
  subnet_ids = [aws_subnet.private.id]

  tags = {
    Name = "classmate-db-subnet-group"
  }
}

resource "aws_db_instance" "postgres" {
  identifier     = "classmate-postgres"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp2"
  storage_encrypted     = true
  
  db_name  = "classmate"
  username = "classmate"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.postgres.id]
  db_subnet_group_name   = aws_db_subnet_group.classmate.name
  
  skip_final_snapshot = true
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  tags = {
    Name = "classmate-postgres"
  }
}

# ElastiCache Redis
resource "aws_elasticache_subnet_group" "classmate" {
  name        = "classmate-redis-subnet-group"
  description = "Subnet group for ClassMate Redis"
  subnet_ids  = [aws_subnet.private.id]
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "classmate-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.classmate.name
  security_group_ids   = [aws_security_group.redis.id]
  
  tags = {
    Name = "classmate-redis"
  }
}

resource "aws_security_group" "redis" {
  name        = "classmate-redis-sg"
  description = "Security group for Redis"
  vpc_id      = aws_vpc.classmate.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "classmate-redis-sg"
  }
}

# S3 Bucket for file storage
resource "aws_s3_bucket" "classmate" {
  bucket = "classmate-audio-storage-${random_id.bucket_suffix}"
  
  tags = {
    Name        = "classmate-audio-storage"
    Environment = "production"
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 8
}

resource "aws_s3_bucket_versioning" "classmate" {
  bucket = aws_s3_bucket.classmate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption" "classmate" {
  bucket = aws_s3_bucket.classmate.id

  rule {
    apply_server_side_encryption_by_default = true
    sse_algorithm = "AES256"
  }
}

# EC2 Instance for API
resource "aws_instance" "api" {
  ami           = "ami-0c55b159cbfafe1f0"  # Ubuntu 22.04 LTS
  instance_type = "t3.micro"
  
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids    = [aws_security_group.api.id]
  associate_public_ip_address = true
  
  user_data = base64encode(file("user-data.sh"))
  
  tags = {
    Name = "classmate-api-server"
  }
}

# Outputs
output "api_public_ip" {
  description = "Public IP address of the API server"
  value       = aws_instance.api.public_ip
}

output "postgres_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.postgres.endpoint
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "s3_bucket_name" {
  description = "S3 bucket name for audio storage"
  value       = aws_s3_bucket.classmate.id
}
