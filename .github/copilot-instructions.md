# Copilot instructions for election_system (Django)

## Big picture
- Django 5 project with a single app `voting`. Core models: `ClientProfile` (one per client `User`, with mirrored `visitor_user`), `Voter`, and `Zone`.
- Denormalized counters are used for performance: `ClientProfile.total_voters/voted_count` and `Zone.total_voters/voted_count`. After bulk changes call `voting.views.recompute_client_counters(profile)`.
- Auth roles are inferred from user relations, not groups: clients have `request.user.clientprofile`; visitors have `request.user.visitor_profile` (auto-synced via signals in `voting/models.py`).
- i18n is disabled. All UI/messages are Spanish-only; do not introduce runtime translation.

## Settings and routing
- Settings are layered in `election_system/settings/`: `base.py`, `development.py`, `production.py`. `manage.py`/`asgi.py` default to `development`; override `DJANGO_SETTINGS_MODULE` (e.g. `election_system.settings.production`) for prod tasks.
- Production is wired for Render.com: see `render.yaml`, `wsgi.py` and `STATICFILES_STORAGE=whitenoise...`.
- Root URLs are in `election_system/urls.py` (used by `ROOT_URLCONF`). The top-level `urls.py` at repo root is legacy and not used by production—avoid editing it.
- Login uses Spanish messages via `SpanishAuthenticationForm` (`election_system/forms.py`) and redirects authenticated users away from the login page.

## Key flows and APIs (voting app)
- Dashboards (namespaced `voting:`):
  - `voting:main_dashboard` (client users) and `voting:visitor_dashboard` (visitor users). `voting:custom_redirect` chooses destination based on role.
- Excel import (.xlsx via pandas/openpyxl):
  - Required columns: `dni`, `Apellido`, `Nombre`. Optional: `Sexo`, `Direccion`, `Mesa`, `Orden`, `Establecimiento`.
  - Main upload on `main_dashboard` assigns default zone "Sin asignar". Use `upload_voters_to_zone` to import to a specific `Zone`.
- JSON endpoints (see `voting/urls.py` and `voting/views.py`):
  - POST `/voting/mark_by_dni_set/`: set `voted=True` by DNI (fast path).
  - POST `/voting/mark_voted/<id>/`: toggle `voted` for a voter, with denorm counter update.
  - POST `/voting/search_voter_by_dni/`: find voter in current client’s scope.
  - GET `/voting/voter_stats/`, `/voting/zone_stats/`: stats using denormalized counters with auto-heal if zero.
  - GET `/voting/pending_voters/`: paginated not-voted list, filterable by `zone_id`.
  - POST `/voting/upload_zone/`: import voters into a named zone (upsert by `(client,dni)`).
  - POST `/voting/clear_voters/`: delete all voters and zones for the client.
  - POST `/voting/validate_password/`: client-side precheck for destructive actions.
- Destructive actions require the hardcoded confirmation password `09285252` (see views). Keep consistent if adding similar flows.

## Conventions and patterns
- Role resolution: check `hasattr(user, 'clientprofile')` or `hasattr(user, 'visitor_profile')`. Use `get_object_or_404(ClientProfile, visitor_user=request.user)` for visitors.
- Upsert pattern: locate by `(client, dni)`; update selective fields with `update_fields`; keep `voted` untouched on imports.
- Counters: when flipping `voted`, increment/decrement with `F()` on both `ClientProfile` and `Zone` and fall back to `recompute_client_counters` if needed.
- Indexes: `Voter` defines partial/compound indexes to optimize pending lookups and ordering; preserve them if you change fields.
- Language middleware/i18n is removed (`voting/middleware.py`); don’t reintroduce `activate()` or translation toggles.

## Local dev and common commands
- Database is PostgreSQL in `development.py`. Ensure a local DB matching NAME/USER/PASSWORD/HOST/PORT, or temporarily point to your DB.
- Typical workflow (dev defaults to `development` settings out of the box):
  - Migrate: `python manage.py migrate`.
  - Run: `python manage.py runserver`.
  - Create admin: `python manage.py createsuperuser`.
- Tests: `voting/tests.py` is minimal; run `python manage.py test`. Add app-specific tests under `voting/tests/` if you extend behavior.

## Examples for extending
- New view/API under `voting`:
  - Add view in `voting/views.py`, guard with `@login_required`, resolve role as above, and return JSON via `JsonResponse`.
  - Wire in `voting/urls.py` with the `app_name='voting'` namespace; reference via `voting:your_name`.
- After bulk imports/edits to voters/zones, always call `recompute_client_counters(client_profile)`.

## Communication Style
- Always respond in a verbose, didactic manner: Break down explanations into clear, numbered steps. Use analogies or real-world examples to illustrate concepts. Explain *why* a solution works, not just *how* to implement it.
- Be educational like a patient coding mentor: Include tips for best practices, potential pitfalls, and follow-up questions to deepen understanding.
- Structure responses: Start with a summary, then detailed steps/code, end with testing/refinement advice. Aim for comprehensive but readable (under 2000 words unless complex).
- Use inclusive, encouraging language: Phrases like "Let's explore this together" or "Here's why this approach scales well."

## Coding Guidelines
- Prioritize clean, readable code: Follow PEP8 for Python, ESLint for JS, etc. Comment liberally for teachability.
- When generating code, always include:
  1. A brief rationale.
  2. The code block.
  3. An explanation of key lines.
  4. Edge cases and error handling.
- For debugging/fixes: Describe the issue root cause first, then the solution.