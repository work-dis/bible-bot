from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Chapter:
    key: str
    book_code: str
    book_name: str
    number: int
    text: str

    @property
    def reference(self) -> str:
        return f"{self.book_name} {self.number}"

    @property
    def lines(self) -> tuple[str, ...]:
        return tuple(self.text.splitlines())


@dataclass(frozen=True, slots=True)
class PlanSelection:
    chapter_key: str
    position: int
    size: int
    is_final: bool


class BibleCatalog:
    def __init__(self, chapters_path: Path, plan_path: Path) -> None:
        with chapters_path.open(encoding="utf-8") as source:
            corpus = json.load(source)
        with plan_path.open(encoding="utf-8") as source:
            plan = json.load(source)

        self.meta = corpus["_meta"]
        if self.meta.get("schema_version") != 2 or self.meta.get("unit") != "chapter":
            raise ValueError("The primary Bible corpus must use the chapter schema")

        self.books: dict[str, dict] = corpus["books"]
        self.theme_labels: dict[str, str] = plan["theme_labels"]
        self.main_plan: list[str] = plan["main"]
        self.themes: dict[str, list[str]] = {
            slug: list(dict.fromkeys(entries)) for slug, entries in plan["themes"].items()
        }
        self.sequential_plan = list(self.main_plan)

        expected_plan = self._build_chapter_plan()
        if self.main_plan != expected_plan:
            raise ValueError("The main plan must contain every New Testament chapter in order")
        if not self.main_plan:
            raise ValueError("The reading plan is empty")

        for key in self.main_plan:
            self.get_chapter(key)
        for entries in self.themes.values():
            for key in entries:
                if self.get_chapter(key).key != key:
                    raise ValueError("Theme plans must contain chapter keys only")

    @classmethod
    def from_data_dir(cls, data_dir: Path) -> BibleCatalog:
        return cls(data_dir / "new_testament_chapters.json", data_dir / "reading_plan.json")

    @staticmethod
    def parse_key(key: str) -> tuple[str, int]:
        try:
            book_code, chapter = key.split(".")
            return book_code, int(chapter)
        except (AttributeError, ValueError, TypeError) as exc:
            raise ValueError(f"Invalid chapter key: {key}") from exc

    @staticmethod
    def make_key(book_code: str, chapter: int) -> str:
        return f"{book_code}.{chapter}"

    def canonical_chapter_key(self, key: str) -> str:
        """Convert callbacks/favorites from the old verse-range format once."""

        try:
            parts = key.split(".")
        except (AttributeError, TypeError) as exc:
            raise ValueError(f"Invalid chapter key: {key}") from exc
        if len(parts) == 2:
            book_code, chapter = self.parse_key(key)
        elif len(parts) == 4:
            try:
                book_code, chapter_text, start_text, end_text = parts
                chapter = int(chapter_text)
                int(start_text)
                int(end_text)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid legacy chapter key: {key}") from exc
        else:
            raise ValueError(f"Invalid chapter key: {key}")

        chapter_key = self.make_key(book_code, chapter)
        try:
            self.books[book_code]["chapters"][str(chapter)]
        except KeyError as exc:
            raise KeyError(f"Chapter does not exist: {chapter_key}") from exc
        return chapter_key

    def get_chapter(self, key: str) -> Chapter:
        chapter_key = self.canonical_chapter_key(key)
        book_code, chapter_number = self.parse_key(chapter_key)
        book = self.books[book_code]
        chapter_text = book["chapters"][str(chapter_number)]
        if not isinstance(chapter_text, str) or not chapter_text.strip():
            raise ValueError(f"Chapter text is empty: {chapter_key}")
        return Chapter(
            key=chapter_key,
            book_code=book_code,
            book_name=book["reference_name"],
            number=chapter_number,
            text=chapter_text,
        )

    def select(
        self,
        *,
        mode: str,
        position: int,
        local_date: date,
        anchor_date: date,
    ) -> PlanSelection:
        if mode == "global":
            plan = self.main_plan
            selected_position = (local_date - anchor_date).days % len(plan)
        elif mode == "personal":
            plan = self.main_plan
            selected_position = position % len(plan)
        elif mode == "sequential":
            plan = self.sequential_plan
            selected_position = position % len(plan)
        elif mode.startswith("theme:"):
            slug = mode.partition(":")[2]
            if slug not in self.themes:
                raise ValueError(f"Unknown theme: {slug}")
            plan = self.themes[slug]
            selected_position = position % len(plan)
        else:
            raise ValueError(f"Unknown delivery mode: {mode}")

        return PlanSelection(
            chapter_key=plan[selected_position],
            position=selected_position,
            size=len(plan),
            is_final=selected_position == len(plan) - 1,
        )

    def _build_chapter_plan(self) -> list[str]:
        return [
            self.make_key(book_code, chapter_number)
            for book_code, book in self.books.items()
            for chapter_number in sorted(map(int, book["chapters"]))
        ]
