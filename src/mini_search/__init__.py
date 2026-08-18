"""Dependency-free BM25 search engine and HTTP service."""

from .index import InvertedIndex, SearchResult

__all__ = ["InvertedIndex", "SearchResult"]

