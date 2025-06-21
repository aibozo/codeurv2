import os, asyncio, confluent_kafka, inspect
from .codec import decode
from .metrics import CONS_CNT

_BOOT=os.getenv("KAFKA_BOOTSTRAP","kafka:9092")

class AsyncConsumer:
    def __init__(self, group:str, topics:list[str], proto_map:dict[str,object]|None=None):
        self._c = confluent_kafka.Consumer({
            "bootstrap.servers":_BOOT,
            "group.id": group,
            "auto.offset.reset":"earliest"})
        self._c.subscribe(topics)
        self._proto_map = proto_map or {}

    async def __aiter__(self):
        while True:
            msg = self._c.poll(0.3)
            if not msg:
                await asyncio.sleep(0.1); continue
            if msg.error():
                if msg.error().code() == confluent_kafka.KafkaError._PARTITION_EOF:
                    continue
                raise RuntimeError(msg.error())
            topic = msg.topic()
            cls = self._proto_map.get(topic, dict)
            CONS_CNT.labels(topic).inc()
            yield topic, decode(msg.value(), cls)