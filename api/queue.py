from functools import lru_cache

from redis import Redis
from rq import Queue

from rag.config import REDIS_URL

QUEUE_NAME = "k8s-rag-jobs"


@lru_cache(maxsize=1)
def get_queue() -> Queue:
    connection = Redis.from_url(REDIS_URL)
    return Queue(QUEUE_NAME, connection=connection)


def enqueue_question(question: str, response_url: str) -> str:
    queue = get_queue()
    job = queue.enqueue("worker.tasks.process_question", question, response_url)
    return job.id
