from __future__ import annotations

import json
import math
import re
import threading
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


TOKEN_PATTERN = re.compile(r"[\w]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.casefold())


@dataclass(frozen=True, slots=True)
class SearchResult:
    document_id: str
    score: float
    text: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class _Document:
    text: str
    metadata: dict[str, Any]
    length: int


class InvertedIndex:
    """Thread-safe in-memory BM25 index with JSON persistence."""

    def __init__(self, *, k1: float = 1.5, b: float = 0.75) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be positive")
        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1")
        self.k1 = k1
        self.b = b
        self._documents: dict[str, _Document] = {}
        self._postings: dict[str, dict[str, int]] = defaultdict(dict)
        self._document_terms: dict[str, Counter[str]] = {}
        self._total_tokens = 0
        self._lock = threading.RLock()

    def add_document(
        self,
        document_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not document_id:
            raise ValueError("document_id cannot be empty")
        terms = Counter(tokenize(text))
        with self._lock:
            self._remove_unlocked(document_id)
            document = _Document(text, dict(metadata or {}), sum(terms.values()))
            self._documents[document_id] = document
            self._document_terms[document_id] = terms
            self._total_tokens += document.length
            for term, frequency in terms.items():
                self._postings[term][document_id] = frequency

    def add_documents(self, documents: Iterable[dict[str, Any]]) -> None:
        for document in documents:
            self.add_document(
                str(document["id"]),
                str(document["text"]),
                document.get("metadata"),
            )

    def remove_document(self, document_id: str) -> bool:
        with self._lock:
            return self._remove_unlocked(document_id)

    def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        if limit < 1:
            raise ValueError("limit must be positive")
        query_terms = Counter(tokenize(query))
        if not query_terms:
            return []

        with self._lock:
            document_count = len(self._documents)
            if document_count == 0:
                return []
            average_length = self._total_tokens / document_count or 1.0
            scores: dict[str, float] = defaultdict(float)

            for term, query_frequency in query_terms.items():
                posting = self._postings.get(term)
                if not posting:
                    continue
                document_frequency = len(posting)
                inverse_document_frequency = math.log(
                    1
                    + (document_count - document_frequency + 0.5)
                    / (document_frequency + 0.5)
                )
                for document_id, term_frequency in posting.items():
                    document_length = self._documents[document_id].length
                    normalization = self.k1 * (
                        1 - self.b + self.b * document_length / average_length
                    )
                    scores[document_id] += query_frequency * (
                        inverse_document_frequency
                        * term_frequency
                        * (self.k1 + 1)
                        / (term_frequency + normalization)
                    )

            ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
            return [
                SearchResult(
                    document_id=document_id,
                    score=round(score, 6),
                    text=self._documents[document_id].text,
                    metadata=dict(self._documents[document_id].metadata),
                )
                for document_id, score in ranked[:limit]
            ]

    def save(self, path: str | Path) -> None:
        with self._lock:
            data = {
                "k1": self.k1,
                "b": self.b,
                "documents": [
                    {
                        "id": document_id,
                        "text": document.text,
                        "metadata": document.metadata,
                    }
                    for document_id, document in self._documents.items()
                ],
            }
        Path(path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: str | Path) -> InvertedIndex:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        index = cls(k1=float(data["k1"]), b=float(data["b"]))
        index.add_documents(data["documents"])
        return index

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "documents": len(self._documents),
                "terms": len(self._postings),
                "tokens": self._total_tokens,
            }

    def _remove_unlocked(self, document_id: str) -> bool:
        document = self._documents.pop(document_id, None)
        terms = self._document_terms.pop(document_id, None)
        if document is None or terms is None:
            return False
        self._total_tokens -= document.length
        for term in terms:
            posting = self._postings[term]
            posting.pop(document_id, None)
            if not posting:
                del self._postings[term]
        return True


def results_as_dicts(results: list[SearchResult]) -> list[dict[str, Any]]:
    return [asdict(result) for result in results]

