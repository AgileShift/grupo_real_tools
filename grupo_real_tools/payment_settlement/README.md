# Payment Settlement

App overview: [Grupo Real Tools](../../README.md).
Development instructions: [AGENTS.md](AGENTS.md).

## Purpose and scope

`Payment Settlement` closes collection events that have already been recorded in ERPNext
and remain temporarily held in clearing accounts.
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

`Percentage` supports gross collections and a running balance after earlier charges for the clearing account selected
in `Apply To`. See [component calculations](#2-components-and-apply-to) for the exact base and ordering.
`Fixed Amount` is not implemented yet.

The standard DocType test file defines Frappe-native regression scenarios.
See [Automated verification](#automated-verification) for coverage, execution requirements, and current verification status.

`Calculation Method` controls whether a Settlement amount is calculated automatically or entered manually.
The owner reports a successful interactive trial of Automatic/Manual Settlement selection.

## Technical documentation

### Document model

#### Payment Settlement Template

Defines the reusable settlement recipe.

It contains:

- `company`;
- one or more `Payment Settlement Template Account` rows;
- one or more `Payment Settlement Template Component` rows.

Each account row maps one clearing account to one settlement account.
Several rows may share the same settlement account:

```text
Mode of Payment
    → Clearing Account
    → Settlement Account
```

Current rules:

- `Clearing Account` is derived from the `Mode of Payment` for the company.
- A `Mode of Payment` is intended to appear only once per Template. The Desk selector filters out modes already chosen;
  the Template controller does not enforce uniqueness on save.
- `Bank Account` is optional.
- When a `Bank Account` exists, its ledger account becomes the `Settlement Account`.
- Without a `Bank Account`, the destination may be a manually selected cash, receivable, wallet, or other clearing account.
- The Desk component account selector excludes structural clearing and settlement accounts.
  The Template controller does not enforce this exclusion on save.
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

`references.py` prepares the account pairs and date range, queries both sources, and excludes already-settled candidates.
The shared settled-reference query is limited to candidate document names and maps economic identities to their
Settlement names. Retrieval uses those keys to filter the combined results; submit-time validation reuses the same query.
The Entry controller assigns the returned snapshot and recalculates the document. It also retains the separate
submit-time validation against references already included in submitted Settlements.

New references use a consistent account-currency contract:

- `account`: the receiving clearing account;
- `currency`: that account's currency, displayed as Account Currency;
- `amount`: the receipt in that currency, displayed as Amount in Account Currency;
- `exchange_rate`: account currency to company currency, or 1 for a company-currency account;
- `base_amount`: the source payment's base amount in company currency.

Sales Invoice Payment amounts belong to the invoice currency. The source query resolves the payment account's currency
and uses the payment's base amount for a company-currency account; otherwise it keeps the invoice-currency amount and
conversion rate, following ERPNext's supported payment-account currencies. Payment Entry already supplies receiving-account
amounts and rates. The invoice's transaction-currency values are not stored separately in this reference model.

Source base amounts are not replaced with final rounded GL debits. Per-entry rounding and change handling remain separate
limitations; the query does not allocate merged GL entries back to payment rows.

The backend loads reference rows.
Users cannot add them manually, but they may remove Draft rows that do not belong to the closing.
Existing references are not migrated automatically. Get Entries replaces a Draft's references using the normalized source
queries; review the selection again because previously excluded rows may return. Submitted and cancelled snapshots remain
unchanged. Older Drafts with invoice-currency references or without the newly required Account field must refresh their
references before recalculation or save; clearing calculations no longer convert older reference representations.

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

The Template and Entry forms show and require `Rate` and `Add or Deduct` for `Percentage` and `Fixed Amount` only.
`Rate` is a Float. `Based On` is shown and required only for `Percentage`.
In the Template, `Apply To` is mandatory for `Percentage` and optional for the other methods.

Desk makes the copied `Calculation Method`, `Rate`, `Add or Deduct` (`add_deduct_tax`), and `Based On` (`based_on`)
read-only on rows of type `Component`. `Apply To` remains editable on both `Component` and user-added `Manual` rows.
These are form restrictions; the backend calculates from the Entry snapshot and does not enforce recipe immutability.

### Calculation

#### 1. Clearing

References are grouped by `Mode of Payment`.

Each structural row calculates:

```text
reference_count       = number of references
clearing_amount       = sum in account currency
clearing_base_amount  = sum in company currency
```

References express `amount` in the clearing account's currency, normalized by the source queries. Clearing calculation
sums `amount` directly and performs no source-currency conversion. Older Draft references must be refreshed through
Get Entries; historical rows are not migrated automatically.

The `Clearing` row credits both amounts. A company-currency clearing row always uses exchange rate 1, including zero rows.
A foreign-currency clearing row derives its aggregate rate from its rounded base and account-currency credits:

```text
exchange_rate = credit / credit_in_account_currency
```

This aggregate rate is not replaced by the Settlement-date rate because the row is clearing balances that were
previously captured at their own rates. An empty foreign-currency clearing row uses rate 0 and is not posted.

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
amount = selected base × rate / 100
Deduct → debit_in_account_currency  → reduces the settlement residual
Add    → credit_in_account_currency → increases the settlement residual
```

- `On Gross Amount` uses the selected clearing row's gross collections. This is the default when `Based On` is blank.
- `On Previous Row Total` starts from the same gross collections, subtracts earlier rounded debits, and adds earlier
  rounded credits for that clearing. Row order matters; the base is not the amount of the immediately preceding row.

Earlier configured `Component` charges and earlier calculated percentage charges can affect the running base.
Structural rows, adjustments, and user-added manual funding do not. The clearing is inferred for an active earlier
configured charge without `Apply To` when there is only one clearing source. With several clearing sources, that
charge must be assigned explicitly before a later cascade can run. The percentage row and all contributing charges
must use the clearing account's currency.

For example, on C$20,000 in collections, a 5.25% deduction on gross is C$1,050. A subsequent 1.50% deduction
on the remaining C$18,950 is C$284.25. With no other movements, the settlement residual is C$18,665.75.

Amounts use the existing component precision and exchange-rate calculation.
Recalculation clears the opposite debit/credit side and recomputes amounts from the current base.
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

The Entry copies `Journal Entry Type` (`voucher_type`) from its Template and passes that snapshot to the Journal Entry.
Entries without a stored type use `Journal Entry`. For `Bank Entry`, enter the deposit's `Reference Number` (`cheque_no`)
in the Entry. The generated journal uses the Settlement's `Posting Date` as its `Reference Date` (`cheque_date`),
without a separate date input. ERPNext validates the bank reference when the journal is submitted.

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
Desk calls the server-side `set_bank_accounts` method on account selection;
calculation and validation reuse that same method, including API saves.
Changing or clearing the account replaces or clears the previous bank link.

If no match exists, POS clearing and other accounts can remain without a `Bank Account`.
ERPNext validates that a ledger account is not linked to multiple Bank Account records.
The Template-derived Settlement path is preserved.

Server-side Journal Entry creation does not execute the client event that normally derives Bank Account,
so the component's Bank Account must be supplied explicitly.

#### Cancellation and deletion

Cancelling a Settlement cancels its submitted Journal Entry without deleting it. Frappe does not allow a submitted
Settlement to be deleted; cancel it first. When a Settlement has a linked Journal Entry, deletion also requires
`Delete Accounting and Stock Ledger entries on deletion of transaction` in Accounts Settings.
After deleting the Settlement, the controller requests deletion of the linked Journal Entry through Frappe,
subject to the normal deletion checks.

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
- Do not use multiple modes with the same clearing in one Entry. Reference totals are grouped by mode, but the
  `Clearing` component is matched by account; a later mapping can overwrite an earlier amount instead of adding to it.
  `Apply To` also identifies a clearing account, so it cannot separate percentage bases by mode within that account.
- Different clearing accounts may share a destination. Their residuals are combined by destination ledger account;
  this does not represent separate bank deposits.
- `Fixed Amount` has no calculation engine.
- `POS Invoice` is not queried directly.
- `Journal Entry`, bank transactions, and other sources are not used as references.
- There is no automatic reconciliation against `Bank Transaction`.
- There is no approval workflow beyond standard Frappe submit.

### Automated verification

Keep regression coverage in the standard
[DocType test file](doctype/payment_settlement_entry/test_payment_settlement_entry.py).
It extends Frappe `IntegrationTestCase` and uses ERPNext test fixtures and real document APIs.
Do not maintain a parallel fake document, precision, or Journal Entry implementation for these scenarios.

Run the tests on the agreed development site with Frappe, ERPNext, and this app installed.
An additional site is not required. If no target has been agreed, confirm it before execution.

```sh
bench --site <site> run-tests --app grupo_real_tools --doctype "Payment Settlement Entry"
```

Replace `<site>` with the agreed site's actual name; do not invent a site name or create another site implicitly.

The suite creates controlled Payment Entries, Sales Invoices, Templates, Settlements, accounts, and Bank Accounts.
It checks:

- Template snapshots, gross and cascading Percentage Add/Deduct calculations, rounding, and default and invalid bases;
- native amount precision, company and foreign currencies, and exchange differences;
- foreign-currency invoice payments into company-currency accounts and split-currency invoice payments;
- Manual/Automatic Settlement switching, duplicate destination rows, and shared bank destinations;
- expenses exceeding collections and additional manual funding;
- Company-configured Round Off, Exchange Gain Or Loss, and Write Off adjustments;
- required components, cancelled sources, and previously settled references;
- Bank Account and User Remark propagation;
- Bank Entry type, reference number, and posting date used as reference date;
- real Journal Entry submission, matching base amounts and GL balances, and linked cancellation.

Each test rolls back its transactional records. Frappe's standard fixture initialization may commit reusable core test
records before the tests run, so this is not a read-only command.
Do not run it against operational sites or substitute real settlements for test fixtures.
Exchange rates are supplied explicitly to avoid live exchange-service calls.
The Sales Invoice scenarios cover reference retrieval and linked Journal Entry submission/cancellation;
Desk interactions still require their own controlled verification.
The consolidated suite's database-backed execution is pending; a syntax check is not a passing integration result.
A focused check with real documents under `_Test Company` passed for a foreign-currency invoice split between company-
and invoice-currency accounts, combined with a Payment Entry, through Settlement and Journal Entry submission,
GL verification, cancellation, and rollback. This does not establish a passing result for the consolidated suite.

### Behavior to preserve

- Selecting a Template copies its account mappings into the Entry
  and creates the corresponding `Clearing` and `Settlement` component rows.
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
14. Gross commission followed by a percentage on the remaining balance, with rounded charges and the expected row order.
15. Bank Entry with its reference number and the posting date used as reference date.
16. Deletion of a cancelled Settlement with a linked journal, with the Accounts Settings option disabled and enabled.

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
    │   └── test_payment_settlement_entry.py
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

- Decide whether to enforce unique modes and structural-account exclusions on the server.
- Consider a small declarative table-rule helper, initially for `unique_within_table` on `accounts.mode_of_payment`.
  Define the rule once in Python and expose its configuration to the form. A Python consumer would enforce it during
  document validation, including API saves; a reusable JavaScript consumer would filter choices already used in other
  rows while preserving the current row's selection. The rule declaration would be shared, not the execution code.
  Keep the initial scope limited: no arbitrary expressions, `eval`, new dependencies, or structural UI changes.
  Inspect core facilities before implementation and verify both native document validation and Desk behavior.
  This proposal does not approve implementation or decide whether clearing accounts must also be unique.

### Calculation extensions

- Define cross-currency bases before extending Percentage beyond same-currency gross and running-balance calculations.
  Implement `Fixed Amount` separately.

### Settlement allocation

- Define how to preserve separate percentage bases and accumulate one clearing balance when several modes share a clearing.
- Separate deposits from several clearing sources into the same bank account still require a design that preserves each
  source and the existing Manual flow.
