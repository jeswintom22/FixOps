# Coding Standards

## General

- Python 3.12+
- Type hints required
- Pydantic models preferred
- Async-first design

---

## Services

Services should contain business logic.

No business logic inside API routes.

---

## API Layer

API routes should:

- Validate input
- Call services
- Return responses

Nothing else.

---

## Workers

Workers should:

- Be small
- Have one responsibility
- Be independently deployable

---

## Logging

All logs must include:

- trace_id
- service
- timestamp

---

## Testing

Every new module should include tests.

---

## Architecture

Never bypass service layers.

Never directly couple modules.