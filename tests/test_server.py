import json
import pathlib
import sys
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

from mini_search import InvertedIndex
from mini_search.server import make_handler


class SearchServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = InvertedIndex()
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(cls.index)
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_document_and_search_endpoints(self) -> None:
        body = json.dumps(
            {"id": "doc-1", "text": "backend search service with Python"}
        ).encode()
        request = urllib.request.Request(
            self.base_url + "/documents",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status, 201)

        with urllib.request.urlopen(self.base_url + "/search?q=backend") as response:
            payload = json.load(response)
        self.assertEqual(payload["results"][0]["document_id"], "doc-1")

    def test_health_endpoint(self) -> None:
        with urllib.request.urlopen(self.base_url + "/health") as response:
            payload = json.load(response)
        self.assertEqual(payload["status"], "ok")


if __name__ == "__main__":
    unittest.main()

