import random
import unittest
from atlas_search.algorithms import SORTS, sort_values, binary_search, kmp_table, kmp_find, huffman_encode, huffman_decode, Graph
from atlas_search.query import parse, combine


class AlgorithmTests(unittest.TestCase):
    def test_all_eight_sorts_and_boundary_inputs(self):
        rng = random.Random(408)
        cases = [[], [1], [2, 2, 2], list(range(50)), list(reversed(range(50))), [rng.randrange(-50, 50) for _ in range(100)]]
        for name in SORTS:
            for values in cases:
                with self.subTest(sort=name, n=len(values)):
                    original = list(values)
                    self.assertEqual(sort_values(values, name), sorted(values))
                    self.assertEqual(values, original)
        with self.assertRaises(ValueError):
            sort_values(["a"], "radix")

    def test_stable_sorts_preserve_equal_keys(self):
        values = [(2, "x"), (1, "a"), (1, "b"), (2, "y")]
        for algorithm in ("insertion", "bubble", "merge", "radix"):
            self.assertEqual(sort_values(values, algorithm, lambda p: p[0]), [(1, "a"), (1, "b"), (2, "x"), (2, "y")])

    def test_binary_lower_bound(self):
        values = [1, 3, 3, 9]
        self.assertEqual(binary_search(values, 3), 1)
        self.assertEqual(binary_search(values, 4), 3)
        self.assertEqual(binary_search([], 3), 0)
        self.assertEqual(binary_search(values, 10), 4)

    def test_kmp_table_overlap_empty_unicode(self):
        self.assertEqual(kmp_table("ababaca"), [0, 0, 1, 2, 3, 0, 1])
        for text, pattern in (("ababababaca", "ababaca"), ("数据结构原理", "结构"), ("aaa", "aaaa"), ("abc", "")):
            self.assertEqual(kmp_find(text, pattern), text.find(pattern))

    def test_huffman_roundtrip_empty_single_all_bytes(self):
        for raw in (b"", b"aaaa", bytes(range(256)), "数据结构 and trees".encode(), b"abracadabra" * 100):
            self.assertEqual(huffman_decode(huffman_encode(raw)), raw)

    def test_huffman_corruption_and_limit(self):
        data = huffman_encode(b"hello world")
        data["bits"] += 100
        with self.assertRaises(ValueError):
            huffman_decode(data)
        with self.assertRaises(ValueError):
            huffman_decode(huffman_encode(b"xxxx"), max_bytes=3)
        data = huffman_encode(b"aaaa"); data["data"] = "/w=="
        with self.assertRaises(ValueError):
            huffman_decode(data)

    def graph(self):
        graph = Graph(range(5))
        for a, b, w in ((0, 1, 7), (0, 2, 1), (2, 1, 1), (1, 3, 1)):
            graph.add(a, b, w)
        return graph

    def test_bfs_dijkstra_dfs_unreachable(self):
        graph = self.graph()
        self.assertEqual(graph.path(0, 3, "bfs"), {"path": [0, 1, 3], "distance": 2})
        self.assertEqual(graph.path(0, 3, "dijkstra"), {"path": [0, 2, 1, 3], "distance": 3})
        self.assertEqual(graph.path(0, 4), {"path": [], "distance": None})
        self.assertEqual(graph.dfs(0), [0, 1, 2, 3])
        with self.assertRaises(ValueError):
            graph.add(0, 4, -1)

    def test_floyd_matches_dijkstra(self):
        graph = self.graph()
        distances = graph.floyd()
        for a in graph.adj:
            for b in graph.adj:
                expected = graph.path(a, b, "dijkstra")["distance"]
                self.assertEqual(distances[a][b], float("inf") if expected is None else expected)

    def test_prim_kruskal_disconnected_forest(self):
        graph = self.graph()
        self.assertEqual(graph.spanning_forest("prim")["weight"], 3)
        self.assertEqual(graph.spanning_forest("kruskal")["weight"], 3)
        self.assertEqual(len(graph.spanning_forest()["edges"]), 3)

    def test_topological_critical_path_cycle(self):
        graph = Graph(range(4))
        for a, b, w in ((0, 1, 2), (0, 2, 3), (1, 3, 4), (2, 3, 1)):
            graph.add(a, b, w, True)
        order = graph.topological()
        self.assertLess(order.index(0), order.index(1))
        self.assertEqual(graph.critical_path()["duration"], 6)
        self.assertEqual(graph.critical_path()["critical_edges"], [(0, 1, 2), (1, 3, 4)])
        with self.assertRaises(ValueError):
            graph.spanning_forest()
        graph.add(3, 0, 1, True)
        with self.assertRaises(ValueError):
            graph.topological()

    def test_query_precedence_and_implicit_and(self):
        self.assertEqual(parse("a OR b AND NOT c"), ["a", "b", "c", "NOT", "AND", "OR"])
        self.assertEqual(parse("(a OR b) c"), ["a", "b", "OR", "c", "AND"])
        self.assertEqual(parse("NOT NOT a"), ["a", "NOT", "NOT"])
        self.assertEqual(parse('"a b"'), ['"a b"'])

    def test_query_malformed(self):
        for query in ("", "a AND", "OR a", "(a", "a)", '"oops', "()", "a AND OR b"):
            with self.subTest(query=query), self.assertRaises(ValueError):
                parse(query)

    def test_posting_merge_boolean(self):
        a, b = [1, 3, 5], [2, 3, 5, 8]
        self.assertEqual(combine(a, b, "AND"), [3, 5])
        self.assertEqual(combine(a, b, "OR"), [1, 2, 3, 5, 8])
        self.assertEqual(combine(a, b, "DIFF"), [1])
