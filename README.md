# Mini Search Engine

A dependency-free BM25 search engine with a thread-safe inverted index, JSON persistence, and a concurrent HTTP API.

## Why this project

Search connects algorithms with backend engineering. This project implements tokenization, inverted postings, BM25 ranking, document replacement and removal, persistence, and a small production-style service boundary without relying on a search library.

## Features

- BM25 relevance ranking
- Thread-safe inverted index
- Document metadata and deterministic results
- Add, replace, remove, and search operations
- JSON persistence
- Concurrent standard-library HTTP server
- Health, document, search, and deletion endpoints
- Unit and HTTP integration tests

## Run the service

```bash
PYTHONPATH=src python3 -m mini_search.server \  --data examples/documents.json --port 8000
```

Search:

```bash
curl 'http://127.0.0.1:8000/search?q=python+concurrency&limit=5'
```

Index a document:

```bash
curl -X POST http://127.0.0.1:8000/documents \  -H 'Content-Type: application/json' \  -d '{"id":"doc-42","text":"Building reliable backend systems"}'
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Ranking model

For each query term, BM25 combines inverse document frequency, term frequency, and length normalization. The index uses a postings map from each term to its documents, so queries only score candidates that contain at least one query term.
