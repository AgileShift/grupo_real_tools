# Module Instructions — Layaway

These instructions apply to `grupo_real_tools/layaway/`.
Read the parent [AGENTS.md](../../AGENTS.md) before working in this module.
Follow the root and any intermediate guides. These instructions add module-specific requirements without weakening them.
If they conflict with parent instructions, ask the owner before proceeding.

## Required reading

- Read [README.md](README.md) before proposing work in this module.
- Treat approved architecture as design, not evidence that its workflow is implemented.
- Revalidate the current scaffold before describing implementation status.
- Preserve the README distinctions among implemented structure, approved later-phase design, and open decisions.
- If code and documentation differ, present the discrepancy before proposing which one should change.

## Module-specific rules

### Module intent and ownership

Preserve the orchestration role and native ERPNext ownership described in
[Approved architecture](README.md#approved-architecture).
Do not duplicate sales, payments, stock reservations, fulfillment, or accounting with parallel custom DocTypes.

The custom document model is `Layaway Plan`, `Layaway`, and `Layaway Item`. Do not reintroduce the superseded global
`Layaway Settings` design without a new owner decision.

### Design invariants

- A company may offer multiple enabled `Layaway Plan` records.
- Each Layaway must retain its Plan link and freeze the rules, terms, currency, conversion rate, prices, discounts, and
  totals that governed the agreement.
- Plan amount limits and customer active exposure use company-currency base values.
- Deposits and partial payments remain native `Payment Entry` documents allocated through the approved Sales Order path.
- Inventory reservations remain native `Stock Reservation Entry` documents against Sales Order items.
- Pricing Rules are applied or ignored according to the Plan before price lock; later rule changes must not reprice an
  active Layaway.
- Terms and Conditions remain a native link and rendered snapshot. Payment Terms Template is optional.
- Warehouse selection remains in the item and Sales Order stock context; it is not a Plan default.
- Forfeiture is terminal and requires explicit human action for destructive stock, sales, and accounting operations.
- Do not create a custom payment table, stock reservation table, customer credit ledger, or accounting ledger.

### Phase discipline

Work only within the authorized phase. Completing one phase does not authorize the next one.

#### Phase 1 — Structural foundation

- Create and arrange `Layaway Plan`, `Layaway`, and `Layaway Item` through the DocType UI.
- Represent the approved form intent without implementing transactional automation or business-rule enforcement.
- Follow the root rules for Frappe UI and generated metadata. Inspect regenerated files but correct discrepancies only
  through Desk.

#### Phase 2 — Native ERPNext links

- Add links only after ownership, idempotency, cancellation, and recovery behavior are approved.
- Do not infer that a visible link or placeholder authorizes document creation.

#### Phase 3 — Business behavior

- Implement Plan resolution, calculations, exposure, price locking, transitions, expiration, completion, and
  forfeiture only after their documented open decisions are resolved.
- Keep authoritative validation, state transitions, and integrity in the backend.

### Phase 1 boundaries

While authorization remains limited to Phase 1, do not implement:

- Sales Order creation, submission, or cancellation;
- Payment Entry creation, aggregation, or allocation;
- stock reservation or release;
- Plan eligibility or customer exposure enforcement;
- minimum-deposit or price-lock enforcement;
- expiration, grace, scheduled jobs, or state transitions;
- completion, delivery, invoicing, forfeiture, or accounting actions;
- notifications, reports, external synchronization, or WhatsApp integration;
- new hooks or core overrides.

### Before implementation

Present the following to the owner:

1. DocTypes to create or modify.
2. Proposed fields, types, options, and layout.
3. Native ERPNext links and the owner of each business value.
4. Files that Frappe will regenerate or that would otherwise be modified.
5. Open decisions that affect the proposed increment.
6. Everything explicitly excluded from the increment.

Do not continue until explicit authorization is received for that implementation scope.

## Verification

For documentation changes:

- compare README and AGENTS for duplicated or contradictory rules;
- verify Markdown links and required template headings;
- run `git diff --check` and inspect the complete scoped diff.

After authorized Phase 1 structural changes:

- inspect Frappe-regenerated files without manually correcting them;
- confirm that `Layaway Plan`, `Layaway`, and `Layaway Item` install or migrate correctly;
- verify basic creation and editing with controlled data;
- confirm that item rows and structural summaries render correctly;
- confirm that no later-phase automation was introduced;
- show the final scoped diff and list every unresolved decision.
