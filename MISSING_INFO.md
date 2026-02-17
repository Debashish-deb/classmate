# ClassMate — Missing Information & External Dependencies

This document lists items that require **external input, credentials, or infrastructure setup** before the app is fully production-ready. Each item includes the file where it needs to be configured.

---

## 1. OAuth Token Encryption at Rest (Priority: High)

**File:** `ai_backend/database/collaboration_models.py` (lines 118–124)

OAuth tokens (`google_access_token`, `microsoft_refresh_token`, etc.) are stored in **plaintext** in the `users` table. These should be encrypted using `EncryptionService.encrypt_sensitive_data()` before writing and decrypted on read.

**Action needed:** Wrap all OAuth token reads/writes through the encryption service. This requires a migration to re-encrypt existing tokens.

---

## 2. Authentication Setup (Email + Google)

### Email Authentication - IMPLEMENTED 
1. Added password hash field to User model
2. Implemented password hashing with bcrypt
3. Created auth endpoints: `/auth/register`, `/auth/login`, `/auth/me`
4. Added JWT token authentication
5. Created mobile auth service and UI pages

### Google OAuth - COMPLETED
1. Created OAuth 2.0 credentials in Google Cloud Console
2. Added SHA-1 fingerprints:
   - Default debug: `BC:CD:BD:BA:85:0F:19:F4:1B:81:05:CE:07:BA:59:BD:CB:D8:EA:31`
   - Custom debug: `27:C0:7A:E5:59:43:B8:90:B0:36:D6:64:AA:64:CA:D7:BD:C7:28:5A`
3. Package name: `com.classmate.mobile_app`
4. Downloaded client secret JSON
5. Configured environment variables in `.env`:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `JWT_SECRET_KEY`

---

## 3. Cloud Storage Configuration (S3/GCS)

**File:** `ai_backend/services/cloud_storage_service.py`

The cloud storage service needs:

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME` — for AWS S3
- Or `GCS_BUCKET_NAME`, `GOOGLE_APPLICATION_CREDENTIALS`

Currently the upload queue in the mobile app points to `https://api.classmate.app/upload` which doesn't exist. Update `upload_queue_service.dart` line 132 to point to your actual backend URL.

**File to update:** `mobile_app/lib/shared/services/upload_queue_service.dart` (line 132)

---

## 4. Production Domain & CORS Origins

**File:** `ai_backend/.env` → `CORS_ALLOWED_ORIGINS`

Replace `*` with your actual production domain(s), e.g.:

```
CORS_ALLOWED_ORIGINS=https://app.classmate.com,https://classmate.app
```

---

## 5. PostgreSQL Connection String

**File:** `ai_backend/.env` → `DATABASE_URL`

For production, set:

```
DATABASE_URL=postgresql://user:password@host:5432/classmate
```

The current default is SQLite which is **not suitable for multi-worker deployments**. A warning is logged if SQLite is used.

---

## 6. Redis for Rate Limiting (Scalability)

**File:** `ai_backend/api/public_api.py` → `APIKeyManager._check_rate_limit()`

Current rate limiting uses an in-memory dict (not shared across workers, unbounded growth). For production at scale, replace with Redis:

- Add `REDIS_URL` to `.env`
- Use `redis-py` with sorted sets for sliding-window rate limiting

---

## 7. Signed URL Expiry & Session Binding

**File:** `ai_backend/services/cloud_storage_service.py`

S3/GCS signed URLs currently use 7-day expiry with no session or IP binding. For security:

- Reduce expiry to 1–4 hours
- Bind URLs to user session tokens

---

## 8. GDPR Deletion Completeness

**Files:**

- `ai_backend/api/routes.py` — session deletion endpoint
- `ai_backend/services/cloud_storage_service.py` — S3/GCS file deletion
- `agent_memory.db` — event cleanup
- Redis — task result cleanup

When a user requests data deletion, all of the above storage systems must be purged. Currently only the SQLite/PostgreSQL row is deleted.

---

## 9. Privacy Policy URL

**Required for:** Google Play Data Safety form, Apple App Store privacy section

A functional privacy policy URL (e.g., `https://classmate.app/privacy`) must be created and submitted during app store review.

---

## 10. App Store Metadata

**iOS:** `mobile_app/ios/Runner/Info.plist`

- `CFBundleDisplayName` should be `ClassMate` (currently `Mobile App`)
- Add `PrivacyInfo.xcprivacy` for iOS 17+ privacy manifest

**Android:** `mobile_app/android/app/src/main/AndroidManifest.xml`

- `android:label` should be `ClassMate` (currently `mobile_app`)

---

## 11. Whisper Model Selection for Production - IMPLEMENTED

**File:** `ai_backend/.env` → `WHISPER_MODEL_SIZE`

The `TranscriptionService` now correctly reads `WHISPER_MODEL_SIZE` from environment variables (default: `medium`).

For production:

- Use `medium` for cost-effective balance
- Use `large-v3` only with dedicated GPU inference service

---

## 13. Docker Registry Credentials (Production)

**File:** Github Actions / CI/CD Pipeline

For production deployment, you need to configure:

- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`
- `DOCKER_REGISTRY` (if not using Docker Hub)

These should be stored as secrets in your CI/CD platform (e.g., GitHub Secrets).

---

## Summary of Quick Config Items

| Item | Env Var | Where to Set |
| :--- | :--- | :--- |
| OpenAI API Key | `OPENAI_API_KEY` | `ai_backend/.env` ✅ |
| DeepSeek API Key | `DEEPSEEK_API_KEY` | `ai_backend/.env` ✅ |
| Database | `DATABASE_URL` | `ai_backend/.env` |
| CORS Origins | `CORS_ALLOWED_ORIGINS` | `ai_backend/.env` |
| Encryption Key | `ENCRYPTION_MASTER_KEY` | `ai_backend/.env` (auto-generated in dev) |
| Whisper Model | `WHISPER_MODEL_SIZE` | `ai_backend/.env` |
| Cloud Storage | `S3_BUCKET_NAME` etc. | `ai_backend/.env` |
| Redis | `REDIS_URL` | `ai_backend/.env` |
| Celery Broker | `CELERY_BROKER_URL` | `ai_backend/.env` |
| Docker Registry | `DOCKER_USERNAME` etc. | CI/CD Secrets |
