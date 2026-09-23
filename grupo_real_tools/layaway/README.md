# Layaway

## Purpose

The Layaway module will manage the lifecycle of merchandise reservations,
partial payments, inventory reservation, expiration, completion, and
forfeiture.

Development is intentionally incremental. This document describes the intended
architecture and the currently authorized first phase; it does not claim that
future-phase behavior is already implemented.

## Business context

The current business rules are:

- maximum reservation period: 30 days;
- minimum initial deposit: 30% of the total;
- arbitrary partial payments during the reservation period;
- maximum of five active reserved items per customer;
- maximum total value of USD 300 across a customer's active reservations;
- merchandise remains reserved while the layaway is active;
- a fully paid layaway can be completed and delivered;
- an unpaid layaway expires at the end of the allowed period;
- forfeiture must eventually release reserved inventory, cancel the associated
  Sales Order, and recognize received payments appropriately instead of leaving
  them as unused customer credit.

These rules describe the target feature. They must not be treated as implemented
until the corresponding phase is explicitly developed and verified.

## Intended architecture

`Layaway` is the business and orchestration document. It coordinates standard
ERPNext documents instead of replacing them:

```text
Layaway
├── Sales Order
│   └── Stock Reservation
├── Payment Entry(s)
└── Completion / Expiration / Forfeiture
```

ERPNext remains responsible for accounting, inventory, and standard
transactions. Layaway owns the business lifecycle and its traceability.

## Development phases

### Phase 1 — Visual structure

Create the DocTypes and establish the Desk form structure. Fields may remain
structural placeholders. No transactional automation or business-rule
enforcement belongs in this phase.

### Phase 2 — ERPNext links

Connect Layaway to Customer, Item, Sales Order, Payment Entry, stock reservation,
and other standard documents after their ownership and lifecycle rules are
approved.

### Phase 3 — Business logic

Implement limits, calculations, state transitions, expiration, reservation,
completion, and accounting actions only after their detailed workflows are
approved.

## Phase 1 DocTypes

### Layaway

The main orchestration document.

#### Customer

- Customer
- Customer Name
- Posting Date
- Expiration Date

#### Reservation

- Status
- Sales Order
- Company
- Currency

The structural status options are:

- Draft
- Awaiting Deposit
- Active
- Partially Paid
- Paid
- Ready for Pickup
- Completed
- Expired
- Forfeited
- Cancelled

Phase 1 does not implement a state machine.

#### Items

The `Layaway Item` child table should appear prominently on the form. Standard
Frappe table behavior is sufficient for Phase 1.

#### Payment summary

The form should clearly show:

- Grand Total
- Minimum Deposit
- Paid Amount
- Outstanding Amount

Example target presentation:

```text
Total              $200.00
Minimum Deposit     $60.00
Paid                $80.00
Outstanding        $120.00
```

These may initially be normal fields or placeholders. Payment aggregation is a
future-phase concern.

#### Time and expiration

Reserve a prominent area for:

- Expiration Date
- Days Remaining

The long-term design should make expiration immediately visible, for example:

```text
Expires
October 21, 2026

29 days remaining
```

Phase 1 does not calculate expiration or schedule expiration processing.

#### Payments

Reserve an intentional location for payment history. Do not create a custom
accounting child table that duplicates Payment Entry. Future payment records
must remain real ERPNext `Payment Entry` documents.

#### Terms

Include a `Terms and Conditions` field intended to use ERPNext's standard terms
mechanism. External documentation synchronization is outside the scope of this
phase.

#### Completion and audit information

Reserve normally hidden or read-only fields for:

- Completed On
- Expired On
- Forfeited On
- Forfeiture Document

Phase 1 does not implement forfeiture accounting.

### Layaway Item

The child DocType is intended to contain:

- Item Code
- Item Name
- Description
- Quantity
- UOM
- Rate
- Amount
- Warehouse

Phase 1 does not reserve stock.

### Layaway Settings

A Single DocType will hold configurable rules so later phases do not hardcode
business policy.

#### Reservation rules

- Default Reservation Days — default 30
- Minimum Deposit Percentage — default 30
- Maximum Active Items per Customer — default 5
- Maximum Active Amount per Customer — default 300

#### Defaults

- Default Warehouse
- Default Terms and Conditions

#### Forfeiture

- Forfeited Deposit Income Account

Phase 1 creates a home for these values but does not enforce them.

## Form hierarchy

The Desk experience should feel like an operational salesperson screen rather
than a raw database record:

```text
CUSTOMER + STATUS + EXPIRATION

ITEMS

TOTAL             $XXX
MINIMUM DEPOSIT   $XXX
PAID              $XXX
OUTSTANDING       $XXX

PAYMENT HISTORY

RELATED DOCUMENTS / AUDIT
```

Use standard Frappe sections, columns, tables, read-only fields, and declarative
dependencies whenever possible. All fields and layout changes must be made in
the DocType UI. Do not construct or rearrange the form in JavaScript.

## Explicit Phase 1 exclusions

Do not implement any of the following during Phase 1:

- Payment Entry creation or aggregation;
- Sales Order creation or cancellation;
- stock reservation or release;
- customer active-item or active-amount limits;
- minimum-deposit enforcement;
- expiration enforcement or scheduled jobs;
- forfeiture or accounting entries;
- Sales Invoice creation;
- notifications or WhatsApp;
- document synchronization;
- a state machine;
- reports.

## Phase 1 definition of done

Phase 1 is complete when:

- `Layaway`, `Layaway Item`, and `Layaway Settings` exist;
- the Layaway form has a clear operational hierarchy;
- items can be entered;
- financial-summary fields are visible;
- expiration has a prominent location;
- payment history has an intentional placeholder;
- terms and lifecycle audit fields have intentional locations;
- settings contain the configurable business rules;
- the DocTypes install or migrate correctly;
- structural tests pass;
- no ERPNext transactional automation or Layaway business logic has been
  introduced.
