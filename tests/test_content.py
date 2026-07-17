from datetime import date
from pathlib import Path

from bible_bot.content import BibleCatalog

DATA_DIR = Path(__file__).resolve().parents[1] / "bible_bot" / "data"


def test_plan_has_all_260_new_testament_chapters_in_order() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    assert len(catalog.main_plan) == 260
    assert len(set(catalog.main_plan)) == 260
    assert catalog.main_plan[0] == "MAT.1"
    assert catalog.main_plan[-1] == "REV.22"
    assert all(len(key.split(".")) == 2 for key in catalog.main_plan)
    assert all(catalog.get_chapter(key).key == key for key in catalog.main_plan)


def test_primary_corpus_contains_chapter_texts_not_verse_records() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    assert not (DATA_DIR / "new_testament.json").exists()
    assert catalog.meta["unit"] == "chapter"
    assert catalog.meta["schema_version"] == 2
    assert all(
        isinstance(chapter_text, str)
        for book in catalog.books.values()
        for chapter_text in book["chapters"].values()
    )


def test_synodal_chapter_rendering() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    chapter = catalog.get_chapter("1TH.5")
    assert chapter.reference == "1 Фессалоникийцам 5"
    assert "Всегда радуйтесь" in chapter.text
    assert "Непрестанно молитесь" in chapter.text


def test_legacy_verse_key_resolves_to_the_whole_chapter() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    chapter = catalog.get_chapter("JHN.3.16.17")
    assert chapter.key == "JHN.3"
    assert chapter.reference == "Иоанна 3"
    assert len(chapter.lines) == 36


def test_global_plan_is_shared_by_calendar_date() -> None:
    catalog = BibleCatalog.from_data_dir(DATA_DIR)
    anchor = date(2026, 7, 16)
    first = catalog.select(mode="global", position=99, local_date=anchor, anchor_date=anchor)
    second = catalog.select(mode="global", position=0, local_date=anchor, anchor_date=anchor)
    assert first.chapter_key == second.chapter_key == catalog.main_plan[0]


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
            assert len(reference.split(".")) == 2
            assert catalog.get_chapter(reference).key == reference
