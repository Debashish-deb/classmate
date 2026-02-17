from ai_backend.celery_client import celery_app

if __name__ == "__main__":
    celery_app.start()
