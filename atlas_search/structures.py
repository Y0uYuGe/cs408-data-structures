"""Handwritten structures used by the engine; Python storage is the backing memory."""
from dataclasses import dataclass


class DynamicArray:
    def __init__(self, values=()):
        self._data = [None] * 4
        self._size = 0
        for value in values:
            self.append(value)

    def append(self, value):
        if self._size == len(self._data):
            memory = [None] * (2 * len(self._data))
            for i in range(self._size):
                memory[i] = self._data[i]
            self._data = memory
        self._data[self._size] = value
        self._size += 1

    def insert(self, index, value):
        if not 0 <= index <= self._size:
            raise IndexError(index)
        self.append(None)
        for i in range(self._size - 1, index, -1):
            self._data[i] = self._data[i - 1]
        self._data[index] = value

    def pop(self, index=-1):
        if index < 0:
            index += self._size
        value = self[index]
        for i in range(index, self._size - 1):
            self._data[i] = self._data[i + 1]
        self._size -= 1
        self._data[self._size] = None
        return value

    def __getitem__(self, index):
        if index < 0:
            index += self._size
        if not 0 <= index < self._size:
            raise IndexError(index)
        return self._data[index]

    def __setitem__(self, index, value):
        if not 0 <= index < self._size:
            raise IndexError(index)
        self._data[index] = value

    def __len__(self):
        return self._size

    def __iter__(self):
        for i in range(self._size):
            yield self._data[i]


@dataclass
class Link:
    value: object
    next: object = None


class LinkedList:
    def __init__(self, values=()):
        self.head = self.tail = None
        self.size = 0
        for value in values:
            self.append(value)

    def append(self, value):
        node = Link(value)
        if self.tail is None:
            self.head = node
        else:
            self.tail.next = node
        self.tail = node
        self.size += 1

    def remove(self, value):
        previous, node = None, self.head
        while node:
            if node.value == value:
                if previous is None:
                    self.head = node.next
                else:
                    previous.next = node.next
                if node is self.tail:
                    self.tail = previous
                self.size -= 1
                return True
            previous, node = node, node.next
        return False

    def popleft(self):
        if self.head is None:
            raise IndexError("empty linked list")
        value = self.head.value
        self.head = self.head.next
        self.size -= 1
        if self.head is None:
            self.tail = None
        return value

    def __len__(self):
        return self.size

    def __iter__(self):
        node = self.head
        while node:
            yield node.value
            node = node.next


class Stack:
    def __init__(self):
        self.values = DynamicArray()

    def push(self, value):
        self.values.append(value)

    def pop(self):
        return self.values.pop()

    def peek(self):
        return self.values[-1]

    def __len__(self):
        return len(self.values)


class Queue:
    def __init__(self):
        self.values = LinkedList()

    def push(self, value):
        self.values.append(value)

    def pop(self):
        return self.values.popleft()

    def __len__(self):
        return len(self.values)


def stable_hash(key):
    value = 2166136261
    for byte in str(key).encode("utf-8"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value


class HashMap:
    """Separate chaining, grow at load > .75. None is a valid stored value."""
    def __init__(self, capacity=8):
        self.buckets = [LinkedList() for _ in range(max(2, capacity))]
        self.size = 0

    def get(self, key, default=None):
        for pair in self.buckets[stable_hash(key) % len(self.buckets)]:
            if pair[0] == key:
                return pair[1]
        return default

    def __contains__(self, key):
        marker = object()
        return self.get(key, marker) is not marker

    def __getitem__(self, key):
        marker = object()
        value = self.get(key, marker)
        if value is marker:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        bucket = self.buckets[stable_hash(key) % len(self.buckets)]
        for pair in bucket:
            if pair[0] == key:
                pair[1] = value
                return
        bucket.append([key, value])
        self.size += 1
        if self.size > len(self.buckets) * .75:
            old = list(self.items())
            self.buckets = [LinkedList() for _ in range(2 * len(self.buckets))]
            self.size = 0
            for k, v in old:
                self[k] = v

    def __delitem__(self, key):
        bucket = self.buckets[stable_hash(key) % len(self.buckets)]
        for pair in bucket:
            if pair[0] == key:
                bucket.remove(pair)
                self.size -= 1
                return
        raise KeyError(key)

    def items(self):
        for bucket in self.buckets:
            for key, value in bucket:
                yield key, value

    def __iter__(self):
        for key, _ in self.items():
            yield key

    def __len__(self):
        return self.size


@dataclass
class AVLNode:
    key: object
    value: object
    left: object = None
    right: object = None
    height: int = 1


class AVLTree:
    def __init__(self):
        self.root = None

    @staticmethod
    def height(node):
        return node.height if node else 0

    def _refresh(self, node):
        node.height = 1 + max(self.height(node.left), self.height(node.right))

    def _rotate(self, node, left):
        pivot = node.right if left else node.left
        if left:
            node.right, pivot.left = pivot.left, node
        else:
            node.left, pivot.right = pivot.right, node
        self._refresh(node)
        self._refresh(pivot)
        return pivot

    def _balance(self, node):
        self._refresh(node)
        delta = self.height(node.left) - self.height(node.right)
        if delta > 1:
            if self.height(node.left.left) < self.height(node.left.right):
                node.left = self._rotate(node.left, True)
            return self._rotate(node, False)
        if delta < -1:
            if self.height(node.right.right) < self.height(node.right.left):
                node.right = self._rotate(node.right, False)
            return self._rotate(node, True)
        return node

    def put(self, key, value):
        def insert(node):
            if node is None:
                return AVLNode(key, value)
            if key < node.key:
                node.left = insert(node.left)
            elif key > node.key:
                node.right = insert(node.right)
            else:
                node.value = value
                return node
            return self._balance(node)
        self.root = insert(self.root)

    def delete(self, key):
        def remove(node, target):
            if node is None:
                raise KeyError(target)
            if target < node.key:
                node.left = remove(node.left, target)
            elif target > node.key:
                node.right = remove(node.right, target)
            else:
                if node.left is None:
                    return node.right
                if node.right is None:
                    return node.left
                successor = node.right
                while successor.left:
                    successor = successor.left
                node.key, node.value = successor.key, successor.value
                node.right = remove(node.right, successor.key)
            return self._balance(node)
        self.root = remove(self.root, key)

    def range(self, low, high):
        def walk(node):
            if not node:
                return
            if node.key > low:
                yield from walk(node.left)
            if low <= node.key <= high:
                yield node.key, node.value
            if node.key < high:
                yield from walk(node.right)
        yield from walk(self.root)

    def validate(self):
        def visit(node, low=None, high=None):
            if node is None:
                return 0
            if (low is not None and node.key <= low) or (high is not None and node.key >= high):
                raise AssertionError("AVL key order")
            lh, rh = visit(node.left, low, node.key), visit(node.right, node.key, high)
            if abs(lh - rh) > 1 or node.height != 1 + max(lh, rh):
                raise AssertionError("AVL height/balance")
            return node.height
        visit(self.root)
        return True


class MinHeap:
    def __init__(self, values=(), key=lambda x: x):
        self.data = DynamicArray()
        self.key = key
        for value in values:
            self.push(value)

    def push(self, value):
        self.data.append(value)
        i = len(self.data) - 1
        while i > 0:
            p = (i - 1) // 2
            if self.key(self.data[p]) <= self.key(self.data[i]):
                break
            self.data[p], self.data[i] = self.data[i], self.data[p]
            i = p

    def pop(self):
        if not self.data:
            raise IndexError("empty heap")
        value, last = self.data[0], self.data.pop()
        if self.data:
            self.data[0] = last
            i = 0
            while 2 * i + 1 < len(self.data):
                child = 2 * i + 1
                if child + 1 < len(self.data) and self.key(self.data[child + 1]) < self.key(self.data[child]):
                    child += 1
                if self.key(self.data[i]) <= self.key(self.data[child]):
                    break
                self.data[i], self.data[child] = self.data[child], self.data[i]
                i = child
        return value

    def __len__(self):
        return len(self.data)


class Trie:
    def __init__(self):
        self.root = {"children": HashMap(), "end": False}

    def add(self, word):
        node = self.root
        for char in word:
            child = node["children"].get(char)
            if child is None:
                child = {"children": HashMap(), "end": False}
                node["children"][char] = child
            node = child
        node["end"] = True

    def remove(self, word):
        node, path = self.root, []
        for char in word:
            child = node["children"].get(char)
            if child is None:
                return False
            path.append((node, char)); node = child
        if not node["end"]:
            return False
        node["end"] = False
        for parent, char in reversed(path):
            child = parent["children"][char]
            if child["end"] or len(child["children"]):
                break
            del parent["children"][char]
        return True

    def prefix(self, prefix, limit=20):
        node = self.root
        for char in prefix:
            node = node["children"].get(char)
            if node is None:
                return []
        result = []
        stack = Stack()
        stack.push((prefix, node))
        while stack and len(result) < limit:
            word, current = stack.pop()
            if current["end"]:
                result.append(word)
            # Order is specified by the API; sorting children is presentation only.
            children = sorted(current["children"].items(), reverse=True)
            for char, child in children:
                stack.push((word + char, child))
        return result


class DisjointSet:
    def __init__(self, values):
        self.parent = {value: value for value in values}
        self.rank = {value: 0 for value in values}

    def find(self, value):
        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])
        return self.parent[value]

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a == b:
            return False
        if self.rank[a] < self.rank[b]:
            a, b = b, a
        self.parent[b] = a
        if self.rank[a] == self.rank[b]:
            self.rank[a] += 1
        return True
