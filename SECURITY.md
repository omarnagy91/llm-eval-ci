# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |

## Reporting a vulnerability

Email **omar@neurascale.org** with a description, reproduction steps, and the impact you see. Do not open a public issue for security problems.

You can expect an acknowledgment within 72 hours and a status update within 7 days. This is a solo-maintained project; fixes for confirmed issues are prioritized ahead of all other work.

## Scope notes

- `llm-eval-ci run --system path.py` imports and executes the given Python module by design. Treat system adapters and eval configs as code: only run files you trust, especially in CI on pull requests from forks.
- The `openai` and `anthropic` judge backends read `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` from the environment and send golden-set content (inputs, context, references, candidate outputs) to the respective API. Do not put secrets inside golden sets.
- The default `heuristic` judge is fully offline and sends nothing anywhere.
