from celery import Celery
from .transcription_worker import transcribe_audio_task
from .notes_worker import generate_notes_task

# Celery configuration
celery_app = Celery(
    'classmate_workers',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['ai_workers.transcription_worker', 'ai_workers.notes_worker']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Register tasks
celery_app.autodiscover_tasks(['ai_workers'])

if __name__ == '__main__':
    celery_app.start()
