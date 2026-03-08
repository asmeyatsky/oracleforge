from typing import Protocol, List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class AgentRole(Enum):
    """Roles for agents in the multi-agent orchestration pipeline."""
    SCOUT = "scout"
    ARCHITECT = "architect"
    VALIDATOR = "validator"
    DOCUMENTER = "documenter"


@dataclass(frozen=True)
class AgentTask:
    """A task assigned to an agent in the orchestration pipeline."""
    task_id: str
    role: AgentRole
    description: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)  # task_ids


@dataclass(frozen=True)
class AgentResult:
    """Result produced by an agent after completing its task."""
    task_id: str
    role: AgentRole
    status: str  # "success", "failed", "partial"
    output_data: Dict[str, Any] = field(default_factory=dict)
    findings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class OrchestrationPlan:
    """A complete orchestration plan with ordered agent tasks."""
    plan_id: str
    schema_name: str
    tasks: List[AgentTask] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def task_count(self) -> int:
        return len(self.tasks)

    def get_tasks_by_role(self, role: AgentRole) -> List[AgentTask]:
        return [t for t in self.tasks if t.role == role]


@dataclass(frozen=True)
class OrchestrationResult:
    """Complete result of the multi-agent orchestration run."""
    plan_id: str
    results: List[AgentResult] = field(default_factory=list)
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def all_succeeded(self) -> bool:
        return all(r.status == "success" for r in self.results)

    @property
    def failed_tasks(self) -> List[AgentResult]:
        return [r for r in self.results if r.status == "failed"]

    @property
    def all_findings(self) -> List[str]:
        findings = []
        for r in self.results:
            findings.extend(r.findings)
        return findings


class AgentOrchestrationPort(Protocol):
    """Port for orchestrating multi-agent migration workflows."""

    async def create_plan(self, schema_name: str, tables: List[str]) -> OrchestrationPlan:
        """Create an orchestration plan for migrating a schema."""
        ...

    async def execute_plan(self, plan: OrchestrationPlan) -> OrchestrationResult:
        """Execute all tasks in an orchestration plan sequentially by dependency."""
        ...
