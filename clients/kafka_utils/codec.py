from __future__ import annotations
import orjson, inspect, typing as _t
from google.protobuf.message import Message as _Proto

def encode(obj) -> bytes:
    if isinstance(obj, _Proto):
        return obj.SerializeToString()
    return orjson.dumps(obj)

def decode(data:bytes, cls:_t.Type) -> object:
    if inspect.isclass(cls) and issubclass(cls, _Proto):
        msg = cls(); msg.ParseFromString(data); return msg
    return orjson.loads(data)