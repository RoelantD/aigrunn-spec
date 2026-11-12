"""Model adapters and Dynamic Sessions executor against mocked HTTP (T021, T022, scenario I/J)."""

import base64
import json

import httpx
import pytest

from app.execution.base import ExecutionInfraError
from app.execution.dynamic_sessions import DynamicSessionsExecutor
from app.execution.harness import MARKER_END, MARKER_START
from app.models.base import ModelInfraError, ModelOutputError, ModelRequest
from app.models.messages_adapter import MessagesAdapter
from app.models.responses_adapter import ResponsesAdapter

SCHEMA = {"type": "object", "required": ["reply"], "properties": {"reply": {"type": "string"}},
          "additionalProperties": False}
REQ = ModelRequest(system="sys", user="usr", schema=SCHEMA, schema_name="ping", effort="medium",
                   max_output_tokens=1000)


async def _nosleep(_):
    return None


async def _token():
    return "entra-token-xyz"


def responses_adapter(handler):
    return ResponsesAdapter(key="workhorse", display_name="Sol", base_url="https://r.openai.azure.com/openai/v1",
                            deployment="sol-deploy", token_fn=_token, transport=httpx.MockTransport(handler),
                            sleep=_nosleep)


async def test_responses_request_and_usage():
    seen = []

    def handler(req):
        seen.append(req)
        return httpx.Response(200, json={
            "status": "completed",
            "output": [{"type": "reasoning", "summary": [{"text": "HIDDEN"}]},
                       {"type": "message", "content": [{"type": "output_text", "text": '{"reply": "pong"}'}]}],
            "usage": {"input_tokens": 11, "output_tokens": 22, "output_tokens_details": {"reasoning_tokens": 7}}})

    r = await responses_adapter(handler).generate(REQ)
    body = json.loads(seen[0].content)
    assert str(seen[0].url) == "https://r.openai.azure.com/openai/v1/responses"
    assert seen[0].headers["authorization"] == "Bearer entra-token-xyz"
    assert body["model"] == "sol-deploy" and body["reasoning"] == {"effort": "medium"}
    assert body["text"]["format"]["type"] == "json_schema" and body["text"]["format"]["strict"] is True
    assert "temperature" not in body
    assert r.data == {"reply": "pong"} and r.usage.reasoning_tokens == 7 and r.usage.output_tokens == 22
    assert "HIDDEN" not in r.raw_text  # reasoning items are discarded (FR-038)


async def test_responses_infra_retry_then_success():
    n = {"i": 0}
    retries = []

    def handler(req):
        n["i"] += 1
        if n["i"] < 3:
            return httpx.Response(429, headers={"retry-after": "1"})
        return httpx.Response(200, json={"output_text": '{"reply": "ok"}', "usage": {}})

    a = responses_adapter(handler)

    async def on_retry(status, wait):
        retries.append(status)

    a.on_retry = on_retry
    r = await a.generate(REQ)
    assert r.data["reply"] == "ok" and retries == [429, 429]


async def test_responses_persistent_outage_is_infra_error():
    a = responses_adapter(lambda req: httpx.Response(503))
    with pytest.raises(ModelInfraError):
        await a.generate(REQ)


async def test_responses_bad_output_is_output_error():
    a = responses_adapter(lambda req: httpx.Response(200, json={"output_text": "not json", "usage": {}}))
    with pytest.raises(ModelOutputError):
        await a.generate(REQ)
    a2 = responses_adapter(lambda req: httpx.Response(200, json={"status": "incomplete", "incomplete_details":
                                                                   {"reason": "max_output_tokens"}, "usage": {}}))
    with pytest.raises(ModelOutputError, match="max_output_tokens"):
        await a2.generate(REQ)


def messages_adapter(handler, api_key=None):
    return MessagesAdapter(key="escalation", display_name="Opus", base_url="https://m.services.ai.azure.com/anthropic",
                           deployment="opus-deploy", token_fn=None if api_key else _token, api_key=api_key,
                           transport=httpx.MockTransport(handler), sleep=_nosleep)


async def test_messages_request_shape_and_thinking_discarded():
    seen = []

    def handler(req):
        seen.append(req)
        return httpx.Response(200, json={"stop_reason": "end_turn", "usage": {"input_tokens": 5, "output_tokens": 9},
                                         "content": [{"type": "thinking", "thinking": "SECRET THOUGHTS"},
                                                     {"type": "text", "text": '{"reply": "pong"}'}]})

    r = await messages_adapter(handler, api_key="k-abc").generate(REQ)
    body = json.loads(seen[0].content)
    assert str(seen[0].url) == "https://m.services.ai.azure.com/anthropic/v1/messages"
    assert seen[0].headers["anthropic-version"] == "2023-06-01" and seen[0].headers["x-api-key"] == "k-abc"
    assert body["thinking"] == {"type": "adaptive"} and body["output_config"]["effort"] == "medium"
    assert body["output_config"]["format"]["type"] == "json_schema"
    for k in ("temperature", "top_p", "top_k"):
        assert k not in body
    assert r.data == {"reply": "pong"} and "SECRET" not in r.raw_text


async def test_messages_structured_output_fallback():
    calls = []

    def handler(req):
        body = json.loads(req.content)
        calls.append(body)
        if "format" in body["output_config"]:
            return httpx.Response(400, json={"error": {"message": "output_config.format: unsupported"}})
        return httpx.Response(200, json={"stop_reason": "end_turn", "usage": {},
                                         "content": [{"type": "text", "text": '```json\n{"reply": "x"}\n```'}]})

    a = messages_adapter(handler)
    r = await a.generate(REQ)
    assert r.data == {"reply": "x"} and r.notes and a.structured_output_supported is False
    await a.generate(REQ)
    assert len(calls) == 3  # third call skips the unsupported format directly


async def test_messages_refusal():
    a = messages_adapter(lambda req: httpx.Response(200, json={"stop_reason": "refusal", "content": [], "usage": {}}))
    with pytest.raises(ModelOutputError, match="refused"):
        await a.generate(REQ)


def _harness_stdout(results, load_error=None):
    payload = {"load_error": load_error, "results": results, "stdout": ""}
    return MARKER_START + base64.b64encode(json.dumps(payload).encode()).decode() + MARKER_END


def executor(handler):
    return DynamicSessionsExecutor(pool_endpoint="https://eastus.dynamicsessions.io/subscriptions/s/pools/p",
                                   token_fn=_token, transport=httpx.MockTransport(handler), sleep=_nosleep)


async def test_dynamic_sessions_success():
    seen = []

    def handler(req):
        seen.append(req)
        return httpx.Response(200, json={"status": "Succeeded", "result": {
            "stdout": _harness_stdout([{"index": 0, "output": "6", "error": None, "duration_ms": 1}]),
            "stderr": "", "executionTimeInMilliseconds": 12}})

    ex = executor(handler)
    sid = ex.new_session_id()
    out = await ex.run_cases("def solve(t): ...", ["1 2 3\n"], 30, sid)
    assert out.status == "ok" and out.results[0].output == "6" and out.correlation_id == sid
    req = seen[0]
    assert "api-version=2025-10-02-preview" in str(req.url) and f"identifier={sid}" in str(req.url)
    body = json.loads(req.content)
    assert body["timeoutInSeconds"] == 30 and body["codeInputType"] == "Inline"
    assert "entra-token-xyz" not in body["code"] and "session=" not in body["code"]  # no secrets in sandbox


async def test_dynamic_sessions_timeout_and_crash():
    ex = executor(lambda req: httpx.Response(200, json={"status": "Failed", "error": "Execution timed out",
                                                        "result": {"stdout": "", "stderr": ""}}))
    out = await ex.run_cases("x", ["a"], 5, "aps-1")
    assert out.status == "timeout" and out.timed_out
    ex2 = executor(lambda req: httpx.Response(200, json={"status": "Succeeded", "result": {"stdout": "", "stderr":
                                                                                         "Killed"}}))
    out2 = await ex2.run_cases("x", ["a"], 5, "aps-2")
    assert out2.status == "error" and "Killed" in out2.stderr


async def test_dynamic_sessions_wrapped_body_fallback_and_auth_error():
    def handler(req):
        body = json.loads(req.content)
        if "properties" not in body:
            return httpx.Response(400, text="properties required")
        return httpx.Response(200, json={"properties": {"status": "Succeeded", "stdout": _harness_stdout([]),
                                                        "stderr": ""}})

    ex = executor(handler)
    out = await ex.run_cases("x", [], 5, "aps-3")
    assert out.status == "ok" and ex.wrap_body
    with pytest.raises(ExecutionInfraError, match="Session Executor"):
        await executor(lambda req: httpx.Response(403)).run_cases("x", [], 5, "aps-4")
    with pytest.raises(ExecutionInfraError):
        await executor(lambda req: httpx.Response(503)).run_cases("x", [], 5, "aps-5")
