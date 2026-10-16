# Module Instructions — Procurement

These instructions apply to `grupo_real_tools/procurement/`.
Read the parent [AGENTS.md](../../AGENTS.md) before working in this module. Follow the root and any intermediate guides.
These instructions add module-specific requirements without weakening them.
If they conflict with parent instructions, ask the owner before proceeding.

## Required reading

- Read [README.md](README.md) before proposing work.
  It records the module's purpose, current implementation status, intended boundaries, and technical references.

## Module-specific rules

### State that must be verified

Do not confuse existing structure with completed functionality.
Before claiming that a flow is implemented, locate its controller, invocation, and test.
Revalidate the observations in [Implemented behavior](README.md#implemented-behavior) against current code before relying on them.

### Module model

- `Procurement` coordinates the process; it does not replace ERPNext's standard purchasing, inventory, or accounting documents.
- `Procurement Item Proposal` represents proposed information before a final `Item` necessarily exists.
- `Procurement Item` must not become a parallel copy of the Item master.
- Merchandise invoices, freight invoices, and additional costs must preserve their distinct identity and document traceability.
- Do not assume that an intended action such as `Configure Item` is implemented merely because its field exists.

### Structural UI work

- Follow the root rules for Frappe UI and generated metadata.
  Make structural changes in Desk and inspect regenerated files afterward without manually correcting them.
- If standard Desk configuration cannot express the required design,
  stop and present the limitation before proposing custom frontend behavior.

### Before expanding the flow

Present and obtain approval for:

1. The actual accepted input and who provides it.
2. The source-of-truth document at each stage.
3. The mapping among proposals, items, and variants.
4. The ERPNext documents that would be created and when they would be submitted.
5. Separate handling of merchandise, freight, and landed cost.
6. Idempotency, cancellation, and recovery from partial failures.
7. The exact files that would be modified.

Do not invent input formats, identifiers, or automation.
Do not add Excel/CSV, bulk imports, or external integrations without an explicit owner decision.

### Accounting and inventory boundaries

- Do not create, submit, or cancel real documents during a test without explicit authorization.
- Do not create inventory movements parallel to standard ERPNext documents.
- Do not combine merchandise and freight invoices when they represent separate obligations.
- Do not allocate landed cost until the allocation basis, currencies, rounding, and eligible documents have been defined.
- Every retry path must avoid duplicate Items, invoices, or costs.

### Responsibility boundaries

- Fields, layout, properties, labels, and permissions: DocType UI.
- Normalization, validation, and idempotency: Python backend.
- Non-structural form events and calls: JavaScript, only with explicit approval.
- Purchasing, receipt, inventory, and accounting: standard ERPNext documents.
- Process decisions and state: `Procurement`, without duplicating ERPNext ledgers.

## Verification

After authorized changes:

- inspect the complete diff and all Frappe-regenerated files;
- run `git diff --check`;
- check Python syntax without writing bytecode into the repository;
- add or update tests for the implemented behavior;
- test retries and rollback when related documents are created;
- verify that no standard documents are duplicated;
- clearly list every part that remains design-only.
