# ADR 0006: Personal input is not sent to models

- **Status**: accepted (2026-11-11)
- **Context**: Puzzle inputs are personal and must not be redistributed. Models still need to know
  the input format.
- **Decision**: Prompts contain the puzzle description and a shape preview of the input: the first
  5 lines, each cut to 120 characters, plus statistics (line count, maximum width, character set).
  The full input goes only to the sandbox. Example inputs come from the public puzzle text.
- **Consequences**: Less private data reaches the model provider. Programs must infer parameters
  from the input itself (rule 6 in the system prompt). A test asserts that lines beyond the preview
  never appear in a prompt.
