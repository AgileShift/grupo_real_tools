# Payment Settlement

App overview: [Grupo Real Tools](../../README.md).
Development instructions: [AGENTS.md](AGENTS.md).

## Purpose and scope

`Payment Settlement` closes collection events that have already been recorded in ERPNext and remain temporarily held in
clearing accounts.
The document identifies included collections, incorporates expenses or additional movements,
calculates the residual destination, and creates a traceable `Journal Entry`.

The module does not collect invoices and does not replace `Payment Entry`.
Its responsibility begins after the money has been captured:

```text
Recorded collections
    → clearing accounts
    → settlement and components
    → destination accounts
    → Journal Entry
```

Target MVP cases include:

- POS and card settlements;
- cash-register closings;
- courier and delivery settlements;
- closings involving several accounts and currencies;
- additional funds from a bank, cash, or another manual account;
- controlled rounding, exchange differences, and write-offs.

## Implemented behavior

The **Manual** flow is implemented and has been tested interactively, including:

- USD and NIO references;
- several clearing accounts in one settlement;
- components applied to a specific clearing account;
- bank and non-bank destinations;
- manually entered settlement amounts;
- `Journal Entry` generation, submission, and cancellation;
- propagation of `Bank Account` and `User Remark` to the journal entry;
- prevention of previously settled references;
- prevention of submit when debit and credit do not balance.

`Percentage` calculates a charge on the gross collections of the clearing account selected in `Apply To`.
The component and clearing account must use the same currency. `Fixed Amount` is not implemented yet.

Template and Entry component forms show and require `Rate` and `Add or Deduct` only for `Percentage` and `Fixed Amount`.
Both fields are read-only for `Manual` and, in the Entry, `Automatic`.
`Rate` is a Float so it can represent either a percentage or a fixed amount.
The Entry copies `add_deduct_tax` from the Template and uses it for percentage calculations.
In the Template form, `Apply To` is mandatory for `Percentage` to identify the clearing source;
it remains optional for `Manual` and `Fixed Amount`.

In-memory calculation tests cover percentage charges, Manual regressions,
and comparison with ERPNext's company-currency calculation.
Submit/cancel wiring is tested with a journal double, without database persistence.
Frappe-native integration tests define controlled Bank Account, Payment Entry, Settlement,
and Journal Entry scenarios with rollback. These new integration tests have not yet been run on a dedicated test site.

`Calculation Method` controls whether a Settlement amount is calculated automatically or entered manually.
Automatic/manual Settlement selection has automated coverage.
The owner reports a successful interactive trial; full database-backed transactional verification remains pending.

## Technical documentation

### Document model

#### Payment Settlement Template

Defines the reusable settlement recipe.

It contains:

- `company`;
- one or more `Payment Settlement Template Account` rows;
- zero or more `Payment Settlement Template Component` rows.

Each account row maps one clearing account to one settlement account.
Several rows may share the same settlement account:

```text
Mode of Payment
    → Clearing Account
    → Settlement Account
```

Current rules:

- `Clearing Account` is derived from the `Mode of Payment` for the company.
- A `Mode of Payment` must not be repeated within the same Template.
- `Bank Account` is optional.
- When a `Bank Account` exists, its ledger account becomes the `Settlement Account`.
- Without a `Bank Account`, the destination may be a manually selected cash, receivable, wallet, or other clearing account.
- A component must not reuse a structural clearing or settlement account.
- When used, `Apply To` points to a `Clearing Account` in the same Template.

#### Payment Settlement Entry

Represents the actual transactional closing.
It stores a snapshot of the configuration used and does not depend dynamically on the Template after it has been copied.

It contains:

- company, Template, posting date, and search range;
- structural accounts table;
- included references table;
- accounting components table;
- totals in company currency;
- calculated difference;
- link to the generated `Journal Entry`.

#### Payment Settlement Entry Reference

Represents a collection event included in the closing, not merely an invoice.

Implemented sources:

1. `Payment Entry` with `payment_type = Receive`.
2. A `Sales Invoice Payment` row belonging to a submitted, non-return `Sales Invoice`.

Candidates are filtered by:

- company;
- date range;
- `Mode of Payment`;
- clearing account;
- `docstatus = 1`.

Although the Entry stores `from_date` and `to_date` as `Datetime`,
reference queries currently convert both values to dates and include the full calendar days.
The time of day is intentionally not used yet; revisit this only when an operational closing requires a narrower time window.

The economic identity of a reference is:

```text
(reference_doctype, reference_name, reference_row_name)
```

`reference_row_name` distinguishes different payment rows within one invoice. It remains empty for `Payment Entry`.

The backend loads reference rows.
Users cannot add them manually, but they may remove Draft rows that do not belong to the closing.

#### Payment Settlement Entry Component

Represents the operational and accounting rows that ultimately feed `Journal Entry Account`.

| Type         | Origin                               | Behavior                                                                   |
|:-------------|:-------------------------------------|:---------------------------------------------------------------------------|
| `Clearing`   | Generated from the Template          | Credits collections grouped by `Mode of Payment`. Not editable.            |
| `Settlement` | Generated from the Template          | Receives the closing residual. May be debited or credited.                 |
| `Component`  | Copied from the Template             | Expense, withholding, or other configured movement.                        |
| `Manual`     | Added by the user                    | Additional movement not anticipated by the Template.                       |
| `Adjustment` | Generated by `Make Difference Entry` | Balances an accounting difference without altering the operating residual. |

The backend requires `Automatic` for Clearing, `Automatic` or `Manual` for Settlement, and `Manual` for Adjustment.
Component and user-added Manual rows retain `Manual`, `Percentage`, or `Fixed Amount`; the latter still has no engine.
New Clearing and Settlement rows use `Automatic`.
Adjustment rows are created as `Manual`; their method selector is read-only, but their amounts remain editable.
In the Entry form, account-currency amounts are editable only for the `Manual` method,
except that Clearing amounts are always read-only.

### Calculation

#### 1. Clearing

References are grouped by `Mode of Payment`.

Each structural row calculates:

```text
reference_count       = number of references
clearing_amount       = sum in account currency
clearing_base_amount  = sum in company currency
```

The `Clearing` row credits both amounts.
Its exchange rate is the weighted rate derived from the included collections:

```text
exchange_rate = clearing_base_amount / clearing_amount
```

This aggregate rate is not replaced by the Settlement-date rate because the row is clearing balances that were
previously captured at their own rates.

#### 2. Components and Apply To

For a manual line:

```text
adjustment = debit_in_account_currency - credit_in_account_currency
```

- A debit consumes part of the amount available to the Settlement.
- A credit contributes funds and increases the amount available to the Settlement.

When several destinations exist, `Apply To` selects the clearing-to-settlement mapping that receives the effect.
`Apply To` always contains the clearing account, not the destination account.

When there is only one destination, a line without `Apply To` may be applied to that destination automatically.
With several destinations, an active line without `Apply To` raises an error.

When the component and destination share a currency, the movement is applied directly in that currency.
When they differ, it is converted through the base amount and destination-account rate.

For `Percentage` on a `Component` or user-added `Manual` row, the backend requires a valid `Apply To` and `Add or Deduct`:

```text
amount = selected clearing_amount × rate / 100
Deduct → debit_in_account_currency  → reduces the settlement residual
Add    → credit_in_account_currency → increases the settlement residual
```

The component must use the clearing account's currency.
The percentage uses gross collections, before other components;
it does not calculate a percentage on a previous charge or on the remaining balance.
Amounts use the existing component precision and exchange-rate calculation.
Recalculation clears the opposite debit/credit side and recomputes zero amounts when references are removed.
Rows whose calculation method is `Manual` retain their entered amounts.

#### 3. Settlement

Each `Settlement` row receives its corresponding residual:

```text
initial clearing balance
- applied debits
+ applied credits
= settlement residual
```

- Positive residual → debit to the `Settlement Account`.
- Negative residual → credit to the `Settlement Account`; the destination account supplied the shortfall.

Example:

```text
Clearing received:       C$1,000  (credit)
Delivery and CargoTrans: C$1,100  (debit)
Manual funding source:     C$300  (credit)
Settlement residual:       C$200  (debit)
```

Setting a `Settlement` row's `Calculation Method` to `Manual` preserves its entered account-currency amounts.
Only one Manual Settlement row is allowed per destination account.
It takes precedence over Automatic rows for that account, which are zeroed to avoid duplicating the balance.
With no Manual row, the first Automatic row receives the residual.
Switching back to `Automatic` recalculates both debit and credit. Base amounts are recalculated in either mode.

#### 4. Totals and difference

Totals are calculated in company currency:

```text
total_debit  = sum of component.debit
total_credit = sum of component.credit
difference   = total_debit - total_credit
```

The Settlement cannot be submitted while `difference` is non-zero.

`Make Difference Entry` creates an `Adjustment` row using one of the accounts configured in `Company`:

- `Round Off`;
- `Exchange Gain Or Loss`;
- `Write Off`.

The user must select the real meaning of the difference; not every difference is rounding.

### Operational flow

1. Create or select a `Payment Settlement Template`.
2. Configure its company, structural accounts, and components.
3. Create a `Payment Settlement Entry`.
4. Select the Template, posting date, and date range.
5. The backend copies the Template accounts and components.
6. The backend loads eligible references.
7. The user removes references that do not belong to the closing.
8. The user enters amounts for manual components.
9. The backend recalculates clearing, rates, settlement, totals, and difference.
10. When appropriate, the user selects `Manual` on the Settlement row or creates an identified adjustment.
11. Submit only when the difference is zero and movements match reality.
12. On submit, the module creates and submits the `Journal Entry` and stores its link.
13. Cancelling the Settlement also cancels the linked `Journal Entry`.

### Generated Journal Entry

Only components with a non-zero debit or credit are copied.

Each row transfers:

- ledger account;
- `Bank Account`;
- exchange rate;
- debit and credit in account currency;
- `User Remark`.

Before submitting the journal entry, the module compares the base amounts recalculated by ERPNext with those in the Settlement.
If ERPNext produces a different amount because of rate or precision, the process stops.

The `Bank Account` follows this path:

```text
Payment Settlement Template Account.bank_account
→ Payment Settlement Entry Account.bank_account
→ Payment Settlement Entry Component.bank_account (Type = Settlement)
→ Journal Entry Account.bank_account
```

User-added Manual components also resolve an enabled company `Bank Account` from their current ledger account and company.
Desk fills it on account selection; the backend resolves it again during calculation and validation, including API saves.
Changing or clearing the account replaces or clears the previous bank link.

If no match exists, POS clearing and other accounts can remain without a `Bank Account`.
ERPNext validates that a ledger account is not linked to multiple Bank Account records.
The Template-derived Settlement path is preserved.

Server-side Journal Entry creation does not execute the client event that normally derives Bank Account,
so the component's Bank Account must be supplied explicitly.

### Validation and responsibilities

The backend is responsible for:

- finding references;
- calculating amounts and rates;
- recalculating the document during `validate`;
- preventing duplicate references in submitted Settlements;
- requiring a zero difference before submit;
- creating and submitting the `Journal Entry`;
- cancelling the linked journal entry.

JavaScript is limited to non-structural user experience:

- field filters;
- copies requested from the backend;
- reference refresh after a date-range change;
- the button that retrieves references;
- the dialog that creates differences;
- recalculation after references are removed.

### Known MVP limitations

- `Percentage` requires an explicit clearing source and the same currency for the source and component.
- Percentage bases on previous charges or remaining balances are not implemented.
- `Fixed Amount` has no calculation engine.
- `POS Invoice` is not queried directly.
- `Journal Entry`, bank transactions, and other sources are not used as references.
- There is no automatic reconciliation against `Bank Transaction`.
- Bank Account database integration tests are defined but have not yet been executed on a dedicated test site.
- There is no approval workflow beyond standard Frappe submit.

The in-memory tests do not replace rollback-based integration tests or a controlled Desk trial before deployment.

Test files: [calculation tests](doctype/payment_settlement_entry/test_calculations.py) and
[integration tests](doctype/payment_settlement_entry/test_payment_settlement_entry.py).

Run the integration tests only on a dedicated test site with Frappe, ERPNext, and this app installed:

```sh
bench --site <test-site> run-tests --app grupo_real_tools --doctype "Payment Settlement Entry"
```

The integration tests use Frappe `IntegrationTestCase`, ERPNext test fixtures, and real document lifecycles.
They create controlled collection events and check bank propagation, submit, cancellation, and ledger amounts.
Do not run them against operational sites or substitute real settlements for test fixtures.

Run the calculation tests from the app root:

```sh
FRAPPE_STREAM_LOGGING=1 ../../env/bin/python -m unittest grupo_real_tools.payment_settlement.doctype.payment_settlement_entry.test_calculations
```

### Behavior to preserve

- Selecting a Template copies its account mappings into the Entry and creates the corresponding `Clearing` and
  `Settlement` component rows.
  At that point, the Template's `Bank Account`, if present, is copied to the `Settlement` row.
- Calculation uses the Entry's account mappings and component rows to compute the residual.
  It does not fetch the `Bank Account` again from the Template or Entry account row.
  On submit, each non-zero component passes its own `Bank Account` to the generated Journal Entry row.
- A user-added Manual component resolves its enabled company `Bank Account` from its current ledger account and company.
  Its resulting value is passed to the Journal Entry; no matching bank is required.
- Clearing and Settlement component rows are required for each Entry account mapping.
  The backend checks their presence during calculation; the form also prevents users from deleting these rows normally.

### Minimum tests before deploying changes

Always test, preferably inside a rollback transaction:

1. One currency and one non-bank destination.
2. USD and NIO in the same Settlement.
3. Several clearing accounts targeting the same bank.
4. Several destinations using `Apply To`.
5. Expenses greater than collections and a credit Settlement residual.
6. A manual credit source that converts the residual to a debit.
7. Manual Settlement amounts, switching back to Automatic, and multiple rows for the same destination account.
8. Round Off, Exchange Gain Or Loss, and Write Off.
9. A reference already used in another submitted Settlement.
10. A source document cancelled before save or submit.
11. Submit with a non-zero difference.
12. `Bank Account` and `User Remark` propagation to the Journal Entry.
13. Cancellation of the Settlement and its linked Journal Entry.

### Main files

```text
payment_settlement/
├── README.md
├── AGENTS.md
└── doctype/
    ├── payment_settlement_template/
    │   ├── payment_settlement_template.py
    │   └── payment_settlement_template.js
    ├── payment_settlement_entry/
    │   ├── payment_settlement_entry.py
    │   ├── payment_settlement_entry.js
    │   ├── references.py
    │   └── test_calculations.py
    └── child DocTypes...
```

## Backlog

The following improvements are not implemented. A backlog entry does not authorize implementation.

### Workspace monitoring

- Add a Settlement workspace table for monitoring clearing-account balances at a user-selected cutoff date.
  Let each user select accounts by company and retain that selection for later visits.
  Show each account's balance in its own currency, with no combined total across currencies.
  Reuse ERPNext balance calculations and respect account permissions.
  Evaluate the existing `Account Balance` report before designing a custom workspace block and preference storage.
  Verify cutoff balances against General Ledger with controlled data.
  Implementation is deferred; the storage mechanism and workspace integration still need a scoped proposal and approval.

### Draft recovery

- Consider a `Reset Components` action for Draft entries when users need to undo manual changes.
  Define whether it recreates rows from the Template and how it handles manually entered settlement amounts,
  adjustments, and remarks before implementing it.

### Validation gaps

- The Template's duplicate Mode of Payment and structural-account exclusions are form query filters.
  Decide whether server-side checks are useful before treating them as backend invariants.

### Calculation extensions

- Extend Percentage only after defining cross-currency bases and charges on a remaining balance.
  Implement `Fixed Amount` separately from the working Manual and gross-percentage flows.

### Settlement allocation

- Settlement residuals currently aggregate by destination account.
  Separate deposits from several clearing sources into the same bank account still require a design that preserves each
  source and the existing Manual flow.
