# ClassMate Project Structure

## Overview

ClassMate is a comprehensive AI-powered meeting assistant application with a monorepo structure containing mobile app, web app, AI backend, workers, and infrastructure.

## Directory Structure

```
classmate/
├── README.md                           # Project overview and setup guide
├── COMPETITIVE_ANALYSIS.md            # Market analysis and competitive gaps
├── PROJECT_STRUCTURE.md               # This file
├── mobile_app/                         # Flutter mobile application
│   ├── android/                         # Android-specific code and configuration
│   │   ├── app/                         # Android app module
│   │   ├── gradle/                      # Gradle build configuration
│   │   └── gradlew                       # Gradle wrapper
│   ├── ios/                             # iOS-specific code and configuration
│   │   ├── Runner.xcodeproj/            # Xcode project
│   │   ├── Runner/                      # iOS app source
│   │   └── Podfile                      # iOS dependencies
│   ├── lib/                             # Dart source code
│   │   ├── main.dart                    # App entry point
│   │   ├── core/                        # Core app functionality
│   │   │   ├── theme/                    # App theming and styling
│   │   │   │   └── app_theme.dart
│   │   │   └── routing/                  # Navigation and routing
│   │   │       └── app_router.dart
│   │   ├── features/                     # Feature-based modules
│   │   │   ├── onboarding/              # User onboarding flow
│   │   │   │   └── pages/
│   │   │   │       └── onboarding_page.dart
│   │   │   ├── recording/                # Audio recording functionality
│   │   │   │   └── pages/
│   │   │   │       └── recording_page.dart
│   │   │   ├── sessions/                 # Session management
│   │   │   │   └── pages/
│   │   │   │       └── sessions_page.dart
│   │   │   ├── notes/                    # Note viewing and management
│   │   │   │   └── pages/
│   │   │   │       └── notes_page.dart
│   │   │   ├── settings/                 # App settings and configuration
│   │   │   │   └── pages/
│   │   │   │       └── settings_page.dart
│   │   │   ├── processing/               # Processing status display
│   │   │   │   └── pages/
│   │   │   │       └── processing_page.dart
│   │   │   └── export/                   # Data export functionality
│   │   │       └── pages/
│   │   │           └── export_page.dart
│   │   └── shared/                       # Shared utilities and components
│   │       ├── models/                   # Data models and schemas
│   │       │   ├── session_model.dart
│   │       │   └── session_model.g.dart
│   │       ├── services/                 # Business logic and API services
│   │       │   ├── api_client.dart
│   │       │   ├── recording_service.dart
│   │       │   ├── session_manager.dart
│   │       │   └── upload_queue_service.dart
│   │       └── widgets/                  # Reusable UI components
│   │           └── recording_button.dart
│   ├── pubspec.yaml                      # Flutter dependencies
│   ├── pubspec.lock                      # Dependency lock file
│   ├── analysis_options.yaml             # Dart analysis configuration
│   └── test/                             # Test files
│       └── widget_test.dart
├── ai_backend/                          # Python FastAPI backend
│   ├── __init__.py                      # Package initialization
│   ├── main.py                          # FastAPI application entry point
│   ├── requirements.txt                  # Python dependencies
│   ├── database/                         # Database configuration and models
│   │   ├── __init__.py
│   │   ├── models.py                    # SQLAlchemy models
│   │   └── database.py                  # Database setup and utilities
│   ├── api/                             # API routes and endpoints
│   │   ├── __init__.py
│   │   └── routes.py                    # FastAPI route definitions
│   ├── services/                         # Business logic services
│   │   ├── __init__.py
│   │   ├── transcription_service.py      # Audio transcription service
│   │   ├── notes_service.py              # AI notes generation service
│   │   └── enhanced_transcription_service.py # Enhanced transcription with speaker ID
│   └── tests/                           # Backend tests
├── ai_workers/                          # Celery worker processes
│   ├── __init__.py                      # Package initialization
│   ├── requirements.txt                  # Worker dependencies
│   ├── transcription_worker.py           # Audio transcription worker
│   ├── notes_worker.py                  # Notes generation worker
│   ├── celery_app.py                     # Celery application configuration
│   └── tests/                           # Worker tests
├── infra/                               # Infrastructure as Code
│   ├── __init__.py                      # Package initialization
│   ├── README.md                         # Infrastructure documentation
│   ├── docker/                           # Docker configurations
│   │   ├── docker-compose.yml          # Multi-service Docker setup
│   │   ├── nginx.conf                    # Nginx reverse proxy
│   │   ├── Dockerfile.backend           # Backend Docker image
│   │   └── Dockerfile.worker            # Worker Docker image
│   ├── k8s/                              # Kubernetes manifests
│   │   ├── namespace.yaml               # Kubernetes namespace
│   │   ├── postgres.yaml                # PostgreSQL deployment
│   │   ├── redis.yaml                   # Redis deployment
│   │   └── api.yaml                     # API deployment
│   └── terraform/                        # Terraform IaC
│       ├── main.tf                      # AWS infrastructure
│       ├── variables.tf                 # Terraform variables
│       ├── user-data.sh                 # EC2 initialization script
│       └── outputs.tf                   # Terraform outputs
├── shared_contracts/                    # Shared API contracts and models
│   ├── __init__.py                      # Package initialization
│   └── models.py                        # Pydantic data models
├── web_app/                             # Progressive Web App
│   ├── index.html                        # Main HTML file
│   ├── manifest.json                     # PWA manifest
│   ├── src/                             # Web app source code
│   │   ├── main.js                      # JavaScript entry point
│   │   ├── styles.css                   # CSS styling
│   │   └── components/                  # Web components
│   └── icons/                           # PWA icons
│       ├── icon-72x72.png
│       ├── icon-96x96.png
│       ├── icon-128x128.png
│       ├── icon-144x144.png
│       ├── icon-152x152.png
│       ├── icon-192x192.png
│       ├── icon-384x384.png
│       └── icon-512x512.png
└── docs/                               # Additional documentation
    ├── API.md                           # API documentation
    ├── DEPLOYMENT.md                    # Deployment guides
    └── DEVELOPMENT.md                   # Development setup
```

## Component Overview

### Mobile App (Flutter)
- **Core**: Theming, routing, and shared utilities
- **Features**: Modular feature-based architecture
  - Onboarding: User introduction flow
  - Recording: Audio capture and management
  - Sessions: Session lifecycle and display
  - Notes: AI-generated note viewing
  - Settings: App configuration
  - Processing: Status display
  - Export: Data export functionality
- **Shared**: Reusable components and services

### AI Backend (FastAPI)
- **Database**: SQLAlchemy models and setup
- **API**: RESTful endpoints and routing
- **Services**: Business logic for transcription and notes
- **Enhanced Features**: Speaker identification, noise reduction

### AI Workers (Celery)
- **Transcription Worker**: Background audio processing
- **Notes Worker**: AI-powered note generation
- **Task Queue**: Redis-based distributed processing

### Infrastructure
- **Docker**: Multi-service containerization
- **Kubernetes**: Production orchestration
- **Terraform**: Cloud infrastructure (AWS)

### Web App (PWA)
- **Progressive Web App**: Browser-based interface
- **Real-time Features**: WebSocket connectivity
- **Responsive Design**: Mobile and desktop support

### Shared Contracts
- **API Models**: Pydantic schemas for API communication
- **Data Validation**: Consistent data structures

## Technology Stack

### Frontend
- **Flutter**: Cross-platform mobile development
- **Dart**: Programming language
- **Riverpod**: State management
- **Go Router**: Navigation
- **Material 3**: UI design system

### Backend
- **FastAPI**: Python web framework
- **SQLAlchemy**: ORM and database toolkit
- **Celery**: Distributed task queue
- **Redis**: Message broker and cache
- **PostgreSQL**: Production database

### Infrastructure
- **Docker**: Containerization
- **Kubernetes**: Container orchestration
- **Terraform**: Infrastructure as Code
- **AWS**: Cloud provider
- **Nginx**: Reverse proxy

### AI/ML
- **Whisper**: Speech-to-text transcription
- **Pydantic**: Data validation
- **PyTorch**: Machine learning framework
- **Pyannote**: Speaker diarization

## Development Workflow

### Local Development
1. **Mobile App**: `cd mobile_app && flutter run`
2. **Backend**: `cd ai_backend && python main.py`
3. **Workers**: `cd ai_workers && celery -A celery_app worker`
4. **Web App**: Serve `web_app/` directory

### Docker Development
```bash
cd infra/docker
docker-compose up -d
```

### Kubernetes Deployment
```bash
kubectl apply -f infra/k8s/
```

### AWS Deployment
```bash
cd infra/terraform
terraform init
terraform apply
```

## Data Flow

```
Flutter App → API Client → FastAPI Backend → Celery Workers → Database
     ↓              ↓              ↓              ↓
  Local Storage ← API Response ← Task Results ← Processed Data
```

## Key Features

### Recording Pipeline
1. Audio capture in Flutter app
2. Upload to FastAPI backend
3. Queue transcription task to Celery
4. Process with Whisper model
5. Generate AI notes
6. Store in database
7. Sync back to Flutter app

### Real-time Features
- WebSocket connections for live updates
- Background task processing
- Progress tracking
- Notification system

### Data Management
- Local SQLite for offline access
- PostgreSQL for production
- Redis for caching and queuing
- S3/MinIO for file storage

## Security Considerations

- API authentication and authorization
- Data encryption at rest and in transit
- Secure file upload handling
- Rate limiting and DDoS protection
- GDPR compliance features

## Performance Optimizations

- Lazy loading of UI components
- Efficient database queries
- Caching strategies
- Background task processing
- Optimized asset delivery

## Monitoring and Observability

- Structured logging
- Health check endpoints
- Performance metrics
- Error tracking
- Resource monitoring

## Testing Strategy

### Frontend Tests
- Widget testing
- Integration testing
- Performance testing

### Backend Tests
- Unit tests
- API endpoint testing
- Database testing
- Load testing

### Infrastructure Tests
- Container testing
- Deployment testing
- Security testing

## Deployment Pipeline

### Continuous Integration
- Automated testing
- Code quality checks
- Security scanning
- Build automation

### Continuous Deployment
- Staging environment
- Production deployment
- Rollback strategies
- Blue-green deployment

## Maintenance

### Regular Updates
- Dependency updates
- Security patches
- Performance optimization
- Feature enhancements

### Monitoring
- System health checks
- Performance metrics
- Error tracking
- User analytics

This structure provides a scalable, maintainable, and production-ready foundation for the ClassMate AI meeting assistant application.
