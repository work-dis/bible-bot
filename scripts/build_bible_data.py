#!/usr/bin/env python3
"""Build the local New Testament corpus and chapter-by-chapter reading plan.

The generated files are committed so production does not depend on the source
at runtime. Re-run this script only when intentionally refreshing data.
"""

from __future__ import annotations

import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "bible_bot" / "data"

BIBLE_SOURCE = (
    "https://raw.githubusercontent.com/seven1m/open-bibles/master/rus-synodal.zefania.xml"
)

BOOKS = {
    40: ("MAT", "Matthew", "Матфея"),
    41: ("MRK", "Mark", "Марка"),
    42: ("LUK", "Luke", "Луки"),
    43: ("JHN", "John", "Иоанна"),
    44: ("ACT", "Acts", "Деяния"),
    45: ("ROM", "Romans", "Римлянам"),
    46: ("1CO", "1 Corinthians", "1 Коринфянам"),
    47: ("2CO", "2 Corinthians", "2 Коринфянам"),
    48: ("GAL", "Galatians", "Галатам"),
    49: ("EPH", "Ephesians", "Ефесянам"),
    50: ("PHP", "Philippians", "Филиппийцам"),
    51: ("COL", "Colossians", "Колоссянам"),
    52: ("1TH", "1 Thessalonians", "1 Фессалоникийцам"),
    53: ("2TH", "2 Thessalonians", "2 Фессалоникийцам"),
    54: ("1TI", "1 Timothy", "1 Тимофею"),
    55: ("2TI", "2 Timothy", "2 Тимофею"),
    56: ("TIT", "Titus", "Титу"),
    57: ("PHM", "Philemon", "Филимону"),
    58: ("HEB", "Hebrews", "Евреям"),
    59: ("JAS", "James", "Иакова"),
    60: ("1PE", "1 Peter", "1 Петра"),
    61: ("2PE", "2 Peter", "2 Петра"),
    62: ("1JN", "1 John", "1 Иоанна"),
    63: ("2JN", "2 John", "2 Иоанна"),
    64: ("3JN", "3 John", "3 Иоанна"),
    65: ("JUD", "Jude", "Иуды"),
    66: ("REV", "Revelation", "Откровение"),
}

THEMES = {
    "faith": [
        "JHN.3.16.17",
        "MRK.9.23.24",
        "JHN.20.29.29",
        "ROM.4.20.21",
        "ROM.10.17.17",
        "2CO.5.7.7",
        "GAL.2.20.20",
        "EPH.2.8.10",
        "HEB.11.1.1",
        "HEB.11.6.6",
        "JAS.1.6.6",
        "1PE.1.8.9",
    ],
    "hope": [
        "MAT.12.21.21",
        "JHN.14.1.3",
        "ROM.5.3.5",
        "ROM.8.24.25",
        "ROM.12.12.12",
        "ROM.15.4.4",
        "ROM.15.13.13",
        "2CO.4.16.18",
        "COL.1.27.27",
        "1TH.5.8.8",
        "HEB.6.19.19",
        "1PE.1.3.4",
    ],
    "love": [
        "MAT.22.37.39",
        "JHN.3.16.17",
        "JHN.13.34.35",
        "JHN.15.12.13",
        "ROM.5.8.8",
        "ROM.8.38.39",
        "ROM.12.9.10",
        "1CO.13.4.7",
        "1CO.13.13.13",
        "COL.3.12.14",
        "1JN.3.18.18",
        "1JN.4.7.8",
    ],
    "prayer": [
        "MAT.6.6.6",
        "MAT.7.7.8",
        "MAT.18.19.20",
        "MRK.11.24.24",
        "LUK.11.9.10",
        "JHN.14.13.14",
        "ROM.12.12.12",
        "PHP.4.6.7",
        "1TH.5.16.18",
        "1TI.2.1.1",
        "JAS.1.5.6",
        "JAS.5.16.16",
    ],
    "jesus_words": [
        "MAT.5.14.16",
        "MAT.6.33.34",
        "MAT.7.7.8",
        "MAT.11.28.30",
        "MAT.22.37.39",
        "LUK.6.31.31",
        "JHN.8.12.12",
        "JHN.10.10.11",
        "JHN.11.25.26",
        "JHN.14.6.6",
        "JHN.14.27.27",
        "JHN.16.33.33",
    ],
    "comfort": [
        "MAT.11.28.30",
        "JHN.14.1.3",
        "JHN.14.27.27",
        "JHN.16.33.33",
        "ROM.8.28.28",
        "ROM.8.31.32",
        "ROM.8.38.39",
        "2CO.1.3.4",
        "2CO.4.16.18",
        "PHP.4.6.7",
        "1PE.5.6.7",
        "REV.21.3.4",
    ],
    "relationships": [
        "MAT.5.44.44",
        "MAT.7.12.12",
        "MAT.18.15.15",
        "MAT.22.39.39",
        "LUK.6.31.31",
        "ROM.12.10.10",
        "ROM.12.14.14",
        "ROM.12.18.18",
        "EPH.4.2.3",
        "EPH.4.31.32",
        "COL.3.12.14",
        "JAS.1.19.19",
        "1PE.4.8.10",
        "1JN.4.20.21",
    ],
}

THEME_LABELS = {
    "faith": "Вера",
    "hope": "Надежда",
    "love": "Любовь",
    "prayer": "Молитва",
    "jesus_words": "Слова Иисуса",
    "comfort": "Утешение",
    "relationships": "Отношения с людьми",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "bible-bot-data-builder/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return response.read()


def clean_text(value: str) -> str:
    return " ".join(value.replace("\ufeff", "").split())


def build_bible(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes.decode("utf-8-sig"))
    result = {
        "_meta": {
            "translation": "Синодальный перевод",
            "edition": "1876, электронная редакция 1956",
            "language": "ru",
            "source": BIBLE_SOURCE,
            "license": "Public Domain",
        },
        "books": {},
    }

    for book_element in root.findall("BIBLEBOOK"):
        number = int(book_element.attrib["bnumber"])
        if number not in BOOKS:
            continue
        code, _, reference_name = BOOKS[number]
        chapters = {}
        for chapter_element in book_element.findall("CHAPTER"):
            chapter_number = chapter_element.attrib["cnumber"]
            verses = {}
            for verse_element in chapter_element.findall("VERS"):
                verse_number = verse_element.attrib["vnumber"]
                verses[verse_number] = clean_text("".join(verse_element.itertext()))
            chapters[chapter_number] = verses
        result["books"][code] = {
            "source_name": book_element.attrib["bname"],
            "reference_name": reference_name,
            "chapters": chapters,
        }
    return result


def key_parts(key: str) -> tuple[str, int, int, int]:
    code, chapter, start, end = key.split(".")
    return code, int(chapter), int(start), int(end)


def validate_key(bible: dict, key: str) -> None:
    code, chapter, start, end = key_parts(key)
    try:
        chapter_data = bible["books"][code]["chapters"][str(chapter)]
        for verse in range(start, end + 1):
            chapter_data[str(verse)]
    except KeyError as exc:
        raise ValueError(f"Reference is missing from the corpus: {key}") from exc


def build_plan(bible: dict) -> dict:
    plan: list[str] = []
    for code, book in bible["books"].items():
        for chapter_number in sorted(map(int, book["chapters"])):
            chapter = book["chapters"][str(chapter_number)]
            plan.append(f"{code}.{chapter_number}.1.{max(map(int, chapter))}")

    themed_chapters = {}
    for slug, entries in THEMES.items():
        chapter_keys = []
        for key in entries:
            validate_key(bible, key)
            code, chapter_number, _, _ = key_parts(key)
            chapter = bible["books"][code]["chapters"][str(chapter_number)]
            chapter_key = f"{code}.{chapter_number}.1.{max(map(int, chapter))}"
            if chapter_key not in chapter_keys:
                chapter_keys.append(chapter_key)
        themed_chapters[slug] = chapter_keys

    return {
        "_meta": {
            "count": len(plan),
            "notes": "One complete New Testament chapter per day in canonical book order.",
        },
        "main": plan,
        "theme_labels": THEME_LABELS,
        "themes": themed_chapters,
    }


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    bible = build_bible(fetch(BIBLE_SOURCE))
    plan = build_plan(bible)
    write_json(DATA_DIR / "new_testament.json", bible)
    write_json(DATA_DIR / "reading_plan.json", plan)
    verse_count = sum(
        len(chapter) for book in bible["books"].values() for chapter in book["chapters"].values()
    )
    print(f"Built {len(bible['books'])} books, {verse_count} verses, {len(plan['main'])} days")


if __name__ == "__main__":
    main()
