from celery import Celery

celery_app = Celery("tasks")
celery_app.conf.update(
    broker_url="redis://localhost:6379/0",
    result_backend=None,
    task_always_eager=True,  # eager mode for tests
)
