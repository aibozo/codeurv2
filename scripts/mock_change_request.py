from confluent_kafka import Producer
from apps import core_contracts_pb2 as pb
import uuid, os
p = Producer({"bootstrap.servers": os.getenv("BOOT","localhost:9092")})
cr = pb.ChangeRequest(id=str(uuid.uuid4()), requester="kil",
                      repo="demo", branch="main",
                      description="add greet()")
p.produce("change.request.in", cr.SerializeToString())
p.flush()