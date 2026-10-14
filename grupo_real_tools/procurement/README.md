# Procurement

## Purpose and scope

Procurement coordinates guided purchasing and item-configuration information. It does not replace ERPNext purchasing,
inventory, or accounting documents.

`Procurement Item Proposal` records proposed item information before a final `Item` necessarily exists. `Procurement
Item` is configuration for an item and must not become a parallel copy of the ERPNext Item master.

## Implemented behavior and verification status

At the time the module guide was introduced, `Procurement.before_validate` calculated proposal quantities and totals.
The Procurement JavaScript file had no operational behavior, and the integration tests were empty scaffolds.

The presence of fields or buttons does not establish that this module creates `Item`, `Purchase Invoice`, `Landed Cost
Voucher`, or other documents. Revalidate these observations against current code before relying on them in a technical
task.

## Intended workflow and boundaries

The intended process keeps separate records for merchandise invoices, freight invoices, and additional costs. Any
future automation must use standard ERPNext documents and preserve their traceability.

Before expanding the workflow, define accepted input, source documents, proposal-to-item mapping, creation and
submission points, landed-cost allocation, idempotency, cancellation, and recovery. Do not infer formats, identifiers,
or integrations.

## Technical documentation

Read [AGENTS.md](AGENTS.md) for module constraints, ERPNext boundaries, and required verification. Read the parent
[AGENTS.md](../../AGENTS.md) for shared repository rules.
