# Grupo Real Tools

Custom ERPNext and HRMS extensions used across Grupo Real companies, including FT, CL, and QB.

## Scope

This app contains business addons shared across Grupo Real companies. Its modules have different implementation stages;
their guides distinguish working behavior from intended design and future phases.

## Features

- **Payment Settlement:** settles recorded collection events held in clearing accounts and creates traceable Journal
  Entries. Its controller implements Journal Entry submission and cancellation. See the module documentation for the
  supported flow and limitations.
- **Procurement:** provides the foundation for guided purchasing and item configuration. The current Procurement
  controller calculates proposal quantities and totals; this does not establish an automated purchasing workflow.
- **Layaway:** documents a phased design for merchandise reservations built around standard ERPNext documents. Its
  future phases are not asserted as implemented.

## Requirements

Declared in [pyproject.toml](pyproject.toml):

- Python 3.14 or later.
- Frappe 16 (`>=16.0.0,<17.0.0`).
- ERPNext 16 (`>=16.0.0,<17.0.0`).

## Technical documentation

- **Payment Settlement:** [module README](grupo_real_tools/payment_settlement/README.md) and
  [module instructions](grupo_real_tools/payment_settlement/AGENTS.md).
- **Procurement:** [module README](grupo_real_tools/procurement/README.md) and
  [module instructions](grupo_real_tools/procurement/AGENTS.md).
- **Layaway:** [module README](grupo_real_tools/layaway/README.md) and
  [module instructions](grupo_real_tools/layaway/AGENTS.md).

## Backlog

The [app backlog](docs/backlog.md) records unapproved ideas and open decisions. It is not an implementation plan.

## Contributing

Read [AGENTS.md](AGENTS.md) and the applicable module instructions before proposing changes. They define the working
agreement, shared conventions, local constraints, and required verification.

## License

[MIT](LICENSE.txt).
