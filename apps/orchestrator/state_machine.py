from transitions import Machine, State
from enum import Enum

class Stage(str, Enum):
    IDLE="idle"; PLAN="plan_phase"; CODE="code_phase"
    BUILD1="build1"; TESTPLAN="test_plan"; TESTBUILD="test_build"
    BUILD2="build2"; DONE="done"; REGRESS="regress"

class OrchestratorFSM:
    states = [State(s.value) for s in Stage]
    def __init__(self):
        self.machine = Machine(model=self, states=self.states, initial=Stage.IDLE.value)
        self.machine.add_transition("crq",  Stage.IDLE.value,   Stage.PLAN.value)
        self.machine.add_transition("plan", Stage.PLAN.value,   Stage.CODE.value)
        self.machine.add_transition("code_ok", Stage.CODE.value, Stage.BUILD1.value)
        self.machine.add_transition("build_ok", Stage.BUILD1.value, Stage.TESTPLAN.value)
        self.machine.add_transition("build_fail", "*", Stage.REGRESS.value)
        self.machine.add_transition("tspec", Stage.TESTPLAN.value, Stage.TESTBUILD.value)
        self.machine.add_transition("gt_ok", Stage.TESTBUILD.value, Stage.BUILD2.value)
        self.machine.add_transition("gt_fail", Stage.TESTBUILD.value, Stage.REGRESS.value)
        self.machine.add_transition("build2_ok", Stage.BUILD2.value, Stage.DONE.value)