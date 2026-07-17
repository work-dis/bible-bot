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
        "JHN.3",
        "MRK.9",
        "JHN.20",
        "ROM.4",
        "ROM.10",
        "2CO.5",
        "GAL.2",
        "EPH.2",
        "HEB.11",
        "JAS.1",
        "1PE.1",
    ],
    "hope": [
        "MAT.12",
        "JHN.14",
        "ROM.5",
        "ROM.8",
        "ROM.12",
        "ROM.15",
        "2CO.4",
        "COL.1",
        "1TH.5",
        "HEB.6",
        "1PE.1",
    ],
    "love": [
        "MAT.22",
        "JHN.3",
        "JHN.13",
        "JHN.15",
        "ROM.5",
        "ROM.8",
        "ROM.12",
        "1CO.13",
        "COL.3",
        "1JN.3",
        "1JN.4",
    ],
    "prayer": [
        "MAT.6",
        "MAT.7",
        "MAT.18",
        "MRK.11",
        "LUK.11",
        "JHN.14",
        "ROM.12",
        "PHP.4",
        "1TH.5",
        "1TI.2",
        "JAS.1",
        "JAS.5",
    ],
    "jesus_words": [
        "MAT.5",
        "MAT.6",
        "MAT.7",
        "MAT.11",
        "MAT.22",
        "LUK.6",
        "JHN.8",
        "JHN.10",
        "JHN.11",
        "JHN.14",
        "JHN.16",
    ],
    "comfort": [
        "MAT.11",
        "JHN.14",
        "JHN.16",
        "ROM.8",
        "2CO.1",
        "2CO.4",
        "PHP.4",
        "1PE.5",
        "REV.21",
    ],
    "relationships": [
        "MAT.5",
        "MAT.7",
        "MAT.18",
        "MAT.22",
        "LUK.6",
        "ROM.12",
        "EPH.4",
        "COL.3",
        "JAS.1",
        "1PE.4",
        "1JN.4",
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


def build_chapter_corpus(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes.decode("utf-8-sig"))
    result = {
        "_meta": {
            "schema_version": 2,
            "unit": "chapter",
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
            lines = []
            for verse_element in chapter_element.findall("VERS"):
                verse_number = verse_element.attrib["vnumber"]
                verse_text = clean_text("".join(verse_element.itertext()))
                lines.append(f"{verse_number}\t{verse_text}")
            chapters[chapter_number] = "\n".join(lines)
        result["books"][code] = {
            "source_name": book_element.attrib["bname"],
            "reference_name": reference_name,
            "chapters": chapters,
        }
    return result


def key_parts(key: str) -> tuple[str, int]:
    code, chapter = key.split(".")
    return code, int(chapter)


def validate_key(corpus: dict, key: str) -> None:
    code, chapter = key_parts(key)
    try:
        chapter_text = corpus["books"][code]["chapters"][str(chapter)]
    except KeyError as exc:
        raise ValueError(f"Chapter is missing from the corpus: {key}") from exc
    if not chapter_text:
        raise ValueError(f"Chapter is empty in the corpus: {key}")


def build_plan(corpus: dict) -> dict:
    plan: list[str] = []
    for code, book in corpus["books"].items():
        for chapter_number in sorted(map(int, book["chapters"])):
            plan.append(f"{code}.{chapter_number}")

    themed_chapters = {}
    for slug, entries in THEMES.items():
        chapter_keys: list[str] = []
        for key in entries:
            validate_key(corpus, key)
            if key not in chapter_keys:
                chapter_keys.append(key)
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
    corpus = build_chapter_corpus(fetch(BIBLE_SOURCE))
    plan = build_plan(corpus)
    write_json(DATA_DIR / "new_testament_chapters.json", corpus)
    write_json(DATA_DIR / "reading_plan.json", plan)
    print(f"Built {len(corpus['books'])} books and {len(plan['main'])} daily chapters")


if __name__ == "__main__":
    main()
