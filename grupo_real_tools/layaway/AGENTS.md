# Layaway Module Guide

These instructions apply to the entire `grupo_real_tools/layaway/` tree. They
specialize the root `AGENTS.md` but must not weaken its authorization, safety,
language, or Frappe UI rules.

## Functional source

- Read `README.md` before proposing work in this module.
- Treat the README as intended design, not as evidence that behavior is already
  implemented.
- If the README is empty or incomplete, state that limitation and use only
  requirements approved in the conversation; do not invent missing decisions.
- Explicitly distinguish the current phase, future architecture, and pending
  business rules.
- If the README and implemented behavior differ, present the discrepancy before
  choosing which one to preserve.

## Module intent

`Layaway` is the business document that orchestrates a merchandise reservation
lifecycle. ERPNext remains authoritative for its standard documents:

```text
Layaway
├── Sales Order
│   └── Stock Reservation
├── Payment Entry(s)
└── Completion / Expiration / Forfeiture
```

Do not duplicate sales, payment, inventory, or accounting concepts that already
belong to ERPNext.

## Phase discipline

Work only within the authorized phase. Completing one phase does not authorize
starting the next phase.

### Phase 1 — Visual structure

- Create and arrange `Layaway`, `Layaway Item`, and `Layaway Settings` through
  the DocType UI.
- Represent the customer, reservation, items, payment summary, expiration,
  payment history, terms, and audit information visually.
- Fields may remain structural or act as placeholders until their logic is
  authorized.
- Prefer standard Frappe capabilities: sections, columns, tables, read-only
  fields, and declarative dependencies configured in Desk.

### Phase 2 — ERPNext links

- Link standard documents only after specific approval.
- Define ownership, cardinality, cancellation behavior, and traceability for
  each link before implementation.

### Phase 3 — Rules and transitions

- Implement limits, calculations, expiration, states, and accounting actions
  only after each flow is documented and approved.
- Keep definitive validation and state transitions in the backend.

## Absolute UI rule

- Never manually edit DocType JSON or an auto-generated type block.
- Never create, order, or modify fields, sections, columns, properties,
  permissions, or layout through Python, JavaScript, patches, console commands,
  or fixtures.
- Do not construct the form with client-side code.
- Make every structural or visual change in Desk, then inspect the regenerated
  diff.
- If the required layout cannot be achieved with the standard UI, stop and ask
  for a decision before adding custom frontend behavior.

## Phase 1 boundaries

While authorization is limited to Phase 1, do not implement:

- `Sales Order` creation or cancellation;
- `Payment Entry` creation, aggregation, or allocation;
- inventory reservation or release;
- per-customer item or amount limits;
- minimum-deposit enforcement;
- automatic 30-day expiration or days-remaining calculations;
- scheduled jobs, notifications, or a state machine;
- completion, expiration, or forfeiture behavior;
- journal entries, forfeited-deposit income, or invoicing;
- reports, external synchronization, or WhatsApp integration.

In Phase 1, payment history must remain a visual location only. Do not create an
accounting child table that duplicates `Payment Entry`.

## Before implementation

Present the following to the owner:

1. DocTypes to create or modify.
2. Proposed fields, types, options, and layout.
3. Files that Frappe will regenerate or that would otherwise be modified.
4. Differences between the proposal and repository conventions.
5. Everything explicitly excluded from the increment.

Do not continue until explicit authorization is received.

## Responsibility boundaries

- Fields, layout, properties, labels, and permissions: DocType UI.
- Definitive validation and business rules: Python controller, when its phase is
  authorized.
- Non-structural form events and feedback: JavaScript, only with explicit
  approval.
- Commercial documents, payments, inventory, and accounting: standard ERPNext
  DocTypes.
- Configurable rules: `Layaway Settings`; do not hardcode them when their
  implementation phase arrives.

## Required verification

After authorized changes:

- inspect Frappe-regenerated files without correcting them manually;
- run `git diff --check`;
- confirm that all three DocTypes install or migrate correctly;
- verify basic creation and editing with controlled data;
- confirm that the items table works structurally;
- confirm that no later-phase automation was introduced;
- show the final diff and list every pending decision.
