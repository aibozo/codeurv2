import asyncio, json, os, uuid
from datetime import datetime
from confluent_kafka import Producer, Consumer, KafkaError
from apps.orchestrator.state_machine import OrchestratorFSM, Stage
from apps.orchestrator import topics as T
from apps import core_contracts_pb2 as pb
from prometheus_client import Counter, Histogram, start_http_server

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP","kafka:9092")

producer = Producer({"bootstrap.servers": BOOTSTRAP})
consumer = Consumer({
    "bootstrap.servers": BOOTSTRAP,
    "group.id": "orchestrator",
    "auto.offset.reset": "earliest"
})
SUBS = [T.CRQ, T.PLAN, T.TASK, T.CRES, T.BREPORT, T.TSPEC, T.GTRES]
consumer.subscribe(SUBS)

fsm = OrchestratorFSM()
current_request_id = None
pending_tasks = set()

STAGE_METRIC = Counter("orch_stage_total","increment per stage",["stage"])
start_http_server(9300)

def update_metric():
    STAGE_METRIC.labels(fsm.state).inc()

def emit(topic:str, msg):
    producer.produce(topic, msg)
    producer.poll(0)

def handle_change_request(msg):
    global current_request_id
    cr = pb.ChangeRequest.FromString(msg.value())
    current_request_id = cr.id
    fsm.crq()
    update_metric()
    print("Request accepted", cr.id)
    # forward to Architect / Planner
    emit(T.DEEP, msg.value())

async def main_loop():
    while True:
        msg = consumer.poll(0.2)
        if msg is None: 
            await asyncio.sleep(0.1); continue
        if msg.error() and msg.error().code() != KafkaError._PARTITION_EOF:
            print("Kafka error", msg.error()); continue
        topic = msg.topic()
        if topic == T.CRQ: handle_change_request(msg)
        elif topic == T.PLAN:
            fsm.plan(); update_metric(); emit(T.TASK, msg.value())
        elif topic == T.CRES:
            res = pb.CommitResult.FromString(msg.value())
            if res.status == "SUCCESS":
                pending_tasks.discard(res.task_id)
            if not pending_tasks:
                fsm.code_ok(); update_metric()
        elif topic == T.BREPORT:
            rep = pb.BuildReport.FromString(msg.value())
            if rep.status == "PASSED":
                if fsm.state == Stage.BUILD1.value: 
                    fsm.build_ok(); update_metric()
                elif fsm.state == Stage.BUILD2.value: 
                    fsm.build2_ok(); update_metric()
            else:
                fsm.build_fail(); update_metric(); emit(T.REG, b"regression")
        elif topic == T.TSPEC: 
            fsm.tspec(); update_metric()
        elif topic == T.GTRES:
            gtr = pb.GeneratedTests.FromString(msg.value())
            if gtr.precheck == "PASSED": 
                fsm.gt_ok(); update_metric()
            else: 
                fsm.gt_fail(); update_metric()
        else:
            print("unrouted topic", topic)
        # done?
        if fsm.state == Stage.DONE.value:
            print("✓ Pipeline complete for", current_request_id)
            fsm.to_idle()   # reset
            update_metric()
        producer.flush(0)