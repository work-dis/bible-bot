from datetime import date
from pathlib import Path

from bible_bot.content import BibleCatalog

DATA_DIR = Path(__file__).resolve().parents[1] / "bible_bot" / "data"


def test_plan_has_365_unique_entries_and_expected_finale() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    assert len(catalog.main_plan) == 365
    assert len(set(catalog.main_plan)) == 365
    assert catalog.main_plan[-1] == "REV.22.21.21"


def test_synodal_passage_rendering() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    passage = catalog.get_passage("1TH.5.16.18")
    assert passage.reference == "1 Фессалоникийцам 5:16–18"
    assert "Всегда радуйтесь" in passage.text
    assert "Непрестанно молитесь" in passage.text


def test_global_plan_is_shared_by_calendar_date() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    anchor = date(2026, 7, 16)
    first = catalog.select(mode="global", position=99, local_date=anchor, anchor_date=anchor)
    second = catalog.select(mode="global", position=0, local_date=anchor, anchor_date=anchor)
    assert first.passage_key == second.passage_key == catalog.main_plan[0]


def test_context_stays_inside_chapter() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    context = catalog.get_context("JHN.3.16.17")
    assert context.verse_start == 14
    assert context.verse_end == 19


def test_all_theme_references_are_valid() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    assert set(catalog.themes) == {
        "faith",
        "hope",
        "love",
        "prayer",
        "jesus_words",
        "comfort",
        "relationships",
    }
    for references in catalog.themes.values():
        assert references
        for reference in references:
            catalog.get_passage(reference)
