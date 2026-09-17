"""RQ worker entrypoint. Run with: uv run python -m worker.run_worker"""

from redis import Redis
from rq import Worker

from api.queue import QUEUE_NAME
from rag.config import REDIS_URL

if __name__ == "__main__":
    connection = Redis.from_url(REDIS_URL)
    worker = Worker([QUEUE_NAME], connection=connection)
    worker.work()
