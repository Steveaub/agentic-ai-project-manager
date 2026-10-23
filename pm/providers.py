"""Bounded adapters. No raw provider errors, credentials, arbitrary endpoints or paid fallback."""
import json
import os
import time
from threading import Lock

import httpx
from pydantic import ValidationError

from .config import FREE_MODELS, config_error, model_for
from .models import now, uid


class ProviderError(RuntimeError):
    def __init__(self, message, code="provider_error", status=503, events=None):
        super().__init__(message)
        self.code, self.status, self.events = code, status, events or []


class OutputError(ProviderError):
    pass


ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models/",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}
_catalog_lock = Lock()
_verified = {}


def wire_schema(model):
    """Portable JSON Schema subset; full Pydantic constraints still apply after inference."""
    unsupported = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minItems", "maxItems",
                   "minLength", "maxLength", "pattern", "default", "title"}
    def clean(value):
        if isinstance(value, list):
            return [clean(v) for v in value]
        if isinstance(value, dict):
            result = {k: ({name: clean(sub) for name, sub in v.items()} if k == "properties" else clean(v))
                      for k, v in value.items() if k not in unsupported}
            if "const" in result:
                result["enum"] = [result.pop("const")]
            if "properties" in result:
                result["required"] = list(result["properties"])
            return result
        return value
    return clean(model.model_json_schema())


def token_count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def verify_openrouter(model, client):
    """Unauthenticated catalog check before sending credentials or inference. Five-minute cache."""
    with _catalog_lock:
        if _verified.get(model, 0) > time.monotonic():
            return
        try:
            response = client.get("https://openrouter.ai/api/v1/models", timeout=15)
            response.raise_for_status()
            entry = next((m for m in response.json()["data"] if m["id"] == model), None)
            if not entry or not model.endswith(":free"):
                raise ValueError()
            prices = entry.get("pricing", {})
            if any(float(prices.get(k, "-1")) != 0 for k in ("prompt", "completion")):
                raise ValueError()
            if any(float(v) != 0 for k, v in prices.items() if k not in {"discount"}):
                raise ValueError()
            if "structured_outputs" not in entry.get("supported_parameters", []):
                raise ValueError()
        except Exception:
            raise ProviderError("OpenRouter free-price/structured-output verification failed; no inference sent.",
                                "free_price_verification") from None
        _verified[model] = time.monotonic() + 300


class ChatAdapter:
    def __init__(self, provider, transport=None):
        error = config_error(provider)
        if error:
            raise ProviderError(error, "configuration")
        if provider not in ENDPOINTS:
            raise ProviderError("Unsupported free provider.", "configuration")
        self.provider, self.model, self.transport = provider, model_for(provider), transport

    def generate(self, schema, instructions, payload, timeout, output_tokens):
        body = {"model": self.model,
                "messages": [{"role": "system", "content": instructions},
                             {"role": "user", "content": json.dumps(payload)}],
                "max_tokens": output_tokens,
                "response_format": {"type": "json_schema", "json_schema": {
                    "name": schema.__name__, "strict": True, "schema": wire_schema(schema)}}}
        if self.provider in {"groq", "gemini"}:
            body["reasoning_effort"] = "low"
        if self.provider == "openrouter":
            body["provider"] = {"require_parameters": True, "allow_fallbacks": False,
                                "max_price": {"prompt": 0, "completion": 0, "request": 0}}
            # Catalog documents optional reasoning for this model; keep the review budget for JSON.
            body["reasoning"] = {"enabled": False}
        endpoint = ENDPOINTS[self.provider]
        headers = {"Authorization": "Bearer " + os.environ[self.provider.upper() + "_API_KEY"]}
        if self.provider == "gemini":
            endpoint += self.model + ":generateContent"
            headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}
            body = {"systemInstruction": {"parts": [{"text": instructions}]},
                    "contents": [{"role": "user", "parts": [{"text": json.dumps(payload)}]}],
                    "generationConfig": {"responseMimeType": "application/json",
                                         "responseJsonSchema": wire_schema(schema),
                                         "maxOutputTokens": output_tokens,
                                         "thinkingConfig": {"thinkingLevel": "low"}}}
        with httpx.Client(timeout=timeout, transport=self.transport, trust_env=False,
                          follow_redirects=False) as client:
            if self.provider == "openrouter":
                verify_openrouter(self.model, client)
            try:
                response = client.post(endpoint, json=body, headers=headers)
            except httpx.TimeoutException:
                raise ProviderError("Provider timed out; retry later. No project change was saved.", "timeout", 504) from None
            except httpx.HTTPError:
                raise ProviderError("Provider connection failed; retry later.", "connection") from None
        if response.status_code >= 400:
            code = response.status_code
            diagnostic = ""
            server_invalid_json = False
            try:
                raw_error = response.json().get("error", {})
                allowed = {"json_validate_failed", "json_generation_failed", "rate_limit_exceeded", "context_length_exceeded", "model_not_found", "invalid_request_error"}
                if raw_error.get("code") in allowed:
                    diagnostic = " Category: " + raw_error["code"] + "."
                if raw_error.get("code") == "json_validate_failed" and isinstance(raw_error.get("failed_generation"), str):
                    server_invalid_json = True
                    try:
                        schema.model_validate_json(raw_error["failed_generation"])
                        diagnostic += " Generated data passes local schema; provider schema compatibility failed."
                    except ValidationError as invalid:
                        kinds = sorted({e["type"] for e in invalid.errors(include_input=False)})
                        diagnostic += " Local validation categories: " + ", ".join(kinds) + "."
                # Emit only known schema keywords; never raw response text or failed generations.
                message = str(raw_error.get("message", ""))
                keywords = [k for k in ["additionalProperties", "required", "schema", "max_tokens", "temperature", "reasoning_effort", "strict", "length"] if k.lower() in message.lower()]
                diagnostic += " Check: " + ", ".join(keywords) + "." if keywords else ""
            except (ValueError, TypeError, AttributeError):
                pass
            explanations = {400: "Provider rejected the model, schema or context size. Check compatibility.",
                            401: "Provider rejected credentials. Check the local key without sharing it.",
                            403: "Provider access denied. Check model eligibility and account permissions.",
                            404: "Model or API endpoint unavailable. Check current model availability.",
                            402: "Provider requested payment. Request stopped; no paid fallback permitted.",
                            413: "Provider context limit exceeded. Reduce project/document context.",
                            429: "Provider free quota/rate limit reached. Wait for quota reset or select another free provider."}
            if server_invalid_json:
                raise OutputError("Provider rejected malformed generated JSON; one bounded repair is permitted.",
                                  "invalid_output", 422)
            raise ProviderError(explanations.get(code, "Provider unavailable; retry later.") + diagnostic,
                                f"http_{code}", 429 if code == 429 else 503)
        meta = {}
        try:
            data = response.json()
            if self.provider == "gemini":
                usage = data.get("usageMetadata", {})
                candidates = data.get("candidates", [])
                data = {"id": data.get("responseId"), "usage": {"prompt_tokens": usage.get("promptTokenCount"),
                        "completion_tokens": usage.get("candidatesTokenCount"), "total_tokens": usage.get("totalTokenCount")},
                        "choices": [{"finish_reason": "stop" if c.get("finishReason") == "STOP" else "length",
                                     "message": {"content": "".join(p.get("text", "") for p in c.get("content", {}).get("parts", []) if not p.get("thought"))}}
                                    for c in candidates]}
            choice = data["choices"][0]
            usage = data.get("usage") or {}
            meta = {"request_id": data.get("id"), "input_tokens": usage.get("prompt_tokens"),
                    "output_tokens": usage.get("completion_tokens"), "total_tokens": usage.get("total_tokens")}
            for field in ("input_tokens", "output_tokens", "total_tokens"):
                meta[field] = token_count(meta[field])
            meta["request_id"] = str(meta["request_id"])[:160] if meta["request_id"] else None
            if choice.get("finish_reason") in {"length", "content_filter"} or choice["message"].get("refusal"):
                raise OutputError("Provider response was truncated or refused; reduce plan size or retry later.", "incomplete")
            parsed = schema.model_validate_json(choice["message"]["content"])
            return parsed, meta
        except OutputError as exc:
            exc.metadata = meta
            raise
        except (ValueError, KeyError, TypeError, IndexError, ValidationError):
            error = OutputError("Provider returned invalid structured output. A bounded repair may be attempted.",
                                "invalid_output")
            error.metadata = meta
            raise error from None


class WorkflowSession:
    """One workflow budget shared across agents, repairs and explicit free fallbacks."""
    def __init__(self):
        self.events, self.calls, self.tokens = [], 0, 0
        self.deadline = time.monotonic() + 300
        self.max_calls = 6

    def call(self, provider, role, schema, instructions, payload):
        fallback = os.getenv(f"PM_{role.upper()}_FALLBACK_PROVIDER", "none")
        choices = [provider] + ([fallback] if fallback != "none" and fallback != provider else [])
        if any(p not in FREE_MODELS for p in choices):
            raise ProviderError("Role assignments and fallbacks must use verified free providers.", "configuration")
        for index, name in enumerate(choices):
            if self.calls >= self.max_calls or time.monotonic() >= self.deadline:
                raise ProviderError("Workflow call/time budget exhausted.", "budget", events=self.events)
            started = time.monotonic()
            event = {"id": uid(), "provider": name, "model": model_for(name), "role": role,
                     "timestamp": now(), "status": "error", "validation": "not_run"}
            try:
                adapter = ChatAdapter(name)
                event["model"] = adapter.model
                self.calls += 1
                event["inference_attempted"] = True
                tokens = 6500 if role in {"planning", "repair"} else 3500 if role == "review" else 1800
                parsed, meta = adapter.generate(schema, instructions, payload,
                                                min(60, self.deadline - time.monotonic()), tokens)
                event.update(meta)
                event.update(status="ok", validation="pydantic_valid")
                self.tokens += meta.get("total_tokens") or 0
                return parsed
            except ProviderError as exc:
                # Never retain raw exceptions/provider response bodies or headers.
                event.update(error_code=exc.code, error=str(exc))
                if exc.code == "free_price_verification":
                    event["inference_attempted"] = False
                metadata = getattr(exc, "metadata", {})
                event.update(metadata)
                self.tokens += metadata.get("total_tokens") or 0
                event["validation"] = "invalid" if isinstance(exc, OutputError) else "not_run"
                exc.events = self.events
                if index + 1 == len(choices) or exc.code in {"invalid_output", "incomplete"}:
                    raise
            finally:
                event["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
                # Bad config might contain a credential in a model field; never emit that field.
                if event["model"] not in FREE_MODELS.get(name, set()):
                    event["model"] = None
                self.events.append(event)

    def summary(self):
        return {"model_calls": sum(bool(e.get("inference_attempted")) for e in self.events),
                "budgeted_attempts": self.calls, "reported_tokens": self.tokens, "invocations": self.events,
                "max_model_calls": self.max_calls, "max_output_tokens_per_call": 6500,
                "workflow_timeout_seconds": 300, "free_only": True,
                "model": next((e["model"] for e in self.events if e["role"] == "planning"), None)}
