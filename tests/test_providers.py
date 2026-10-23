import json

import httpx
import pytest

from pm.agents import Requirements
from pm.config import load_environment, public_config
from pm.providers import ChatAdapter, OutputError, ProviderError, WorkflowSession, wire_schema


@pytest.fixture
def configured(monkeypatch):
    for provider in ["groq", "gemini", "openrouter"]:
        monkeypatch.setenv(provider.upper() + "_API_KEY", "unit-test-placeholder-not-a-real-key")
        monkeypatch.setenv(f"PM_{provider.upper()}_FREE_TIER_CONFIRMED", "true")
    monkeypatch.setenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
    from pm.providers import _verified
    _verified.clear()


def test_dotenv_preserves_process_precedence_and_literal_values(tmp_path, monkeypatch):
    file = tmp_path / ".env"
    file.write_text('LOCAL_UNIT_SETTING="literal ${NO_INTERPOLATION}"\nEXISTING_UNIT_SETTING=changed\n')
    monkeypatch.setenv("EXISTING_UNIT_SETTING", "original")
    monkeypatch.delenv("LOCAL_UNIT_SETTING", raising=False)
    load_environment(file)
    import os
    assert os.getenv("EXISTING_UNIT_SETTING") == "original"
    assert os.getenv("LOCAL_UNIT_SETTING") == "literal ${NO_INTERPOLATION}"


def completion(content=None):
    return {"id": "mock-request", "choices": [{"finish_reason": "stop", "message": {
        "content": content or json.dumps({"requirements": ["Solar deployment"], "assumptions": [], "questions": []})}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}}


@pytest.mark.parametrize("provider", ["gemini", "groq", "openrouter"])
def test_compatible_adapters_validate_and_report_usage(configured, provider):
    def handle(request):
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "nvidia/nemotron-3-super-120b-a12b:free",
                "pricing": {"prompt": "0", "completion": "0"}, "supported_parameters": ["structured_outputs"]}]})
        payload = json.loads(request.content)
        if provider == "gemini":
            assert payload["generationConfig"]["responseMimeType"] == "application/json"
            assert "x-goog-api-key" in request.headers
            return httpx.Response(200, json={"responseId": "mock-gemini", "candidates": [{"finishReason": "STOP",
                "content": {"parts": [{"text": completion()["choices"][0]["message"]["content"]}]}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20, "totalTokenCount": 30}})
        assert payload["response_format"]["json_schema"]["strict"] is True
        if provider == "openrouter":
            assert payload["provider"]["allow_fallbacks"] is False
            assert payload["provider"]["max_price"] == {"prompt": 0, "completion": 0, "request": 0}
            assert "models" not in payload
        return httpx.Response(200, json=completion())
    result, meta = ChatAdapter(provider, httpx.MockTransport(handle)).generate(Requirements, "Extract", {}, 2, 100)
    assert result.requirements == ["Solar deployment"]
    assert meta["total_tokens"] == 30


@pytest.mark.parametrize("status,code", [(429, "http_429"), (401, "http_401"), (402, "http_402"), (404, "http_404"), (500, "http_500")])
def test_sanitized_errors(configured, status, code):
    adapter = ChatAdapter("groq", httpx.MockTransport(lambda r: httpx.Response(status, text="SECRET DO NOT ECHO")))
    with pytest.raises(ProviderError) as error:
        adapter.generate(Requirements, "Extract", {}, 2, 100)
    assert error.value.code == code
    assert "SECRET" not in str(error.value)


def test_malformed_json_is_repairable_output_error(configured):
    adapter = ChatAdapter("groq", httpx.MockTransport(lambda r: httpx.Response(200, json=completion("{bad"))))
    with pytest.raises(OutputError):
        adapter.generate(Requirements, "Extract", {}, 2, 100)


def test_wire_schema_keeps_title_property():
    from pm.models import AgentExecutionPlan
    schema = wire_schema(AgentExecutionPlan)
    assert "title" in schema["properties"]
    assert "title" in schema["$defs"]["Task"]["properties"]


def test_paid_model_and_unconfirmed_account_fail_closed(configured, monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL", "paid/model")
    with pytest.raises(ProviderError, match="allowlist"):
        ChatAdapter("openrouter")
    monkeypatch.setenv("PM_GROQ_FREE_TIER_CONFIRMED", "false")
    with pytest.raises(ProviderError, match="free-tier"):
        ChatAdapter("groq")


def test_openrouter_changed_price_blocks_before_inference(configured):
    seen = []
    def handle(request):
        seen.append(request.method)
        return httpx.Response(200, json={"data": [{"id": "nvidia/nemotron-3-super-120b-a12b:free",
            "pricing": {"prompt": "1", "completion": "0"}, "supported_parameters": ["structured_outputs"]}]})
    with pytest.raises(ProviderError, match="verification failed"):
        ChatAdapter("openrouter", httpx.MockTransport(handle)).generate(Requirements, "Extract", {}, 2, 100)
    assert seen == ["GET"]


def test_shared_execution_budget(configured):
    session = WorkflowSession()
    session.calls = 4
    with pytest.raises(ProviderError, match="budget"):
        session.call("groq", "requirements", Requirements, "Extract", {})


def test_public_configuration_never_contains_keys(configured):
    assert "unit-test-placeholder" not in json.dumps(public_config())


def test_timeout_is_sanitized(configured):
    def handle(request):
        raise httpx.ReadTimeout("SECRET", request=request)
    with pytest.raises(ProviderError, match="timed out") as error:
        ChatAdapter("groq", httpx.MockTransport(handle)).generate(Requirements, "Extract", {}, 2, 100)
    assert "SECRET" not in str(error.value)


def test_server_json_rejection_enters_bounded_repair(configured):
    transport = httpx.MockTransport(lambda r: httpx.Response(400, json={"error": {
        "code": "json_validate_failed", "failed_generation": "{invalid", "message": "SECRET"}}))
    with pytest.raises(OutputError, match="bounded repair") as error:
        ChatAdapter("groq", transport).generate(Requirements, "Extract", {}, 2, 100)
    assert "SECRET" not in str(error.value)


def test_explicit_free_fallback_uses_shared_budget(configured, monkeypatch):
    monkeypatch.setenv("PM_REQUIREMENTS_FALLBACK_PROVIDER", "gemini")
    def generate(self, *args):
        if self.provider == "groq":
            raise ProviderError("Quota reached", "http_429", 429)
        return Requirements(requirements=["Fallback"], assumptions=[], questions=[]), {"total_tokens": 5}
    monkeypatch.setattr(ChatAdapter, "generate", generate)
    session = WorkflowSession()
    result = session.call("groq", "requirements", Requirements, "Extract", {})
    assert result.requirements == ["Fallback"]
    assert session.calls == 2
    assert [e["provider"] for e in session.events] == ["groq", "gemini"]


def test_paid_fallback_rejected_before_any_request(configured, monkeypatch):
    monkeypatch.setenv("PM_REQUIREMENTS_FALLBACK_PROVIDER", "openai")
    session = WorkflowSession()
    with pytest.raises(ProviderError, match="verified free"):
        session.call("groq", "requirements", Requirements, "Extract", {})
    assert session.calls == 0
