# App backlog

This file records ideas and open decisions for Grupo Real Tools.

None of the items below is approved design or implemented behavior.

Confirm the business need, scope, owner, and applicable module before starting work.

## Daily activities

### Proposal

Consider a daily-activity record and completion history to support operational readiness before users begin routine
work. Any access restriction, responsible roles, and workflow remain open decisions.

| Daily Activity | Daily Activity History |
|----------------|------------------------|
| Primary key    | Primary key            |
| Name           | Name                   |
| Recurrence     | Last completed         |
|                | Completed by User      |

### Examples to validate

- Day opening:
  - Update the day's BCN exchange rate.
  - Open cash and bank accounts.
  - Record prior-day expenses and retain supporting documents.
  - Record prior-day purchases.
  - Update image-related work records in the system.
  - Review packages that require reporting from the previous day.
- Day closing:
  - Close cash and bank accounts.
  - Record the day's expenses and retain supporting documents.
  - Record the day's purchases.

## Reimbursements

Consider separate reimbursement flows for customers and suppliers. Their documents, approvals, accounting treatment,
and relation to standard ERPNext processes remain undefined.

## Workforce management

Potential needs include:

- recording attendance and departure times;
- deciding whether a fingerprint reader is needed;
- recording absences;
- identifying information that changes base salaries; and
- evaluating automatic payroll calculation through Frappe HR.

## Administrative reporting and notifications

Potential reporting or notification work, possibly through Insights or outside this app:

- outstanding invoices;
- import orders pending payment;
- cash closings;
- charts to define; and
- transactional Telegram or WhatsApp notifications, including the events that would trigger them.
