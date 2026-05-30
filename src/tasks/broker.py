from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from src.core.config import settings

# Initialize the broker
broker = ListQueueBroker(
    url=settings.REDIS_URL,
).with_result_backend(
    RedisAsyncResultBackend(
        redis_url=settings.REDIS_URL,
    )
)

# Initialize the scheduler
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
