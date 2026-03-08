import pytest
from domain.ports.orchestration_ports import (
    AgentRole,
    AgentTask,
    AgentResult,
    OrchestrationPlan,
    OrchestrationResult,
)


@pytest.fixture
def sample_plan():
    tasks = [
        AgentTask("t1", AgentRole.SCOUT, "Scan schema", {"schema_name": "APPS"}),
        AgentTask("t2", AgentRole.ARCHITECT, "Design mapping", {"tables": ["GL_JE_HEADERS"]}, depends_on=["t1"]),
        AgentTask("t3", AgentRole.VALIDATOR, "Validate mapping", {}, depends_on=["t2"]),
        AgentTask("t4", AgentRole.DOCUMENTER, "Update catalog", {}, depends_on=["t3"]),
    ]
    return OrchestrationPlan(plan_id="PLAN-001", schema_name="APPS", tasks=tasks)


def test_orchestration_plan_task_count(sample_plan):
    assert sample_plan.task_count == 4


def test_orchestration_plan_get_tasks_by_role(sample_plan):
    scout_tasks = sample_plan.get_tasks_by_role(AgentRole.SCOUT)
    assert len(scout_tasks) == 1
    assert scout_tasks[0].task_id == "t1"


def test_orchestration_plan_no_tasks_for_role():
    plan = OrchestrationPlan(plan_id="P1", schema_name="HR", tasks=[])
    assert plan.get_tasks_by_role(AgentRole.SCOUT) == []


def test_agent_task_dependencies():
    task = AgentTask("t2", AgentRole.ARCHITECT, "Design", depends_on=["t1"])
    assert task.depends_on == ["t1"]


def test_agent_task_no_dependencies():
    task = AgentTask("t1", AgentRole.SCOUT, "Scan")
    assert task.depends_on == []


def test_agent_result_success():
    result = AgentResult(
        task_id="t1", role=AgentRole.SCOUT, status="success",
        output_data={"customizations": []}, findings=["No customizations found"],
        duration_seconds=5.2,
    )
    assert result.status == "success"
    assert len(result.findings) == 1


def test_agent_result_failed():
    result = AgentResult(
        task_id="t2", role=AgentRole.ARCHITECT, status="failed",
        errors=["Connection timeout"],
    )
    assert result.status == "failed"
    assert result.errors == ["Connection timeout"]


def test_orchestration_result_all_succeeded():
    results = [
        AgentResult("t1", AgentRole.SCOUT, "success"),
        AgentResult("t2", AgentRole.ARCHITECT, "success"),
        AgentResult("t3", AgentRole.VALIDATOR, "success"),
        AgentResult("t4", AgentRole.DOCUMENTER, "success"),
    ]
    orch_result = OrchestrationResult(plan_id="P1", results=results)
    assert orch_result.all_succeeded is True
    assert orch_result.failed_tasks == []


def test_orchestration_result_partial_failure():
    results = [
        AgentResult("t1", AgentRole.SCOUT, "success", findings=["Found custom index"]),
        AgentResult("t2", AgentRole.ARCHITECT, "failed", errors=["AI timeout"]),
    ]
    orch_result = OrchestrationResult(plan_id="P1", results=results)
    assert orch_result.all_succeeded is False
    assert len(orch_result.failed_tasks) == 1
    assert orch_result.failed_tasks[0].task_id == "t2"


def test_orchestration_result_all_findings():
    results = [
        AgentResult("t1", AgentRole.SCOUT, "success", findings=["Finding A", "Finding B"]),
        AgentResult("t2", AgentRole.ARCHITECT, "success", findings=["Finding C"]),
    ]
    orch_result = OrchestrationResult(plan_id="P1", results=results)
    assert orch_result.all_findings == ["Finding A", "Finding B", "Finding C"]


def test_agent_role_values():
    assert AgentRole.SCOUT.value == "scout"
    assert AgentRole.ARCHITECT.value == "architect"
    assert AgentRole.VALIDATOR.value == "validator"
    assert AgentRole.DOCUMENTER.value == "documenter"
