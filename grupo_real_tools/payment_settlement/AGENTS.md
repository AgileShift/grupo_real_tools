# Module Instructions — Payment Settlement

These instructions apply to `grupo_real_tools/payment_settlement/`.
Read the parent [AGENTS.md](../../AGENTS.md) before working in this module.
They add module-specific requirements; ask the owner before proceeding if they conflict with parent instructions.

## Required reading

- Read [README.md](README.md) before proposing changes. It describes implemented behavior, known limitations, and
  required regression scenarios.

## Module intent

This module does not pay invoices. It settles collection events that have
already reached clearing accounts and creates an explainable, auditable
`Journal Entry`.

Do not assume that every component is a tax or that a withholding is recoverable. The selected account is the primary
source of accounting meaning.

## Invariants that must be preserved

1. A Template is a recipe; an Entry is a transactional snapshot.
2. A Template may include several `Mode of Payment` values, but the same value
   must not appear in more than one row.
3. `Clearing Account` is derived from the `Mode of Payment` and company.
4. Each structural row maps one clearing account to one settlement account.
5. `Bank Account` is optional and must propagate only to its corresponding
   `Settlement` row.
6. References represent collection events, not complete invoices.
7. The duplication key is
   `(reference_doctype, reference_name, reference_row_name)`.
8. `Apply To` points to an Entry clearing account.
9. `Clearing` and `Settlement` are structural rows and must not be editable,
   except for the controlled `Settlement` override.
10. Manual components use debit and credit in account currency.
11. Totals and `difference` are expressed in company currency.
12. Submit requires `difference == 0`.
13. The `Journal Entry` must produce exactly the same base amounts as the
    Settlement.
14. Cancelling the Settlement must cancel the linked `Journal Entry`.
15. Definitive accounting logic and validation belong to the backend;
    JavaScript only orchestrates non-structural UI behavior.

## Component type semantics

- `Clearing`: generated, automatic, normally a credit.
- `Settlement`: generated, automatic residual or explicit override.
- `Component`: copied from the Template.
- `Manual`: added by the user and applied during settlement.
- `Adjustment`: created to balance an identified difference; it does not
  recalculate the operating residual.

Do not change signs without tracing a complete accounting case. In the current
calculation:

```text
component adjustment = debit - credit
settlement residual  -= component adjustment
```

Therefore, a debit reduces the amount available to the destination, while a
credit increases it.

## Currencies

- A clearing row uses the real aggregate rate of its references:
  `base_amount / amount`.
- A row in company currency uses a rate of 1.
- Other rows obtain the rate for the accounting date if one has not already
  been provided.
- When a component and destination share a currency, apply the amount directly
  in that currency.
- When their currencies differ, convert through base amounts and the
  destination rate.
- Do not hide exchange differences by silently changing the cash residual.

## Implemented reference sources

Do not claim support for a source without finding its query in the controller.

The currently implemented sources are:

- `Payment Entry` with type `Receive`;
- `Sales Invoice Payment` linked to a submitted, non-return `Sales Invoice`.

There is no direct query for `POS Invoice`, `Journal Entry`, or
`Bank Transaction`.

## Bank Account path

The complete path must remain intact:

```text
Payment Settlement Template Account.bank_account
→ Payment Settlement Entry Account.bank_account
→ Payment Settlement Entry Component.bank_account (Type = Settlement)
→ Journal Entry Account.bank_account
```

Server-side `Journal Entry` creation does not execute the client event that
normally derives `Bank Account`, so it must be supplied explicitly.

## Responsibility boundaries

- Calculations, queries, submit, and cancellation:
  `payment_settlement_entry.py`.
- Server-side Template configuration: `payment_settlement_template.py`.
- Filters, buttons, and form calls: corresponding `.js` files, only after
  explicit approval.
- User-visible Python strings: wrap in `_()`.
- User-visible JavaScript strings: wrap in `__()`.
- English is the source language for labels and messages.
- Spanish translations belong in `.po` catalogs; update them through the
  translation workflow and reuse native messages when suitable.

## Known limitations that are not bugs

- `Percentage` and `Fixed Amount` exist as options but have no calculation
  engine.
- The current functional scope is `Manual`.
- Integration test files are empty scaffolds.
- Automatic bank reconciliation is outside the MVP.

## Required verification

For Python changes:

- check syntax without writing bytecode inside the repository;
- run `git diff --check`;
- test the affected case with rollback when it creates journal entries;
- confirm that ERPNext recalculates the same base debits and credits;
- verify submit and cancellation together.

For JavaScript changes:

- test the real event in Desk;
- check both selection and field clearing;
- verify that changing a Template or date range does not leave stale references
  or components.

For accounting or currency changes, include at least:

- an account in company currency;
- an account in a foreign currency;
- a component in the destination currency;
- a component in a different currency;
- a positive and negative residual;
- a precision difference.

## Recommended priorities

1. Add automated tests for the implemented `Manual` flow.
2. Operationally test POS, cash-register, and courier settlements with
   controlled records.
3. Implement `Percentage` and `Fixed Amount` only after `Manual` is stable.
4. Add reference sources only for a demonstrated need.
5. Consider bank reconciliation after `Journal Entry` generation is stable.
