from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Passage:
    key: str
    book_code: str
    book_name: str
    chapter: int
    verse_start: int
    verse_end: int
    verses: tuple[tuple[int, str], ...]

    @property
    def reference(self) -> str:
        suffix = str(self.verse_start)
        if self.verse_end != self.verse_start:
            suffix += f"–{self.verse_end}"
        return f"{self.book_name} {self.chapter}:{suffix}"

    @property
    def text(self) -> str:
        if len(self.verses) == 1:
            return self.verses[0][1]
        return " ".join(f"{number} {text}" for number, text in self.verses)


@dataclass(frozen=True, slots=True)
class PlanSelection:
    passage_key: str
    position: int
    size: int
    is_final: bool


class BibleCatalog:
    def __init__(self, bible_path: Path, plan_path: Path) -> None:
        with bible_path.open(encoding="utf-8") as source:
            bible = json.load(source)
        with plan_path.open(encoding="utf-8") as source:
            plan = json.load(source)

        self.meta = bible["_meta"]
        self.books: dict[str, dict] = bible["books"]
        self.book_order = list(self.books)
        self.main_plan: list[str] = plan["main"]
        self.theme_labels: dict[str, str] = plan["theme_labels"]
        self.themes: dict[str, list[str]] = plan["themes"]
        self.sequential_plan = sorted(self.main_plan, key=self._sort_key)

        if not self.main_plan:
            raise ValueError("The reading plan is empty")
        for key in self.main_plan:
            self.get_passage(key)
        for entries in self.themes.values():
            for key in entries:
                self.get_passage(key)

    @classmethod
    def from_data_dir(cls, data_dir: Path) -> BibleCatalog:
        return cls(data_dir / "new_testament.json", data_dir / "reading_plan.json")

    @staticmethod
    def parse_key(key: str) -> tuple[str, int, int, int]:
        try:
            book_code, chapter, verse_start, verse_end = key.split(".")
            return book_code, int(chapter), int(verse_start), int(verse_end)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid passage key: {key}") from exc

    def make_key(self, book_code: str, chapter: int, start: int, end: int | None = None) -> str:
        return f"{book_code}.{chapter}.{start}.{end or start}"

    def get_passage(self, key: str) -> Passage:
        book_code, chapter, start, end = self.parse_key(key)
        try:
            book = self.books[book_code]
            chapter_data = book["chapters"][str(chapter)]
            verses = tuple((number, chapter_data[str(number)]) for number in range(start, end + 1))
        except KeyError as exc:
            raise KeyError(f"Passage does not exist: {key}") from exc
        return Passage(
            key=key,
            book_code=book_code,
            book_name=book["reference_name"],
            chapter=chapter,
            verse_start=start,
            verse_end=end,
            verses=verses,
        )

    def get_context(self, key: str, radius: int = 2) -> Passage:
        book_code, chapter, start, end = self.parse_key(key)
        chapter_data = self.books[book_code]["chapters"][str(chapter)]
        last_verse = max(map(int, chapter_data))
        return self.get_passage(
            self.make_key(
                book_code,
                chapter,
                max(1, start - radius),
                min(last_verse, end + radius),
            )
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
            passage_key=plan[selected_position],
            position=selected_position,
            size=len(plan),
            is_final=selected_position == len(plan) - 1,
        )

    def _sort_key(self, key: str) -> tuple[int, int, int, int]:
        book_code, chapter, start, end = self.parse_key(key)
        return self.book_order.index(book_code), chapter, start, end
