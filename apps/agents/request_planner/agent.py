import os, uuid, json, re, asyncio, logging
from datetime import datetime
from prometheus_client import Counter, start_http_server
from apps.core_contracts_pb2 import ChangeRequest, Plan, Step
from clients.srm_client import SRMClient
from clients.rag_client import RagClient
from .prompt import build_prompt
from apps.orchestrator import topics as T
from clients.llm_client import json_chat
from clients.kafka_utils import produce, subscribe

GROUP = "request-planner"

log = logging.getLogger("request-planner")

# Prometheus metrics
PLANS = Counter("rp_plans_total","plans emitted")
start_http_server(9400)

srm = SRMClient("srm", 9090)
rag = RagClient("rag_service", 9100)

RESERVE_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")  # simple fn capture

async def process_change(cr):
    ctx_snips = await rag.hybrid_search(cr.description, k=8, alpha=.3)
    prompt = build_prompt(cr, ctx_snips)
    llm_json_str = await json_chat(
        messages=[
            {"role": "system", "content": "You are Request-Planner v1. Return ONLY valid JSON with keys: steps: [{goal, kind, path}], rationale: [...]"},
            {"role": "user", "content": prompt}
        ],
        model=os.getenv("PLANNER_MODEL","gpt-4o-mini")
    )
    llm_json = json.loads(llm_json_str)
    plan = Plan(
        id=str(uuid.uuid4()),
        parent_request_id=cr.id,
        rationale=llm_json["rationale"]
    )
    # steps
    for i, step_js in enumerate(llm_json["steps"], 1):
        plan.steps.append(
            Step(order=i, goal=step_js["goal"],
                 kind=step_js["kind"], path=step_js.get("path",""))
        )
    # reserve symbol names
    for sym in RESERVE_RE.findall(cr.description):
        try:
            reply = await srm.reserve(
                repo=cr.repo, branch=cr.branch,
                fq_name=sym, kind="function",
                file_path=step_js.get("path",""), plan_id=plan.id, ttl_sec=600)
            plan.reserved_lease_ids.append(str(reply.lease_id))
        except Exception as e:
            log.warning("Symbol conflict for %s: %s", sym, e)
    await produce(T.PLAN, plan)
    PLANS.inc()

async def main_loop():
    async for topic, msg in subscribe(GROUP, [T.CRQ], proto_map={T.CRQ: ChangeRequest}):
        await process_change(msg)

if __name__ == "__main__":
    asyncio.run(main_loop())