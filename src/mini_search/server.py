from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .index import InvertedIndex, results_as_dicts


def make_handler(index: InvertedIndex, data_path: Path | None = None):
    class SearchHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._json(HTTPStatus.OK, {"status": "ok", **index.stats()})
                return
            if parsed.path == "/search":
                parameters = parse_qs(parsed.query)
                query = parameters.get("q", [""])[0]
                try:
                    limit = int(parameters.get("limit", ["10"])[0])
                    results = index.search(query, limit=limit)
                except ValueError as exc:
                    self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return
                self._json(
                    HTTPStatus.OK,
                    {"query": query, "results": results_as_dicts(results)},
                )
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/documents":
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            try:
                payload = self._read_json()
                index.add_document(
                    str(payload["id"]),
                    str(payload["text"]),
                    payload.get("metadata"),
                )
                if data_path is not None:
                    index.save(data_path)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            self._json(HTTPStatus.CREATED, {"id": str(payload["id"])})

        def do_DELETE(self) -> None:
            prefix = "/documents/"
            parsed = urlparse(self.path)
            if not parsed.path.startswith(prefix):
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            document_id = unquote(parsed.path[len(prefix) :])
            if not index.remove_document(document_id):
                self._json(HTTPStatus.NOT_FOUND, {"error": "document not found"})
                return
            if data_path is not None:
                index.save(data_path)
            self._json(HTTPStatus.OK, {"deleted": document_id})

        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _read_json(self) -> dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(content_length))

        def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return SearchHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the mini BM25 search service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--data", type=Path, default=Path("documents.json"))
    args = parser.parse_args()

    index = InvertedIndex.load(args.data) if args.data.exists() else InvertedIndex()
    server = ThreadingHTTPServer(
        (args.host, args.port), make_handler(index, args.data)
    )
    print(f"Search service listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

