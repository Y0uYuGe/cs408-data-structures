import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from atlas_search.engine import Engine, tokenize
from atlas_search import storage


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "db"
        self.engine = Engine(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self):
        a = self.engine.add("Trees", "AVL tree 数据结构")
        b = self.engine.add("Graph", "tree graph 最短路径", links=[a])
        c = self.engine.add("Sort", "sort tree tree", links=[b])
        return a, b, c

    def test_tokenize_cjk_latin_deterministic(self):
        self.assertEqual(tokenize("AVL 数据结构!"), ["avl", "数", "据", "结", "构", "数据", "据结", "结构"])

    def test_search_boolean_phrase_ranking(self):
        a, b, c = self.fixture()
        self.assertEqual([r["id"] for r in self.engine.search("tree")], [c, a, b])
        self.assertEqual([r["id"] for r in self.engine.search("tree AND NOT graph")], [c, a])
        self.assertEqual([r["id"] for r in self.engine.search("graph OR avl")], [b, a])
        self.assertEqual([r["id"] for r in self.engine.search('"数据结构"')], [a])
        self.assertEqual(self.engine.search("unknown"), [])
        self.assertEqual(self.engine.search("NOT unknown", 0), [])

    def test_update_delete_remove_every_index_restart(self):
        a, b, c = self.fixture()
        self.engine.update(a, title="New", text="replacement")
        self.assertEqual(self.engine.search("avl"), [])
        self.assertEqual(self.engine.trie.prefix("av"), [])
        self.assertTrue(self.engine.check()["ok"])
        self.engine.delete(b)
        restarted = Engine(self.db)
        self.assertEqual(restarted.search("graph"), [])
        self.assertEqual(restarted.documents[c]["links"], [])
        self.assertTrue(restarted.check()["ok"])
        with self.assertRaises(KeyError):
            restarted.delete(b)

    def test_array_and_linked_posting_backends(self):
        for backend in ("array", "linked"):
            self.engine.posting_backend = backend; self.engine.rebuild()
            a = self.engine.add("X", "alpha beta")
            b = self.engine.add("Y", "beta")
            self.engine.update(a, text="beta gamma")
            self.assertEqual([r["id"] for r in self.engine.search("beta")], [a, b])
            self.engine.delete(a); self.engine.delete(b)
            self.assertTrue(Engine(self.db).check()["ok"])

    def test_eight_sorts_actual_search(self):
        self.fixture()
        from atlas_search.algorithms import SORTS
        reference = self.engine.search("tree", sort="merge")
        for name in SORTS:
            self.assertEqual(self.engine.search("tree", sort=name), reference)

    def test_range_boundary_and_binary_lookup(self):
        a = self.engine.add("A", "123")
        b = self.engine.add("B", "12345")
        self.assertEqual([d["id"] for d in self.engine.range(3, 3)], [a])
        self.assertEqual([d["id"] for d in self.engine.range(3, 5)], [a, b])
        self.assertEqual(self.engine.locate_id(b), self.engine.documents[b])
        self.assertIsNone(self.engine.locate_id(999))
        with self.assertRaises(ValueError):
            self.engine.range(5, 3)

    def test_directory_upsert_and_decoding_failure_atomic(self):
        corpus = self.root / "corpus"; corpus.mkdir()
        file = corpus / "one.md"; file.write_text("trees", encoding="utf-8")
        self.assertEqual(self.engine.index_directory(corpus), {"added": 1, "updated": 0})
        file.write_text("graphs", encoding="utf-8")
        self.assertEqual(self.engine.index_directory(corpus), {"added": 0, "updated": 1})
        self.assertEqual(self.engine.search("trees"), [])
        (corpus / "bad.txt").write_bytes(b"\xff")
        with self.assertRaises(UnicodeError):
            self.engine.index_directory(corpus)
        self.assertEqual(len(Engine(self.db).documents), 1)

    def test_graph_on_real_document_relationships(self):
        a, b, c = self.fixture()
        self.assertEqual(self.engine.graph().path(a, c)["path"], [a, c])
        self.assertEqual(self.engine.graph(True).path(c, a)["path"], [c, b, a])
        self.assertEqual(self.engine.graph(True).topological(), [c, b, a])
        self.assertGreater(self.engine.graph(True).critical_path()["duration"], 0)

    def test_huffman_archive_restore_and_corruption(self):
        self.fixture()
        archive = self.root / "backup.atlas.json"
        self.engine.export_archive(archive)
        restored = Engine(self.root / "restored")
        restored.import_archive(archive)
        self.assertEqual(restored.search("tree"), self.engine.search("tree"))
        self.assertTrue(restored.check()["ok"])
        with self.assertRaises(ValueError):
            restored.import_archive(archive)
        restored.import_archive(archive, replace=True)
        bad = json.loads(archive.read_text(encoding="utf-8")); bad["sha256"] = "bad"
        archive.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(ValueError):
            restored.import_archive(archive, replace=True)

    def test_snapshot_corruption_recovery_and_repair(self):
        self.fixture()
        (self.db / "snapshot.json").write_text("{broken", encoding="utf-8")
        recovered = Engine(self.db)
        self.assertTrue(recovered.recovered)
        self.assertEqual(len(recovered.documents), 3)
        recovered.commit()
        self.assertFalse(Engine(self.db).recovered)
        (self.db / "snapshot.json").write_text("bad", encoding="utf-8")
        (self.db / "snapshot.backup.json").write_text("bad", encoding="utf-8")
        with self.assertRaises(ValueError):
            Engine(self.db)

    def test_checksum_and_schema_validation(self):
        self.fixture()
        payload = self.engine.payload()
        payload["documents"][0]["links"] = [999]
        with self.assertRaises(ValueError):
            storage.validate_payload(payload)
        env = storage.envelope({"x": 1}); env["payload"]["x"] = 2
        with self.assertRaises(ValueError):
            storage.verify(env)

    def test_check_detects_damaged_index(self):
        a, _, _ = self.fixture()
        self.engine.postings["avl"].append(999)
        with self.assertRaises(AssertionError):
            self.engine.check()

    def test_check_detects_frequency_and_range_corruption(self):
        a, _, _ = self.fixture()
        self.engine.frequencies[a]["avl"] = 999
        with self.assertRaises(AssertionError):
            self.engine.check()
        self.engine.rebuild()
        self.engine.sizes.delete((len(self.engine.documents[a]["text"]), a))
        self.engine.sizes.put((999, a), a)
        with self.assertRaises(AssertionError):
            self.engine.check()

    def test_lock_exclusion_and_stale_owner_recovery(self):
        with storage.database_lock(self.db):
            with self.assertRaises(RuntimeError):
                with storage.database_lock(self.db, timeout=.05):
                    pass
        (self.db / "writer.lock").write_text('{"pid": 99999999}', encoding="utf-8")
        with storage.database_lock(self.db):
            self.assertTrue((self.db / "writer.lock").exists())
        self.assertFalse((self.db / "writer.lock").exists())

    def test_select_newest_valid_snapshot_and_ignore_temporary(self):
        self.fixture()
        old = self.engine.payload()
        old["revision"] = 0
        (self.db / "snapshot.json").write_bytes(storage.canonical(storage.envelope(old)))
        (self.db / "snapshot.json.tmp").write_text("uncommitted", encoding="utf-8")
        restarted = Engine(self.db)
        self.assertEqual(restarted.revision, self.engine.revision)
        self.assertTrue(restarted.recovered)
        self.assertEqual(len(restarted.documents), 3)

    def test_partial_commit_new_primary_survives(self):
        self.engine.add("A", "old")
        original = storage.atomic_write
        def fail_backup(path, data):
            if Path(path).name == "snapshot.backup.json":
                raise OSError("injected backup failure")
            original(path, data)
        with patch("atlas_search.storage.atomic_write", side_effect=fail_backup):
            with self.assertRaises(OSError):
                self.engine.add("B", "new")
        restarted = Engine(self.db)
        self.assertEqual(restarted.search("new")[0]["id"], 2)
        self.assertEqual(restarted.revision, 2)
