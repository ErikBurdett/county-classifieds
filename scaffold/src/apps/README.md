# Django application boundaries

Generate/register apps only when their milestone begins. The approved boundaries are documented in `docs/01-ARCHITECTURE.md`:

- `core`
- `accounts`
- `locations`
- `catalog`
- `listings`
- `media`
- `moderation`
- `billing`
- `favorites`
- `notifications`
- `operations`

Phase 1B/later apps such as saved searches, messaging, ratings, and dealer tooling must not be added to MVP merely because their future names are known.
