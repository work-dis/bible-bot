# Graph Report - bible-bot  (2026-07-16)

## Corpus Check
- 27 files · ~149,419 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 220 nodes · 501 edges · 14 communities (11 shown, 3 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 17 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3aee4a37`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Database
- handlers.py
- scheduler.py
- DailyScheduler
- next_delivery_at
- BibleCatalog
- Bible Bot
- build_bible_data.py
- __init__.py
- bible-bot
- app.py
- test_database.py
- configure_telegram.py

## God Nodes (most connected - your core abstractions)
1. `PostgresDatabase` - 34 edges
2. `create_router()` - 31 edges
3. `SQLiteDatabase` - 30 edges
4. `BibleCatalog` - 20 edges
5. `User` - 20 edges
6. `Database` - 20 edges
7. `DailyScheduler` - 20 edges
8. `next_delivery_at()` - 12 edges
9. `parse_clock_time()` - 11 edges
10. `get_runtime()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Runtime` --uses--> `BibleCatalog`  [INFERRED]
  app.py → bible_bot/content.py
- `Runtime` --uses--> `Database`  [INFERRED]
  app.py → bible_bot/database.py
- `Runtime` --uses--> `DailyScheduler`  [INFERRED]
  app.py → bible_bot/scheduler.py
- `FakeBot` --uses--> `BibleCatalog`  [INFERRED]
  tests/test_scheduler.py → bible_bot/content.py
- `Runtime` --uses--> `Settings`  [INFERRED]
  app.py → bible_bot/config.py

## Import Cycles
- None detected.

## Communities (14 total, 3 thin omitted)

### Community 0 - "Database"
Cohesion: 0.08
Nodes (6): date, datetime, Path, SQLiteDatabase, Connection, Row

### Community 1 - "handlers.py"
Cohesion: 0.20
Nodes (22): Passage, create_router(), date, completion_keyboard(), confirmation_keyboard(), daily_verse_keyboard(), settings_keyboard(), stop_confirmation_keyboard() (+14 more)

### Community 2 - "scheduler.py"
Cohesion: 0.13
Nodes (7): AsyncConnection, PendingInput, User, PostgresDatabase, date, datetime, Short-lived PostgreSQL connections suited to Neon PgBouncer.

### Community 3 - "DailyScheduler"
Cohesion: 0.16
Nodes (13): main(), run(), PlanSelection, Database, Select PostgreSQL for DATABASE_URL and SQLite for local development/tests., DailyScheduler, date, datetime (+5 more)

### Community 4 - "next_delivery_at"
Cohesion: 0.26
Nodes (13): format_clock_time(), next_delivery_at(), normalize_timezone(), parse_clock_time(), datetime, Return the next local delivery time converted to UTC.      ``force_tomorrow`` is, validate_timezone(), test_force_tomorrow_prevents_second_daily_message() (+5 more)

### Community 5 - "BibleCatalog"
Cohesion: 0.21
Nodes (8): BibleCatalog, date, Path, test_all_theme_references_are_valid(), test_context_stays_inside_chapter(), test_global_plan_is_shared_by_calendar_date(), test_plan_has_365_unique_entries_and_expected_finale(), test_synodal_passage_rendering()

### Community 6 - "Bible Bot"
Cohesion: 0.12
Nodes (14): Data notices, 1. Neon, 2. Vercel, 3. Telegram webhook, 4. Запуск ежедневной доставки, Bible Bot, Архитектура на Vercel, Деплой (+6 more)

### Community 7 - "build_bible_data.py"
Cohesion: 0.32
Nodes (11): build_bible(), build_plan(), clean_text(), covered_by_featured(), fetch(), key_parts(), main(), parse_external_reference() (+3 more)

### Community 10 - "app.py"
Cohesion: 0.17
Nodes (13): cron_get(), cron_post(), dispatch_due(), get_runtime(), _require_cron_secret(), _require_webhook_secret(), Runtime, _same_secret() (+5 more)

### Community 11 - "test_database.py"
Cohesion: 0.46
Nodes (7): database(), test_favorites_toggle(), test_pending_input_survives_and_can_be_cleared(), test_plan_anchor_is_stable(), test_scheduler_lock_has_an_owner_and_expiry(), test_telegram_update_is_claimed_once(), test_user_schedule_and_delivery_claim()

## Knowledge Gaps
- **13 isolated node(s):** `bible-bot`, `Data notices`, `Сценарий пользователя`, `Архитектура на Vercel`, `1. Neon` (+8 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PostgresDatabase` connect `scheduler.py` to `Database`, `DailyScheduler`?**
  _High betweenness centrality (0.186) - this node is a cross-community bridge._
- **Why does `SQLiteDatabase` connect `Database` to `scheduler.py`?**
  _High betweenness centrality (0.164) - this node is a cross-community bridge._
- **Why does `Database` connect `DailyScheduler` to `Database`, `handlers.py`, `scheduler.py`, `app.py`, `test_database.py`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `PostgresDatabase` (e.g. with `Database` and `PendingInput`) actually correct?**
  _`PostgresDatabase` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `BibleCatalog` (e.g. with `Runtime` and `DailyScheduler`) actually correct?**
  _`BibleCatalog` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `User` (e.g. with `PostgresDatabase` and `DailyScheduler`) actually correct?**
  _`User` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Daily New Testament verse bot.`, `Select PostgreSQL for DATABASE_URL and SQLite for local development/tests.`, `Short-lived PostgreSQL connections suited to Neon PgBouncer.` to the rest of the system?**
  _17 weakly-connected nodes found - possible documentation gaps or missing edges._