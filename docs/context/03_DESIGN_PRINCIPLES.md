# Design Principles

## Principle 1

Detection before LLM.

Detection systems detect incidents.

LLMs explain incidents.

---

## Principle 2

LLMs remain outside the critical path.

System must continue functioning if:

- OpenAI fails
- Ollama fails
- Azure fails

---

## Principle 3

Everything async.

No expensive processing inside request handlers.

---

## Principle 4

Modular architecture.

Every major capability must be isolated.

---

## Principle 5

Extension over modification.

Prefer new workers and modules.

Avoid rewriting stable systems.

---

## Principle 6

Provider independence.

Business logic must never depend on a specific model provider.

---

## Principle 7

Traceability.

Every incident must be traceable.

Every action must be auditable.

---

## Principle 8

Verification is mandatory.

Actions are not considered successful until verified.