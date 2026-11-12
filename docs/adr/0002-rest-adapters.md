# ADR 0002: Plain REST adapters for Foundry models

- **Status**: accepted (2026-11-11)
- **Context**: GPT-6.1 Sol uses the Foundry OpenAI v1 **Responses API**. Claude Opus 5.5 uses the
  **Claude Messages API in Foundry**. Their schemas differ: `reasoning.effort` and `text.format`
  on one side, `thinking: adaptive` and `output_config.effort/format` on the other. Some details
  were unverified at design time: which effort values Sol accepts, and whether Foundry's Claude
  endpoint supports `output_config.format`.
- **Decision**: Both adapters (`app/models/responses_adapter.py`, `app/models/messages_adapter.py`)
  call REST directly with `httpx`, behind the `ModelProvider` interface.
  - They share one infra-retry helper (`post_with_retry`) that handles 429/5xx/network errors and
    honours `Retry-After`.
  - Auth is an Entra ID token for `https://ai.azure.com/.default`; API keys are optional.
  - If the deployment rejects `output_config.format`, the Messages adapter falls back to JSON in a
    fenced block, and remembers that for later calls.
  - Reasoning and thinking content is discarded and never persisted (FR-038).
  - `temperature`, `top_p` and `top_k` are never sent.
- **Consequences**: Request shapes are visible and unit-tested with mocked transports. Changes to
  either API are isolated to one file. Infra failures raise `ModelInfraError`, which pauses the run
  without consuming a solving attempt.
- **Rejected**: the vendor SDKs (`openai`, `anthropic` `AnthropicFoundry`). They work, but they hide
  the request shape and need two retry stacks.
