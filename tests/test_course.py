import ast
import json
from pathlib import Path
import unittest
from atlas_search.assessment import questions, assess

ROOT = Path(__file__).resolve().parents[1]


class CourseTests(unittest.TestCase):
    def test_topic_map_paths_symbols_and_tests(self):
        mapping = json.loads((ROOT / "topics.json").read_text(encoding="utf-8"))
        topics = mapping["topics"]
        self.assertGreaterEqual(len(topics), 40)
        self.assertEqual(len({t["id"] for t in topics}), len(topics))
        for topic in topics:
            with self.subTest(topic=topic["id"]):
                self.assertIn(topic["status"], ("implemented", "theory"))
                self.assertIn(topic["level"], range(1, 7))
                self.assertTrue(topic["notes"])
                self.assertTrue(topic["docs"]); self.assertTrue(topic["tests"])
                if topic["status"] == "implemented":
                    self.assertTrue(topic["code"])
                for doc in topic["docs"]:
                    self.assertTrue((ROOT / doc).is_file(), doc)
                for code in topic["code"]:
                    file = ROOT / code["path"]
                    self.assertTrue(file.is_file(), code["path"])
                    if file.suffix == ".py":
                        nodes = ast.walk(ast.parse(file.read_text(encoding="utf-8")))
                        self.assertIn(code["symbol"].split(".")[-1], {n.name for n in nodes if isinstance(n, (ast.FunctionDef, ast.ClassDef))})
                for reference in topic["tests"]:
                    path, qualified = reference.split("::")
                    class_name, method = qualified.split(".")
                    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
                    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
                    self.assertIn(method, {n.name for n in cls.body if isinstance(n, ast.FunctionDef)})

    def test_original_question_bank_and_diagnostic(self):
        bank = questions()
        self.assertGreaterEqual(len(bank), 30)
        self.assertEqual(len({q["id"] for q in bank}), len(bank))
        topic_ids = {t["id"] for t in json.loads((ROOT / "topics.json").read_text(encoding="utf-8"))["topics"]}
        for q in bank:
            self.assertEqual(q["origin"], "original")
            self.assertIn(q["topic"], topic_ids)
            self.assertTrue(q["answers"]); self.assertTrue(q["explanation"])
            self.assertTrue((ROOT / q["review"]).is_file())
            self.assertTrue(any("\u3400" <= c <= "\u9fff" for c in q["prompt"]))
        all_correct = {q["id"]: q["answers"][0] for q in bank}
        result = assess(all_correct)
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["band"], "高分巩固")
        self.assertEqual(result["review"], [])
        self.assertEqual(assess({})["band"], "基础重建")
        with self.assertRaises(ValueError):
            assess({"Q999": "A"})

    def test_six_levels_and_substantive_course(self):
        for level in range(1, 7):
            self.assertEqual(len(questions(level)), 8)
            answers = {q["id"]: q["answers"][0] for q in questions(level)}
            self.assertEqual(assess(answers, level)["score"], 100)
        chapters = sorted((ROOT / "docs").glob("[0-9][0-9]-*.md"))
        self.assertGreaterEqual(len(chapters), 11)
        for chapter in chapters:
            text = chapter.read_text(encoding="utf-8")
            self.assertGreater(len(text), 600, chapter.name)
            self.assertIn("答案", text, chapter.name)
            self.assertIn("代码", text, chapter.name)

    def test_all_diagnostic_bands(self):
        bank = questions()
        for count, expected in ((0, "基础重建"), (30, "专项补弱"), (40, "综合迁移"), (48, "高分巩固")):
            result = assess({q["id"]: q["answers"][0] for q in bank[:count]})
            self.assertEqual(result["band"], expected)
