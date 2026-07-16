# Graph Report - bible-bot  (2026-07-16)

## Corpus Check
- 22 files · ~146,035 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 149 nodes · 346 edges · 10 communities (8 shown, 2 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

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

## God Nodes (most connected - your core abstractions)
1. `Database` - 33 edges
2. `create_router()` - 29 edges
3. `BibleCatalog` - 18 edges
4. `DailyScheduler` - 17 edges
5. `User` - 14 edges
6. `next_delivery_at()` - 12 edges
7. `parse_clock_time()` - 11 edges
8. `Passage` - 9 edges
9. `Bible Bot` - 9 edges
10. `main()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `FakeBot` --uses--> `BibleCatalog`  [INFERRED]
  tests/test_scheduler.py → bible_bot/content.py
- `FakeBot` --uses--> `Database`  [INFERRED]
  tests/test_scheduler.py → bible_bot/database.py
- `database()` --calls--> `Database`  [EXTRACTED]
  tests/test_scheduler.py → bible_bot/database.py
- `FakeBot` --uses--> `DailyScheduler`  [INFERRED]
  tests/test_scheduler.py → bible_bot/scheduler.py
- `test_parse_clock_time()` --calls--> `parse_clock_time()`  [EXTRACTED]
  tests/test_time_utils.py → bible_bot/time_utils.py

## Import Cycles
- None detected.

## Communities (10 total, 2 thin omitted)

### Community 0 - "Database"
Cohesion: 0.10
Nodes (10): Database, date, datetime, Path, Connection, Row, database(), test_favorites_toggle() (+2 more)

### Community 1 - "handlers.py"
Cohesion: 0.25
Nodes (17): Settings, create_router(), date, completion_keyboard(), confirmation_keyboard(), daily_verse_keyboard(), settings_keyboard(), stop_confirmation_keyboard() (+9 more)

### Community 2 - "scheduler.py"
Cohesion: 0.22
Nodes (11): Passage, PlanSelection, User, activated_text(), completion_text(), context_text(), favorites_text(), schedule_confirmation_text() (+3 more)

### Community 3 - "DailyScheduler"
Cohesion: 0.19
Nodes (9): main(), run(), DailyScheduler, date, Bot, database(), FakeBot, test_scheduler_pauses_after_final_passage() (+1 more)

### Community 4 - "next_delivery_at"
Cohesion: 0.24
Nodes (13): format_clock_time(), next_delivery_at(), normalize_timezone(), parse_clock_time(), datetime, Return the next local delivery time converted to UTC.      ``force_tomorrow`` is, validate_timezone(), test_force_tomorrow_prevents_second_daily_message() (+5 more)

### Community 5 - "BibleCatalog"
Cohesion: 0.21
Nodes (8): BibleCatalog, date, Path, test_all_theme_references_are_valid(), test_context_stays_inside_chapter(), test_global_plan_is_shared_by_calendar_date(), test_plan_has_365_unique_entries_and_expected_finale(), test_synodal_passage_rendering()

### Community 6 - "Bible Bot"
Cohesion: 0.17
Nodes (10): Data notices, Bible Bot, Docker, Как работает доставка, Команды, Локальный запуск, Обновление корпуса, Пользовательский сценарий (+2 more)

### Community 7 - "build_bible_data.py"
Cohesion: 0.32
Nodes (11): build_bible(), build_plan(), clean_text(), covered_by_featured(), fetch(), key_parts(), main(), parse_external_reference() (+3 more)

## Knowledge Gaps
- **10 isolated node(s):** `bible-bot`, `Data notices`, `Пользовательский сценарий`, `Команды`, `Локальный запуск` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `handlers.py`, `scheduler.py`, `DailyScheduler`?**
  _High betweenness centrality (0.273) - this node is a cross-community bridge._
- **Why does `BibleCatalog` connect `BibleCatalog` to `handlers.py`, `scheduler.py`, `DailyScheduler`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Why does `create_router()` connect `handlers.py` to `Database`, `scheduler.py`, `DailyScheduler`, `next_delivery_at`, `BibleCatalog`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Database` (e.g. with `DailyScheduler` and `FakeBot`) actually correct?**
  _`Database` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `BibleCatalog` (e.g. with `DailyScheduler` and `FakeBot`) actually correct?**
  _`BibleCatalog` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `DailyScheduler` (e.g. with `BibleCatalog` and `PlanSelection`) actually correct?**
  _`DailyScheduler` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Daily New Testament verse bot.`, `Return the next local delivery time converted to UTC.      ``force_tomorrow`` is`, `bible-bot` to the rest of the system?**
  _12 weakly-connected nodes found - possible documentation gaps or missing edges._