# Procurement

App overview: [Grupo Real Tools](../../README.md).
Development instructions: [AGENTS.md](AGENTS.md).

## Purpose and scope

Procurement coordinates guided purchasing and item-configuration information.
It does not replace ERPNext purchasing, inventory, or accounting documents.

`Procurement Item Proposal` records proposed item information before a final `Item` necessarily exists.
`Procurement Item` is configuration for an item and must not become a parallel copy of the ERPNext Item master.

## Implemented behavior

`Procurement.before_validate` calculates proposal subtotals, total quantity, and document totals.
The form script has no operational behavior, and the integration test file is a scaffold without test cases.

`Configure Item` is present in the form metadata but has no implemented action.
The module does not automate creation of `Item`, `Purchase Invoice`, or `Landed Cost Voucher` documents.

## Technical documentation

### Intended workflow and boundaries

The intended process keeps separate records for merchandise invoices, freight invoices, and additional costs.
Any future automation must use standard ERPNext documents and preserve their traceability.

Before expanding the workflow, define accepted input, source documents, proposal-to-item mapping,
creation and submission points, landed-cost allocation, idempotency, cancellation, and recovery.
Do not infer formats, identifiers, or integrations.
