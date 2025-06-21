from prometheus_client import Counter, Histogram

PROD_CNT = Counter("kf_messages_produced_total","",["topic"])
CONS_CNT = Counter("kf_messages_consumed_total","",["topic"])
LAT      = Histogram("kf_produce_latency_sec","",["topic"])