import os, asyncio, functools, confluent_kafka, time
from .codec import encode
from .metrics import PROD_CNT, LAT

_BOOT=os.getenv("KAFKA_BOOTSTRAP","kafka:9092")
_producer: confluent_kafka.Producer|None = None

def _get():
    global _producer
    if _producer is None:
        _producer = confluent_kafka.Producer({"bootstrap.servers":_BOOT})
    return _producer

async def send(topic:str, obj, key:str|None=None):
    p=_get(); data=encode(obj)
    loop=asyncio.get_running_loop()
    t0=time.perf_counter()
    await loop.run_in_executor(None, p.produce, topic, data, key)
    p.poll(0)                     # trigger delivery callbacks
    PROD_CNT.labels(topic).inc()
    LAT.labels(topic).observe(time.perf_counter()-t0)