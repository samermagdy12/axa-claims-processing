"""Provider-neutral OpenAI-compatible tool-calling loop for claim analysis."""
from __future__ import annotations

import json
from typing import Any
import httpx

from app.claim_analysis_llm import ClaimAnalysisError, GROQ_CHAT_COMPLETIONS_URL, OPENROUTER_CHAT_COMPLETIONS_URL, _analysis_prompt
from app.claim_tools import ClaimToolExecutor, TOOL_SCHEMAS
from app.config import settings

MAX_ROUNDS, MAX_TOOL_CALLS, MAX_IDENTICAL_CALLS = 8, 16, 2


def analyze_claim_with_tools(executor: ClaimToolExecutor) -> dict[str, Any]:
    providers = (("openrouter", OPENROUTER_CHAT_COMPLETIONS_URL, settings.OPENROUTER_API_KEY, settings.OPENROUTER_LLM_MODEL), ("groq", GROQ_CHAT_COMPLETIONS_URL, settings.GROQ_API_KEY, settings.GROQ_LLM_MODEL))
    errors = []
    for name, url, key, model in providers:
        if not key or not model:
            errors.append(f"{name} not configured"); continue
        executor.provider = name
        try: return _run_provider_loop(url, key, model, executor)
        except ClaimAnalysisError as exc: errors.append(str(exc))
    raise ClaimAnalysisError("Claim analysis tool loop unavailable: " + "; ".join(errors))


def _run_provider_loop(url: str, api_key: str, model: str, executor: ClaimToolExecutor) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": _analysis_prompt() + " You have tools. Obtain evidence using tools; call validate_claim and search_policy_docs before approve_or_route_claim. You must submit your recommendation through approve_or_route_claim, then provide a short final response."}, {"role": "user", "content": json.dumps({"claim_id": executor.claim_id, "instruction": "Analyze only this claim using tools."})}]
    calls, repeats = 0, {}
    for _ in range(MAX_ROUNDS):
        payload = {"model": model, "temperature": 0, "messages": messages, "tools": TOOL_SCHEMAS, "tool_choice": "auto"}
        try:
            response = httpx.post(url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=settings.CLAIM_ANALYSIS_TIMEOUT_SECONDS)
            response.raise_for_status(); message = response.json()["choices"][0]["message"]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise ClaimAnalysisError("Tool-calling provider response failed") from exc
        tool_calls = message.get("tool_calls") or []
        messages.append({"role": "assistant", "content": message.get("content"), "tool_calls": tool_calls} if tool_calls else {"role": "assistant", "content": message.get("content", "")})
        if not tool_calls:
            if executor.submission:
                return {**executor.submission, "provider": executor.provider, "tool_trace": list(executor.retrieved)}
            raise ClaimAnalysisError("Model ended without submitting approve_or_route_claim")
        for call in tool_calls:
            calls += 1
            if calls > MAX_TOOL_CALLS: raise ClaimAnalysisError("Tool call limit exceeded")
            function = call.get("function") or {}; name, raw = function.get("name"), function.get("arguments", "{}")
            try: arguments = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError: arguments = {}
            fingerprint = f"{name}:{json.dumps(arguments, sort_keys=True, default=str)}"; repeats[fingerprint] = repeats.get(fingerprint, 0) + 1
            if repeats[fingerprint] > MAX_IDENTICAL_CALLS: raise ClaimAnalysisError("Repeated identical tool call limit exceeded")
            result = executor.execute(str(name), arguments if isinstance(arguments, dict) else {})
            messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": json.dumps(result, default=str)})
    raise ClaimAnalysisError("Tool-calling round limit exceeded")
