import uuid, asyncio, os, logging
from collections import defaultdict
from apps.core_contracts_pb2 import Plan, TaskBundle, CodingTask
from clients import rag_client
from clients.srm_client import SRMClient
from apps.orchestrator import topics as T
from clients.kafka_utils import produce, subscribe
from prometheus_client import Counter, start_http_server
import networkx as nx
import radon.complexity as rc

GROUP = "code-planner"

# Prometheus metrics
TASKS = Counter("cp_tasks_emitted_total","coding tasks")
start_http_server(9500)

srm = SRMClient("srm", 9090)
log = logging.getLogger("code-planner")

async def complexity_of(snippet:str)->str:
    try:
        cc = max(b.complexity for b in rc.cc_visit(snippet))
        return "trivial" if cc<=5 else "moderate" if cc<=10 else "complex"
    except Exception:
        return "moderate"

async def build_tasks(plan:Plan)->TaskBundle:
    tb = TaskBundle(plan_id=plan.id)
    for step in plan.steps:
        task = CodingTask(
            id=str(uuid.uuid4()),
            parent_plan_id=plan.id,
            step_number=step.order,
            goal=step.goal,
            path=step.path,
            kind=step.kind
        )
        # hydrate contextual chunks
        ctx = await rag_client.hybrid_search(step.goal, k=6, alpha=.25,
                                             filter={"path": step.path} if step.path else None)
        task.blob_ids.extend([str(c.get("id", i)) for i, c in enumerate(ctx)])
        # complexity label
        if ctx:
            snippet = ctx[0].get("snippet", "")
            task.complexity = await complexity_of(snippet)
        else:
            task.complexity = "moderate"
        tb.tasks.append(task)
    return tb

async def loop():
    async for topic, plan in subscribe(GROUP, [T.PLAN], proto_map={T.PLAN: Plan}):
        tb = await build_tasks(plan)
        await produce(T.TASK, tb)
        TASKS.inc(len(tb.tasks))
        log.info("emitted %d tasks for plan %s", len(tb.tasks), plan.id)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(loop())