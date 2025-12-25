from abc import ABC, abstractmethod
from pathlib import Path
import json

import httpx
from pydantic import BaseModel, ConfigDict, Field


class Book(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    author_names: list[str] = Field(default_factory=list, alias="author_name")
    first_publish_year: int | None = None
    publisher: list[str] = Field(default_factory=list)
    language: list[str] = Field(default_factory=list)
    number_of_pages: int | None = Field(default=None, alias="number_of_pages_median")


class OpenLibraryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    num_found: int = Field(alias="numFound")
    docs: list[Book]


class BookFormatter(ABC):
    @abstractmethod
    def format(self, books: list[Book]) -> str:
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        pass

    def write_to_file(self, books: list[Book], filepath: Path) -> None:
        content = self.format(books)
        filepath.write_text(content, encoding="utf-8")


class JsonFormatter(BookFormatter):
    def __init__(self, indent: int = 2):
        self.indent = indent

    def format(self, books: list[Book]) -> str:
        books_data = [book.model_dump(by_alias=False) for book in books]
        return json.dumps(books_data, indent=self.indent, ensure_ascii=False)

    def get_file_extension(self) -> str:
        return ".json"


class BookFetcher:
    BASE_URL = "https://openlibrary.org/search.json"

    def __init__(self, formatter: BookFormatter | None = None):
        self.formatter = formatter or JsonFormatter()

    def fetch_books(self, query: str, limit: int = 100) -> list[Book]:
        params = {"q": query, "limit": limit}

        with httpx.Client(timeout=30.0) as client:
            response = client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        parsed = OpenLibraryResponse.model_validate(data)
        return parsed.docs

    def filter_books(
        self,
        books: list[Book],
        title_contains: str | None = None,
        min_year: int | None = None,
    ) -> list[Book]:
        result = books

        if title_contains:
            keyword = title_contains.lower()
            result = [b for b in result if keyword in b.title.lower()]

        if min_year is not None:
            result = [
                b for b in result
                if b.first_publish_year is not None and b.first_publish_year >= min_year
            ]

        return result

    def save_books(self, books: list[Book], output_path: Path) -> None:
        self.formatter.write_to_file(books, output_path)


def main():
    fetcher = BookFetcher(formatter=JsonFormatter(indent=2))

    print("Fetching books from Open Library API...")
    books = fetcher.fetch_books(query="python programming", limit=50)
    print(f"Found {len(books)} books")

    filtered = fetcher.filter_books(
        books,
        title_contains="python",
        min_year=2010,
    )
    print(f"After filtering: {len(filtered)} books")

    output_file = Path("filtered_books.json")
    fetcher.save_books(filtered, output_file)
    print(f"Results written to {output_file}")


if __name__ == "__main__":
    main()
