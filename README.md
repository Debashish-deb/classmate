# ClassMate - AI-Powered Lecture Recording & Note-Taking

ClassMate is a comprehensive mobile application for recording lectures, transcribing audio using AI, and generating intelligent notes automatically.

## 🏗️ Architecture

This project follows a monorepo structure:

```
classmate/
├── mobile_app/          # Flutter client (Android/iOS)
├── ai_backend/          # FastAPI services
├── ai_workers/          # Heavy processing workers
├── shared_contracts/    # API schemas
├── infra/               # Docker, Terraform, K8s
├── docs/
└── scripts/
```

## 📱 Mobile App Structure

The Flutter app follows a feature-based architecture:

```
mobile_app/lib/
├── core/
│   ├── theme/           # App theming
│   ├── routing/         # Navigation
│   ├── errors/          # Error handling
│   ├── permissions/     # Permission management
│   └── utils/           # Utilities
├── features/
│   ├── onboarding/      # First-time user experience
│   ├── recording/       # Audio recording interface
│   ├── processing/      # Transcription progress
│   ├── notes/           # View and edit notes
│   ├── export/          # PDF export functionality
│   ├── sessions/        # Session history
│   └── settings/        # App configuration
├── shared/
│   ├── widgets/         # Reusable UI components
│   ├── models/          # Data models
│   └── services/        # Core services
└── main.dart
```

## 🎯 Key Features

### Audio Recording
- **Chunked Recording**: 30-second chunks with 1-second overlap
- **Whisper Compatibility**: 16kHz mono PCM 16-bit WAV format
- **Background Recording**: Foreground service with proper Android handling
- **Real-time Waveform**: Visual feedback during recording

### AI Processing
- **Speech-to-Text**: Faster-Whisper integration
- **Note Generation**: AI-powered summarization
- **Speaker Detection**: Multiple speaker identification
- **Key Point Extraction**: Automatic highlighting

### Data Management
- **Offline Queue**: Resumable uploads with retry logic
- **Local Storage**: SQLite for session management
- **Cloud Sync**: Automatic synchronization
- **Export Options**: PDF and other formats

## 🚀 Getting Started

### Prerequisites
- Flutter SDK (>=3.10.8)
- Dart SDK
- Android Studio / Xcode
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd classmate
   ```

2. **Set up Flutter app**
   ```bash
   cd mobile_app
   flutter pub get
   flutter run
   ```

3. **Configure permissions**
   - Android: Update `android/app/src/main/AndroidManifest.xml`
   - iOS: Update `ios/Runner/Info.plist`

4. **Run tests**
   ```bash
   flutter test
   ```

## 🧪 Testing Strategy

### Unit Tests
- Service layer testing
- Model validation
- Business logic verification

### Integration Tests
- Recording pipeline
- Upload queue functionality
- Background processing

### UI Tests
- User flows
- Component interactions
- Error scenarios

## 🔧 Development

### State Management
- **Riverpod**: Compile-time safe state management
- **Providers**: Dependency injection and state containers

### Code Generation
```bash
# Run code generation
flutter packages pub run build_runner build

# Watch for changes
flutter packages pub run build_runner watch
```

### Architecture Patterns
- **Clean Architecture**: Separation of concerns
- **Repository Pattern**: Data access abstraction
- **Service Layer**: Business logic encapsulation

## 📦 Dependencies

### Core
- `flutter_riverpod`: State management
- `go_router`: Navigation
- `dio`: HTTP client

### Audio
- `record`: Audio recording
- `flutter_sound`: Advanced audio features
- `permission_handler`: Permissions

### Storage
- `sqflite`: Local database
- `shared_preferences`: Simple storage
- `path_provider`: File system access

### Background
- `flutter_background_service`: Background tasks
- `workmanager`: Scheduled tasks

## 🔒 Security

- **API Keys**: Environment-based configuration
- **Data Encryption**: Local storage encryption
- **Network Security**: HTTPS certificate pinning
- **Privacy Compliance**: GDPR and CCPA ready

## 📊 Performance

### Optimization
- **Lazy Loading**: On-demand data fetching
- **Memory Management**: Efficient audio buffering
- **Battery Optimization**: Smart background processing
- **Network Efficiency**: Chunked uploads

### Monitoring
- **Analytics**: User behavior tracking
- **Crash Reporting**: Automatic error collection
- **Performance Metrics**: Response time monitoring

## 🚀 Deployment

### Android
```bash
flutter build apk --release
flutter build appbundle --release
```

### iOS
```bash
flutter build ios --release
```

### CI/CD
- **GitHub Actions**: Automated testing and building
- **Fastlane**: Deployment automation
- **Code Signing**: Automated certificate management

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Join our community Discord

---

**Built with ❤️ for students and educators**
