web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
worker: celery -A app.tasks.celery_app worker --beat --loglevel=info --concurrency=2
