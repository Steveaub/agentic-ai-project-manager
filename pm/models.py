from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def uid() -> str:
    return uuid4().hex


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ProjectGoal(Contract):
    objective: str = Field(min_length=10, max_length=6000)


class ProjectConstraint(Contract):
    days: int = Field(ge=1, le=3650, default=60)
    budget: float = Field(gt=0, le=1e9, default=20000)
    team_size: int = Field(ge=1, le=100, default=4)


class ScopeRequirement(Contract):
    id: str = Field(pattern=r"^R[0-9]+$")
    description: str = Field(min_length=1, max_length=1000)
    mandatory: bool = True


class ProjectScope(Contract):
    asset: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1, le=1000)
    location: str = Field(max_length=200)
    site_ids: list[str] = Field(max_length=1000)
    deliverables: list[ScopeRequirement] = Field(min_length=1, max_length=30)


class ConfirmedRequirements(Contract):
    id: str = Field(default_factory=uid)
    goal: ProjectGoal
    constraints: ProjectConstraint
    scope: ProjectScope
    confirmed_at: str = Field(default_factory=now)
    provenance: dict = Field(default_factory=dict)
    unresolved_questions: list[str] = Field(default_factory=list)


class RequirementExtraction(Contract):
    goal: ProjectGoal
    form_constraints: ProjectConstraint | None = None


class RequirementConfirmation(Contract):
    draft_id: str
    confirmed: Literal[True]
    constraints: ProjectConstraint
    scope: ProjectScope
    resolution: str = Field(default="", max_length=2000)


class ProjectRequest(Contract):
    goal: ProjectGoal
    constraints: ProjectConstraint = Field(default_factory=ProjectConstraint)
    provider: Literal["demo", "openai", "gemini", "groq", "openrouter", "multi"] = "demo"
    confirmation_id: str | None = None


class FixedCostBreakdown(Contract):
    equipment: float = Field(ge=0, default=0)
    materials: float = Field(ge=0, default=0)
    logistics: float = Field(ge=0, default=0)
    permitting: float = Field(ge=0, default=0)
    contingency: float = Field(ge=0, default=0)
    includes_labor: bool = False
    basis: str = Field(default="", max_length=500)
    evidence: Literal["unverified_estimate", "user_provided"] = "unverified_estimate"


class Task(Contract):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    title: str = Field(min_length=1, max_length=200)
    deliverable: str = Field(min_length=1, max_length=200)
    duration: int = Field(ge=1, le=3650)
    people: int = Field(ge=1, le=100)
    daily_rate: float = Field(ge=0, le=100000)
    fixed_cost: float = Field(ge=0, le=1e8)
    source: Literal["demo_estimate", "ai_estimate", "user"]
    site_ids: list[str] = Field(default_factory=list, max_length=1000)
    phase: Literal["planning", "procurement", "implementation", "verification", "support"] = "support"
    cost_breakdown: FixedCostBreakdown | None = None


class Dependency(Contract):
    predecessor: str
    successor: str
    justification: Literal["none", "technical", "shared_equipment", "regulatory"] = "none"


class RequirementCoverage(Contract):
    requirement_id: str
    task_ids: list[str] = Field(max_length=80)
    exclusion_reason: str = Field(max_length=1000)


class LaborEstimate(Contract):
    daily_rate: float = Field(gt=0, le=10000)
    basis: str = Field(min_length=10, max_length=1000)
    source: Literal["unverified_model_estimate"]


class CostCategoryExclusion(Contract):
    category: Literal["equipment", "materials", "logistics", "permitting", "contingency"]
    reason: str = Field(min_length=1, max_length=500)


class Milestone(Contract):
    title: str
    task_id: str


class Resource(Contract):
    name: str
    capacity: int = Field(ge=1)


class BudgetItem(Contract):
    task_id: str
    labor: float
    fixed: float
    total: float


class Risk(Contract):
    title: str = Field(max_length=300)
    probability: Literal["low", "medium", "high"]
    impact: Literal["low", "medium", "high"]
    mitigation: str = Field(max_length=1500)
    source: Literal["calculated", "demo_estimate", "ai_estimate"]


ToolName = Literal["validate_wbs", "schedule", "budget", "resources", "review"]


class ToolInvocation(Contract):
    tool: ToolName


class AgentExecutionPlan(Contract):
    title: str = Field(min_length=1, max_length=200)
    tasks: list[Task] = Field(min_length=1, max_length=80)
    dependencies: list[Dependency] = Field(max_length=500)
    milestones: list[Milestone] = Field(max_length=80)
    assumptions: list[str] = Field(max_length=30)
    questions: list[str] = Field(max_length=20)
    risks: list[Risk] = Field(max_length=30)
    operations: list[ToolInvocation] = Field(min_length=5, max_length=5)
    confirmed_constraints: ProjectConstraint | None = None
    scope: ProjectScope | None = None
    requirement_coverage: list[RequirementCoverage] = Field(default_factory=list, max_length=30)
    exclusions: list[str] = Field(default_factory=list, max_length=30)
    estimation_notes: list[str] = Field(default_factory=list, max_length=30)
    cost_category_exclusions: list[CostCategoryExclusion] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def required_operations(self):
        if [o.tool for o in self.operations] != ["validate_wbs", "schedule", "budget", "resources", "review"]:
            raise ValueError("Required tool order: validate_wbs, schedule, budget, resources, review")
        return self


class AgentDecision(Contract):
    agent: str
    message: str
    timestamp: str = Field(default_factory=now)


class ToolResult(Contract):
    tool: str
    status: Literal["ok", "error"]
    output: dict
    duration_ms: float


class ProjectRevision(Contract):
    id: str = Field(default_factory=uid)
    number: int
    created_at: str = Field(default_factory=now)
    constraints: ProjectConstraint
    change: str
    plan: AgentExecutionPlan
    results: dict
    decisions: list[AgentDecision]
    trace: list[ToolResult]
    sources: list[dict]
    provider: Literal["demo", "openai", "gemini", "groq", "openrouter", "multi"]


class Project(Contract):
    id: str = Field(default_factory=uid)
    goal: ProjectGoal
    created_at: str = Field(default_factory=now)
    revisions: list[ProjectRevision]
    status: Literal["planned"] = "planned"


class ProjectScenario(Contract):
    constraints: ProjectConstraint
    change: str = Field(default="Constraint scenario", max_length=2000)
    provider: Literal["demo", "openai", "gemini", "groq", "openrouter", "multi"] = "demo"
    expected_revision: int = Field(ge=1)
    confirmation_id: str | None = None


class DocumentInput(Contract):
    name: str = Field(min_length=1, max_length=180)
    text: str = Field(min_length=1, max_length=100000)


class SearchInput(Contract):
    query: str = Field(min_length=1, max_length=2000)
