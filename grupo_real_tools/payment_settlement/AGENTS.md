# Module Instructions — Payment Settlement

These instructions apply to `grupo_real_tools/payment_settlement/`.
Read the parent [AGENTS.md](../../AGENTS.md) before working in this module. Follow the root and any intermediate guides.
These instructions add module-specific requirements without weakening them.
If they conflict with parent instructions, ask the owner before proceeding.

## Required reading

- Read [README.md](README.md) before proposing changes.
  It describes implemented behavior, known limitations, and required regression scenarios.

## Module-specific rules

### Module intent

This module does not pay invoices.
It settles collection events that have already reached clearing accounts and creates an explainable, auditable `Journal Entry`.

Do not assume that every component is a tax or that a withholding is recoverable.
The selected account is the primary source of accounting meaning.

### Invariants that must be preserved

1. A Template is a recipe; an Entry is a transactional snapshot.
2. A Template may include several `Mode of Payment` values, but the same value must not appear in more than one row.
3. `Clearing Account` is derived from the `Mode of Payment` and company.
4. Each structural row maps one clearing account to one settlement account.
5. `Bank Account` is optional. A Template bank propagates to its corresponding Settlement row.
   User-added Manual rows resolve their bank from the current ledger account and company; missing matches stay empty.
6. References represent collection events, not complete invoices.
7. The duplication key is `(reference_doctype, reference_name, reference_row_name)`.
8. `Apply To` points to an Entry clearing account.
9. Clearing amounts are automatic. Settlement amounts are calculated for `Automatic` and preserved for `Manual`.
   Only one Manual Settlement row is allowed per destination account; it takes precedence over Automatic rows.
10. Manual components use debit and credit in account currency.
11. Totals and `difference` are expressed in company currency.
12. Submit requires `difference == 0`.
13. The `Journal Entry` must produce exactly the same base amounts as the Settlement.
14. Cancelling the Settlement must cancel the linked `Journal Entry`.
15. Definitive accounting logic and validation belong to the backend; JavaScript only orchestrates non-structural UI behavior.

### Component type semantics

Preserve the component types and allowed calculation methods documented in the
[component model](README.md#payment-settlement-entry-component).
Do not treat an allowed calculation method as proof that its calculation engine is implemented.
Do not change signs without tracing a complete accounting case through the
[component calculations](README.md#2-components-and-apply-to).

### Currencies

- A clearing row uses the real aggregate rate of its references: `base_amount / amount`.
- A row in company currency uses a rate of 1.
- Other rows obtain the rate for the accounting date if one has not already been provided.
- When a component and destination share a currency, apply the amount directly in that currency.
- When their currencies differ, convert through base amounts and the destination rate.
- Do not hide exchange differences by silently changing the cash residual.

### Implemented reference sources

Do not claim support for a source without finding its query in `doctype/payment_settlement_entry/references.py`.
Consult the [reference model](README.md#payment-settlement-entry-reference) and
[documented limitations](README.md#known-mvp-limitations) for the supported sources and exclusions.

### Bank Account path

Preserve the Template-derived bank path and Manual bank resolution described in
[Generated Journal Entry](README.md#generated-journal-entry).
Supply each component's Bank Account explicitly during server-side journal creation; do not rely on client events.
Resolve Manual bank links from the current ledger account and company, clearing stale links after account changes.
Allow accounts without a matching Bank Account, including POS clearing accounts.

### Responsibility boundaries

- Calculations, reference orchestration, submit, and cancellation: `payment_settlement_entry.py`.
- Source queries: `doctype/payment_settlement_entry/references.py`.
- Server-side Template configuration: `payment_settlement_template.py`.
- Filters, buttons, and form calls: corresponding `.js` files, only after explicit approval.

### Known limitations that are not bugs

Consult the [documented limitations](README.md#known-mvp-limitations) and
[verification status](README.md#implemented-behavior) before describing support or planning extensions.
Do not present unfinished calculations, unsupported reference sources, or bank reconciliation as implemented.

### Recommended priorities

1. Run and extend Frappe-native integration tests for Manual settlement use cases on a dedicated test site.
   Preserve the fast calculation tests; use controlled records and rollback for real submit/cancel coverage.
2. Operationally test POS, cash-register, and courier settlements with controlled records.
3. Extend gross-percentage calculations and implement `Fixed Amount` in separate approved increments.
4. Add reference sources only for a demonstrated need.
5. Consider bank reconciliation after `Journal Entry` generation is stable.

## Verification

For Python changes:

- check syntax without writing bytecode inside the repository;
- run `git diff --check`;
- test the affected case with rollback when it creates journal entries;
- confirm that ERPNext recalculates the same base debits and credits;
- verify submit and cancellation together.

For JavaScript changes:

- test the real event in Desk;
- check both selection and field clearing;
- verify that changing a Template or date range does not leave stale references or components.

For accounting or currency changes, include at least:

- an account in company currency;
- an account in a foreign currency;
- a component in the destination currency;
- a component in a different currency;
- a positive and negative residual;
- a precision difference.
