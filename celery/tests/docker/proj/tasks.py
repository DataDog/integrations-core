from celery import Celery

app = Celery('tasks', broker='redis://default:devops-best-friend@docker-redis-standalone-1:6379')


@app.task(bind=True)
def add(self, x: int, y: int) -> int:
    result = x + y
    self.update_state(state='CUSTOM', meta={'custom_info': 'Hello from add', 'result': result})
    return result


@app.task(bind=True)
def multiply(self, x: int, y: int) -> int:
    result = x * y
    self.update_state(state='CUSTOM', meta={'custom_info': 'Hello from multiply', 'result': result})
    return result
