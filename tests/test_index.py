import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

from mini_search import InvertedIndex


class InvertedIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.index = InvertedIndex()
        self.index.add_document("python", "Python asyncio concurrency task queue")
        self.index.add_document("cpp", "C++ thread safe concurrent cache")
        self.index.add_document("business", "Technology product and business strategy")

    def test_ranks_relevant_documents(self) -> None:
        results = self.index.search("python concurrency")
        self.assertEqual(results[0].document_id, "python")
        self.assertGreater(results[0].score, 0)

    def test_replacing_document_updates_postings(self) -> None:
        self.index.add_document("python", "financial market research")
        self.assertEqual(self.index.search("asyncio"), [])
        self.assertEqual(self.index.search("market")[0].document_id, "python")

    def test_remove_document(self) -> None:
        self.assertTrue(self.index.remove_document("cpp"))
        self.assertFalse(self.index.remove_document("missing"))
        self.assertEqual(self.index.search("cache"), [])

    def test_persistence_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "index.json"
            self.index.save(path)
            restored = InvertedIndex.load(path)

        self.assertEqual(restored.stats(), self.index.stats())
        self.assertEqual(
            restored.search("business")[0].document_id,
            self.index.search("business")[0].document_id,
        )

    def test_metadata_is_copied(self) -> None:
        metadata = {"source": "portfolio"}
        self.index.add_document("meta", "search service", metadata)
        metadata["source"] = "changed"
        self.assertEqual(
            self.index.search("service")[0].metadata["source"], "portfolio"
        )


if __name__ == "__main__":
    unittest.main()

