import pytest

from pm.agents import Requirements, demo_plan, run
from pm.models import ProjectConstraint, ProjectGoal


def test_live_handoff_and_bounded_repair_with_fake_transport(monkeypatch):
    """Exercises live orchestration with injected transport, never a paid API call."""
    calls = []
    class FakeProvider:
        calls = 0
        tokens = 0
        def call(self, schema, instructions, payload):
            self.calls += 1
            calls.append(payload)
            if schema is Requirements:
                return Requirements(requirements=["Checkout testing"], assumptions=[], questions=[])
            plan = demo_plan()
            for task in plan.tasks:
                task.source = "ai_estimate"
            if self.calls == 2:
                plan.dependencies[0].predecessor = "invalid"
            return plan
    monkeypatch.setattr("pm.agents.OpenAIProvider", FakeProvider)
    result = run(ProjectGoal(objective="Launch an e-commerce website"), ProjectConstraint(), "openai")
    assert calls[1]["requirements_handoff"]["requirements"] == ["Checkout testing"]
    assert "validation_error" in calls[2]
    assert result.results["execution"]["model_calls"] == 3


def test_invalid_live_repair_stops(monkeypatch):
    class BadProvider:
        calls = 0
        tokens = 0
        def call(self, schema, instructions, payload):
            self.calls += 1
            if schema is Requirements:
                return Requirements(requirements=[], assumptions=[], questions=[])
            plan = demo_plan()
            plan.dependencies[0].predecessor = "invalid"
            for task in plan.tasks:
                task.source = "ai_estimate"
            return plan
    monkeypatch.setattr("pm.agents.OpenAIProvider", BadProvider)
    with pytest.raises(ValueError, match="unknown"):
        run(ProjectGoal(objective="Launch a website"), ProjectConstraint(), "openai")
