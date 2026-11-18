# Grupo Real Tools

Custom ERPNext extensions used across Grupo Real companies, including FT, CL, and QB.

## Scope

This app contains business addons shared across Grupo Real companies. Its modules have different implementation stages;
their guides distinguish working behavior from intended design and future phases.

## Features

- **Payment Settlement:** settles recorded collection events held in clearing accounts and creates traceable Journal Entries.
  Its controller implements Journal Entry submission and cancellation.
  See the module documentation for the supported flow and limitations.
- **Procurement:** provides the foundation for guided purchasing and item configuration.
  Before validation, the controller sums proposal quantities and calculates subtotals from quantities and purchase rates.
- **Layaway:** includes a DocType scaffold for a phased merchandise reservation design built around standard ERPNext
  documents. The transactional workflow remains planned.
- **Ecommerce:** provides product listings, template details, categories, and attributes through Frappe API v2.
  Product listings and details use the default company's `default_warehouse`. Catalog pricing uses ERPNext.
  The read-only GET methods are grouped by primary ERPNext resource under `grupo_real_tools.ecommerce.api`.
  Template detail includes `images` for the requested Item and each available variant. These lists include only
  public Item attachments under `/files/` with JPG, JPEG, or PNG extensions, ordered by creation. They do not
  publish private files or external URLs. Image paths are local-development data, not the future public media API.

## Requirements

Declared in [pyproject.toml](pyproject.toml):

- Python 3.14 or later.
- Frappe 16 (`>=16.60.0,<17.0.0`).
- ERPNext 16 (`>=16.60.0,<17.0.0`).

## Technical documentation

- **Payment Settlement:** [module README](grupo_real_tools/payment_settlement/README.md) and
  [module instructions](grupo_real_tools/payment_settlement/AGENTS.md).
- **Procurement:** [module README](grupo_real_tools/procurement/README.md) and
  [module instructions](grupo_real_tools/procurement/AGENTS.md).
- **Layaway:** [module README](grupo_real_tools/layaway/README.md) and
  [module instructions](grupo_real_tools/layaway/AGENTS.md).
- **Ecommerce:** [module guide](grupo_real_tools/ecommerce/README.md),
  [module instructions](grupo_real_tools/ecommerce/AGENTS.md) and [resource API](grupo_real_tools/ecommerce/api/).

## Backlog

The [app backlog](docs/backlog.md) records unapproved ideas and open decisions. It is not an implementation plan.

## Contributing

Read [AGENTS.md](AGENTS.md) and the applicable module instructions before proposing changes.
They define the working agreement, shared conventions, local constraints, and required verification.

## License

[MIT](LICENSE.txt).
