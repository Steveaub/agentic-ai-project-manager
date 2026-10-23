"""Server-only configuration. Process environment takes precedence over this repo's .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def load_environment(path=ROOT / ".env"):
    # No interpolation: values are literal, never shell expressions or other secrets.
    load_dotenv(path, override=False, interpolate=False)


load_environment()

DEFAULT_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "gemini": "gemini-3.5-flash-lite",
    "openrouter": "nvidia/nemotron-3.5-super-vl:free",
}
FREE_MODELS = {
    "groq": {"openai/gpt-oss-120b", "openai/gpt-oss-20b"},
    "gemini": {"gemini-3.8-flash", "gemini-3.5-flash-lite"},
    "openrouter": {"nvidia/nemotron-3-super-120b-a12b:free", "nvidia/nemotron-3.5-super-vl:free"},
}


def model_for(provider):
    return os.getenv(provider.upper() + "_MODEL", DEFAULT_MODELS.get(provider, ""))


def config_error(provider):
    if provider == "openai":
        if os.getenv("PM_FREE_ONLY", "true") != "false" or os.getenv("PM_ALLOW_PAID_CALLS") != "true":
            return "OpenAI is disabled by the free-only policy; select Groq, Gemini or OpenRouter."
    elif provider not in FREE_MODELS or model_for(provider) not in FREE_MODELS[provider]:
        return "Model is not in Northstar's verified free-model allowlist. Check server configuration."
    if provider in {"groq", "gemini"} and os.getenv(f"PM_{provider.upper()}_FREE_TIER_CONFIRMED") != "true":
        return f"Confirm the {provider} account uses free-tier billing before enabling this provider."
    key = os.getenv(provider.upper() + "_API_KEY", "")
    if not key or key.startswith("replace-"):
        return f"Missing {provider.upper()}_API_KEY. Set it in the repository's local .env and restart."
    if not model_for(provider):
        return "Missing server-side model setting."
    return None


def role_assignments(provider):
    if provider != "multi":
        return {"requirements": provider, "planning": provider, "review": "none"}
    return {role: os.getenv(f"PM_{role.upper()}_PROVIDER", default) for role, default in
            [("requirements", "gemini"), ("planning", "groq"), ("review", "openrouter")]}


def public_config():
    # Only allowlisted model strings, status and role names; never return environment dictionaries.
    providers = []
    for name in ["gemini", "groq", "openrouter", "openai"]:
        error = config_error(name)
        model = model_for(name)
        providers.append({"provider": name, "model": model if model in FREE_MODELS.get(name, set()) else None,
                          "ready": error is None, "message": error})
    roles = role_assignments("multi")
    return {"providers": providers, "roles": {k: v if v in FREE_MODELS or v == "none" else "invalid"
                                               for k, v in roles.items()},
            "free_only": os.getenv("PM_FREE_ONLY", "true") != "false"}
