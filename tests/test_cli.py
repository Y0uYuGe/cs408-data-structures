import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "db"

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, success=True, db=None):
        result = subprocess.run([sys.executable, "-m", "atlas_search", "--db", str(db or self.db), *args],
                                cwd=ROOT, encoding="utf-8", capture_output=True,
                                env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=15)
        self.assertEqual(result.returncode, 0 if success else 2, result.stdout + result.stderr)
        return json.loads(result.stdout if success else result.stderr)

    def test_cross_process_add_search_update_delete(self):
        self.run_cli("init", "--posting", "linked")
        self.assertEqual(self.run_cli("add", "--title", "中文文档", "--text", "数据结构 AVL tree")["id"], 1)
        self.assertEqual(self.run_cli("search", "数据结构")[0]["id"], 1)
        self.run_cli("update", "1", "--text", "new content")
        self.assertEqual(self.run_cli("search", "tree"), [])
        self.run_cli("delete", "1")
        self.assertEqual(self.run_cli("list"), [])
        self.assertTrue(self.run_cli("check")["ok"])

    def test_all_public_commands_real_processes(self):
        self.run_cli("init")
        self.run_cli("add", "--title", "A", "--text", "alpha tree")
        self.run_cli("add", "--title", "B", "--text", "beta tree", "--links", "1")
        self.assertEqual(self.run_cli("suggest", "tr"), ["tree"])
        self.assertEqual(len(self.run_cli("range", "0", "100")), 2)
        self.assertEqual(self.run_cli("show", "1", "--lookup", "binary")["title"], "A")
        for algorithm in ("bfs", "dijkstra"):
            self.assertEqual(self.run_cli("path", "1", "2", "--algorithm", algorithm)["path"], [1, 2])
        for algorithm in ("floyd", "prim", "kruskal"):
            self.run_cli("graph", algorithm)
        self.run_cli("graph", "dfs", "--source", "1")
        self.assertEqual(self.run_cli("graph", "topological", "--directed"), [2, 1])
        self.run_cli("graph", "critical", "--directed")
        archive = Path(self.temp.name) / "archive.json"
        self.run_cli("export", str(archive))
        self.run_cli("import", str(archive), db=Path(self.temp.name) / "other")
        self.run_cli("repair")
        self.assertIn("avl", self.run_cli("tokenize", "AVL"))
        self.assertGreaterEqual(len(self.run_cli("practice")), 30)
        self.assertIn("answers", self.run_cli("practice", "--reveal")[0])
        answers = Path(self.temp.name) / "answers.json"
        answers.write_text('{"Q01":"B"}', encoding="utf-8")
        self.assertIn("band", self.run_cli("assess", "--answers", str(answers)))
        corpus = Path(self.temp.name) / "corpus"; corpus.mkdir()
        (corpus / "c.md").write_text("course", encoding="utf-8")
        self.assertEqual(self.run_cli("index", str(corpus))["added"], 1)

    def test_cli_errors_are_structured(self):
        self.assertIn("error", self.run_cli("search", "a AND", success=False))
        self.assertIn("error", self.run_cli("delete", "999", success=False))
        self.assertIn("error", self.run_cli("suggest", "a", "--limit", "-1", success=False))

    def test_cli_corruption_recovers_latest_documents(self):
        self.run_cli("add", "--title", "A", "--text", "persisted")
        (self.db / "snapshot.json").write_text("invalid", encoding="utf-8")
        self.assertEqual(self.run_cli("search", "persisted")[0]["id"], 1)
        self.assertTrue(self.run_cli("check")["recovered_from_backup"])
        self.assertFalse(self.run_cli("repair")["recovered_from_backup"])

    def test_concurrent_writers_do_not_lose_updates(self):
        processes = []
        for i in range(6):
            processes.append(subprocess.Popen([sys.executable, "-m", "atlas_search", "--db", str(self.db),
                             "add", "--title", f"doc{i}", "--text", "shared"], cwd=ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8",
                             env={**os.environ, "PYTHONIOENCODING": "utf-8"}))
        ids = []
        for process in processes:
            out, err = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, err)
            ids.append(json.loads(out)["id"])
        self.assertEqual(sorted(ids), list(range(1, 7)))
        self.assertEqual(len(self.run_cli("search", "shared")), 6)
        self.assertTrue(self.run_cli("check")["ok"])
