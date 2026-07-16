# Graph Report - bible-bot  (2026-07-16)

## Corpus Check
- 28 files · ~149,431 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 221 nodes · 502 edges · 13 communities (10 shown, 3 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 17 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `900b105b`
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
- `FakeBot` --uses--> `BibleCatalog`  [INFERRED]
  tests/test_scheduler.py → bible_bot/content.py
- `FakeBot` --uses--> `Database`  [INFERRED]
  tests/test_scheduler.py → bible_bot/database.py
- `FakeBot` --uses--> `DailyScheduler`  [INFERRED]
  tests/test_scheduler.py → bible_bot/scheduler.py
- `test_parse_clock_time()` --calls--> `parse_clock_time()`  [EXTRACTED]
  tests/test_time_utils.py → bible_bot/time_utils.py
- `test_parse_clock_time_rejects_invalid_value()` --calls--> `parse_clock_time()`  [EXTRACTED]
  tests/test_time_utils.py → bible_bot/time_utils.py

## Import Cycles
- None detected.

## Communities (13 total, 3 thin omitted)

### Community 0 - "Database"
Cohesion: 0.09
Nodes (6): date, datetime, Path, SQLiteDatabase, Connection, Row

### Community 1 - "handlers.py"
Cohesion: 0.17
Nodes (26): Passage, PlanSelection, User, create_router(), date, completion_keyboard(), confirmation_keyboard(), daily_verse_keyboard() (+18 more)

### Community 2 - "scheduler.py"
Cohesion: 0.12
Nodes (6): AsyncConnection, PendingInput, PostgresDatabase, date, datetime, Short-lived PostgreSQL connections suited to Neon PgBouncer.

### Community 3 - "DailyScheduler"
Cohesion: 0.13
Nodes (18): main(), run(), Database, Select PostgreSQL for DATABASE_URL and SQLite for local development/tests., DailyScheduler, date, Bot, database() (+10 more)

### Community 4 - "next_delivery_at"
Cohesion: 0.27
Nodes (12): next_delivery_at(), normalize_timezone(), parse_clock_time(), datetime, Return the next local delivery time converted to UTC.      ``force_tomorrow`` is, validate_timezone(), test_force_tomorrow_prevents_second_daily_message(), test_next_delivery_uses_local_timezone() (+4 more)

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
Cohesion: 0.16
Nodes (13): Path, Settings, cron_get(), cron_post(), dispatch_due(), get_runtime(), _require_cron_secret(), _require_webhook_secret() (+5 more)

## Knowledge Gaps
- **13 isolated node(s):** `bible-bot`, `Data notices`, `Сценарий пользователя`, `Архитектура на Vercel`, `1. Neon` (+8 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PostgresDatabase` connect `scheduler.py` to `Database`, `handlers.py`, `DailyScheduler`?**
  _High betweenness centrality (0.185) - this node is a cross-community bridge._
- **Why does `SQLiteDatabase` connect `Database` to `scheduler.py`?**
  _High betweenness centrality (0.164) - this node is a cross-community bridge._
- **Why does `Database` connect `DailyScheduler` to `Database`, `handlers.py`, `scheduler.py`, `app.py`?**
  _High betweenness centrality (0.146) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `PostgresDatabase` (e.g. with `Database` and `PendingInput`) actually correct?**
  _`PostgresDatabase` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `BibleCatalog` (e.g. with `DailyScheduler` and `Runtime`) actually correct?**
  _`BibleCatalog` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `User` (e.g. with `PostgresDatabase` and `DailyScheduler`) actually correct?**
  _`User` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Daily New Testament verse bot.`, `Select PostgreSQL for DATABASE_URL and SQLite for local development/tests.`, `Short-lived PostgreSQL connections suited to Neon PgBouncer.` to the rest of the system?**
  _17 weakly-connected nodes found - possible documentation gaps or missing edges._