import random
import unittest
from atlas_search.structures import DynamicArray, LinkedList, Stack, Queue, HashMap, stable_hash, AVLTree, MinHeap, Trie, DisjointSet


class StructureTests(unittest.TestCase):
    def test_dynamic_array_growth_insert_delete(self):
        array = DynamicArray(range(70))
        array.insert(0, -1); array.insert(36, 99); array.insert(len(array), 100)
        self.assertEqual(array.pop(36), 99)
        self.assertEqual(array.pop(), 100)
        self.assertEqual(list(array), [-1] + list(range(70)))
        with self.assertRaises(IndexError):
            array[99]

    def test_linked_list_head_tail_singleton(self):
        links = LinkedList([1, 2, 3])
        self.assertTrue(links.remove(1)); self.assertTrue(links.remove(3))
        self.assertEqual(links.popleft(), 2)
        self.assertIsNone(links.head); self.assertIsNone(links.tail)
        self.assertFalse(links.remove(1))
        links.append(4); self.assertEqual(list(links), [4])

    def test_stack_lifo_and_queue_fifo(self):
        stack, queue = Stack(), Queue()
        for i in range(10):
            stack.push(i); queue.push(i)
        self.assertEqual([stack.pop() for _ in range(10)], list(reversed(range(10))))
        self.assertEqual([queue.pop() for _ in range(10)], list(range(10)))
        with self.assertRaises(IndexError):
            queue.pop()
        with self.assertRaises(IndexError):
            stack.pop()

    def test_hash_collisions_rehash_update_none_delete(self):
        table = HashMap(32)
        groups = {}
        collision = None
        for i in range(100):
            slot = stable_hash(str(i)) % 32
            if slot in groups:
                collision = (groups[slot], str(i)); break
            groups[slot] = str(i)
        a, b = collision
        table[a] = 1; table[b] = None
        self.assertIn(b, table); self.assertIsNone(table[b])
        table[a] = 2; self.assertEqual(len(table), 2)
        for i in range(100):
            table[f"term{i}"] = i
        for i in range(100):
            self.assertEqual(table[f"term{i}"], i)
        del table[a]; self.assertEqual(table[b], None)
        with self.assertRaises(KeyError):
            table[a]

    def test_avl_all_rotations(self):
        for values in ([3, 2, 1], [1, 2, 3], [3, 1, 2], [1, 3, 2]):
            tree = AVLTree()
            for v in values:
                tree.put(v, v * 10); tree.validate()
            self.assertEqual(tree.root.key, 2)
            self.assertEqual(list(tree.range(2, 3)), [(2, 20), (3, 30)])

    def test_avl_delete_and_random_invariants(self):
        tree, values = AVLTree(), list(range(200))
        rng = random.Random(408); rng.shuffle(values)
        for v in values:
            tree.put(v, v); tree.validate()
        tree.put(9, 999)
        self.assertEqual(list(tree.range(9, 9)), [(9, 999)])
        rng.shuffle(values)
        for v in values:
            tree.delete(v); tree.validate()
        self.assertIsNone(tree.root)
        with self.assertRaises(KeyError):
            tree.delete(4)

    def test_heap_order_and_empty(self):
        values = [3, -1, 8, 3, 0]
        heap = MinHeap(values)
        self.assertEqual([heap.pop() for _ in values], sorted(values))
        with self.assertRaises(IndexError):
            heap.pop()

    def test_trie_prefix_removal_shared_path(self):
        trie = Trie()
        for word in ("tree", "trie", "trip", "树", "树形"):
            trie.add(word)
        self.assertEqual(trie.prefix("tri"), ["trie", "trip"])
        self.assertTrue(trie.remove("trie")); self.assertFalse(trie.remove("missing"))
        self.assertEqual(trie.prefix("tri"), ["trip"])
        trie.remove("树"); self.assertEqual(trie.prefix("树"), ["树形"])
        self.assertEqual(trie.prefix("", 0), [])

    def test_disjoint_set_path_compression(self):
        groups = DisjointSet(range(5))
        self.assertTrue(groups.union(0, 1)); self.assertTrue(groups.union(1, 2))
        self.assertFalse(groups.union(0, 2))
        self.assertEqual(groups.find(0), groups.find(2))
        self.assertNotEqual(groups.find(0), groups.find(4))
