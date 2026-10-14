# Agent Instructions — Grupo Real Tools

Maintenance reference:
[Frappe App Documentation Standard](../../frappe-app-standards/skills/frappe-app-docs-normalize/references/frappe-app-standard.md).

Technical app name: `grupo_real_tools`.

These instructions apply throughout this repository. Module guides add specific instructions.
If they conflict with the root rules, ask the owner before proceeding.

<!-- BEGIN SHARED RULES: maintained from frappe-app-standard.md -->
## General rules — shared across apps

### Working agreement

- Read the root README, root AGENTS, and applicable module guides before proposing or making changes. Read
  CONTRIBUTING.md before preparing a commit or pull request.
- Before working inside a module, locate and read its applicable local instructions. When creating or reorganizing
  documentation, consult the canonical standard linked by the root AGENTS. Keep template schemas in that standard and do
  not repeat parent rules in module guides.
- Before editing, explain the objective, exact affected files, proposed behavior, material risks, and verification plan.
  Obtain explicit authorization for that scope. Honor authorization already given; do not request it again for the same
  work.
- Work in small, reviewable increments and follow the authorized phase literally. Completing a phase does not authorize
  the next one.
- Treat documentation normalization as an explicit task with one declared scope: entire app, root only, named module(s)
  only, or root plus named module(s). Entire app includes the root files and every existing meaningful module README.md
  and AGENTS.md. Do not infer module inclusion from a root-only request.
- Do not expand a focused task into a broader refactor, migration, or automation.
- Preserve unrelated worktree changes. Never discard, overwrite, or include them.
- Evaluate the business need before adding modules, screens, or forms. Generalize requirements across businesses when
  appropriate, without inventing future needs.
- Keep code understandable on first reading. Prefer direct solutions over unnecessary abstractions; remove real
  duplication without building speculative frameworks.
- Keep affected documentation current as part of authorized refactors, improvements, and behavior changes, before
  declaring the work complete or preparing its commit. Update README, technical references, and local instructions
  where their documented behavior or constraints changed; leave unrelated documentation intact.
- Keep small pending work near its context in Issues, README sections, or code TODOs. When it becomes distributed,
  repetitive, or difficult to review, consider a backlog: use `docs/backlog.md` for app-wide work and a module backlog
  only when that module has enough independent work to justify it. Link related backlogs and avoid duplicate items.
- Before implementing a proposal that conflicts with a README or other documented decision, warn the owner, explain
  the conflict, and obtain approval for the new direction. Do not silently change code or rewrite documentation to
  conceal the disagreement.

### Decision quality

- Be direct and truthful. Challenge weak assumptions with evidence and explain their practical consequences. Do not
  agree merely to be agreeable.
- Distinguish implemented behavior, approved design, external documented behavior, inference, and unresolved decisions.
  State uncertainty instead of guessing.
- When explicitly evaluating an idea or design, give an honest score out of 10 with criteria. Do not attach arbitrary
  scores to routine implementation work.
- Do not infer business policy from field names, historical data, test fixtures, or unfinished documentation. Consult
  the relevant approved operational process.
- During authorized technical work, compare relevant documentation with the code in scope. Report discrepancies and
  distinguish implemented behavior, approved design, and pending decisions or verification. Do not change rules or code
  to resolve discrepancies without authorization, or expand the task into a repository-wide audit.
- When explicitly asked to audit technical documentation, verify every factual technical claim in the selected scope
  against relevant current evidence. This includes README.md files, AGENTS.md files, repository-specific rules, module
  guides, and other technical documentation.
- Report unsupported, contradicted, stale, duplicated, or ambiguous claims. Distinguish confirmed facts, approved
  design, business policy, and pending decisions. Do not silently rewrite policy or claim that missing evidence proves
  a feature is absent.
- A field, button, README, or scaffold test does not prove a workflow is implemented. When verifying behavior within a
  technical task, trace its controller and invocation, and inspect meaningful tests when available.
- Revalidation means checking available evidence first. Ask the owner when evidence conflicts or a business decision is
  missing; do not request repeated confirmation of an unchanged decision already approved.

### Language and documentation conventions

- Use 120 characters as a Markdown readability target, preserving its structure. If wrapping would leave only a few
  words on the next line, keep the phrase together with a modest overflow. Keep URLs and complete
  `[label](destination)` links (external, internal, or fragments) on one line; move them to the next line when needed.
  Exceed the limit rather than break a link, unbreakable token, table row, or code example.
- Use English for code and documentation; translate user-facing text into Spanish through Frappe i18n (`_()` in Python,
  `__()` in JavaScript) and the app's translation catalogs.

### Frappe UI and generated metadata

- Make UI structure and DocType metadata changes through the Frappe interface. This includes fields, labels, sections,
  columns, order, options, dependencies, properties, and permissions.
- Never implement structural changes through code, scripts, console commands, patches, or fixtures. Never manually
  create or edit Frappe-generated JSON files.
- Never manually edit blocks between `begin: auto-generated types` and `end: auto-generated types`. Inside a DocType
  controller, do not put manual attributes or methods before Frappe's initial generated type block.
- If the required interface is unavailable, ask the owner to make the change. Do not bypass the interface restriction
  through code.
- Inspect regenerated files to verify the configuration. Correct discrepancies through the interface, not by editing
  generated output.
- If the interface cannot express a requirement, present the limitation and alternatives for a decision before
  proceeding.
- Authorized JavaScript may provide non-structural form behavior and UI assistance; it must not construct, reorder, or
  replace declarative form structure.

### Core terminology and translations

- Reuse existing Frappe and ERPNext labels whenever they accurately express the intended meaning. Avoid tiny wording
  changes that require new translations.
- Prefer existing core terms for Select options with equivalent semantics, and follow core fieldname conventions for
  equivalent concepts.
- Inspect the relevant core implementation and translation strings before introducing new terminology. Never reuse a
  misleading label just to avoid a translation.
- If no core term fits, explain the difference and propose an accurate name.

### Core functionality and business logic

- Inspect Frappe, ERPNext, declared dependencies, and existing app helpers before implementing new behavior. Verify the
  installed source rather than assuming compatibility from memory.
- Prefer existing DocTypes, APIs, functions, utilities, and business workflows over parallel custom implementations. Do
  not copy core logic when it can be reused.
- Use supported entry points and preserve validations, permissions, and document lifecycles. Do not bypass them merely
  to make an operation easier.
- Add custom behavior for a verified gap, and explain that gap before editing.
- Keep authoritative validation, calculations, state transitions, and data integrity in Python. JavaScript may
  orchestrate necessary UI interaction and feedback.
- Keep controllers focused. Introduce shared helpers when they remove real duplication.
- For workflows creating related documents, define ownership, retry behavior, cancellation, and recovery before
  implementing automation.

### Hooks and core overrides

- Every new hook requires the owner's explicit authorization, including document events, scheduled tasks, lifecycle
  hooks, and other hook registrations.
- Adding or changing core overrides also requires explicit authorization. Do not edit or bypass core behavior as an
  incidental part of a feature.
- Approval must cover the particular hook or override. A general feature request does not implicitly approve that
  mechanism.
- Explain the trigger, affected behavior, scope, and why existing supported mechanisms are insufficient. Preserve
  existing hooks during documentation normalization.

### Data and transaction safety

- Do not inspect production or restored production business data unless the owner explicitly requests it for the current
  task. Use only the necessary data.
- Do not create, submit, cancel, or modify real business documents without explicit authorization. Documentation of an
  existing production practice is not permission.
- Use controlled test data and rollback whenever possible for accounting, inventory, shipment, receipt, and other
  transactional tests.
- Do not run destructive migrations or improvised schema changes.
- Prefer Frappe document APIs, database APIs, and query builder over raw SQL. Use raw SQL only for a demonstrated need,
  preserving integrity within the authorized scope.
- Never commit or expose credentials, tokens, sensitive payloads, or unnecessary personal data in documentation, logs,
  examples, or tool output.
- Access to code or a database provides evidence, not authority to redefine business policy.

### Verification and completion

- Inspect the complete scoped diff and confirm unrelated work was preserved.
- Run `git diff --check`. Check syntax for changed Python and JavaScript source.
- Run focused checks and meaningful tests appropriate to the changed behavior, plus the requirements of applicable
  module guides.
- For UI changes, verify the actual interaction and Frappe-regenerated files.
- For transactional behavior, verify relevant retries, cancellation, and rollback using controlled data. Do not treat
  empty test scaffolds as coverage.
- Report what changed, why, what was tested, and unresolved limitations or decisions. Do not claim untested behavior is
  verified.
- Deployment and production data changes require their own applicable authorization; a successful local check or
  documentation update does not grant it.
<!-- END SHARED RULES -->

## Repository rules — Grupo Real Tools

### Purpose and scope

This repository contains ERPNext and HRMS extensions used across Grupo Real companies, including FT, CL, and QB.
Preserve the distinction between implemented functionality, module intent, and future implementation phases.

### Required reading

- Read the root [README.md](README.md) for app scope and module entry points.
- Before working inside a module, follow its guide under Module guides, even if the session started at the repository
  root.
- Read the module's technical references and required verification before proposing implementation.

### Architecture and dependencies

- Dependency and tool configuration lives in [pyproject.toml](pyproject.toml). It declares Python 3.14 or later and
  Frappe/ERPNext 16. Verify the installed source before relying on core behavior.
- Keep module models, invariants, phases, and detailed verification in their existing local guides. Do not centralize or
  replace them with a generic description of the app.
- Keep Spanish translations in [grupo_real_tools/locale/es.po](grupo_real_tools/locale/es.po), using English source
  strings as `msgid` values.
- The shared 120-character convention applies to Markdown documentation. Preserve the Python formatter configuration in
  pyproject.toml; documentation normalization does not change code formatting settings.

### Repository-wide constraints

- If a module lacks a local guide, apply the root instructions and propose a guide before broad or sensitive work. This
  does not authorize inventing module rules.
- When the owner's conclusion is wrong, say so clearly and explain why without becoming dismissive or adversarial.
  Prefer a supported correction over reassurance and a precise unknown over a fabricated answer.
- Before declaring a task complete, the coordinating agent must verify scope, authorization, and the full scoped diff.
  Run the affected module's required checks and report what was implemented, what was deliberately not implemented, and
  what still needs a decision.

### Module guides

- **Layaway:** read [AGENTS.md](grupo_real_tools/layaway/AGENTS.md) and its
  [README.md](grupo_real_tools/layaway/README.md).
- **Payment Settlement:** read [AGENTS.md](grupo_real_tools/payment_settlement/AGENTS.md) and its
  [README.md](grupo_real_tools/payment_settlement/README.md).
- **Procurement:** read [README.md](grupo_real_tools/procurement/README.md) and
  [AGENTS.md](grupo_real_tools/procurement/AGENTS.md).
