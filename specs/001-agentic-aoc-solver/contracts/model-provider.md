# Model Provider Contract

```python
class ModelProvider(Protocol):
    key: str                 # "workhorse" | "escalation"
    display_name: str        # e.g. "GPT-6.1 Sol"
    async def generate(req: ModelRequest) -> ModelResponse
```

`ModelRequest`: `system: str` (trusted instructions), `user: str` (contains delimited untrusted
blocks), `schema: dict` (JSON Schema), `schema_name: str`, `effort: str`, `max_output_tokens: int`.

`ModelResponse`: `data: dict` (validated against schema), `raw_text: str`, `usage:
{input_tokens, output_tokens, reasoning_tokens|None}`, `latency_ms`, `deployment`.

Errors: `ModelInfraError` (429/5xx/network/timeout after retries — not a solving failure),
`ModelOutputError` (unparseable/invalid JSON, refusal — counts as a failed attempt).

## Adapters

- `ResponsesAdapter` → `POST {base}/responses` (Foundry v1). Body: `model`, `instructions`,
  `input`, `reasoning.effort`, `max_output_tokens`, `text.format = {type: json_schema, name,
  schema, strict: true}`.
- `MessagesAdapter` → `POST {base}/v1/messages`, header `anthropic-version: 2023-06-01`. Body:
  `model`, `max_tokens`, `system`, `messages`, `thinking: {type: adaptive}`,
  `output_config: {effort, format: {type: json_schema, schema}}`; on HTTP 400 mentioning
  `output_config`/`format` retry once without `format` and require a fenced JSON block.
- Auth for both: `AzureTokenProvider(scope="https://ai.azure.com/.default")` via
  `DefaultAzureCredential`, or API key (`api-key` / `x-api-key`) when configured.
- Infra retry: up to 5 tries, backoff `min(60, 2^n)` s or `Retry-After`.

## Structured output: `SolutionProposal`

```json
{
  "summary": "string — 1-3 sentences restating the task",
  "algorithm": "string — approach in plain language",
  "complexity": "string — e.g. O(n log n)",
  "diagnosis": "string — for repairs: what was wrong (empty otherwise)",
  "examples": [{"input": "verbatim example input", "expected_output": "string|null", "note": "string"}],
  "code": "complete Python module defining solve(input_text: str) -> str"
}
```
