from apps.orchestrator.state_machine import OrchestratorFSM, Stage
def test_ok_flow():
    f = OrchestratorFSM()
    f.crq(); assert f.state == Stage.PLAN.value
    f.plan(); assert f.state == Stage.CODE.value
    f.code_ok()
    f.build_ok()
    f.tspec(); f.gt_ok(); f.build2_ok()
    assert f.state == Stage.DONE.value