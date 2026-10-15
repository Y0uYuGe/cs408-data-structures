"""Algorithms selected by real engine commands; no third-party dependencies."""
import base64
from .structures import MinHeap, Queue, Stack, HashMap, DisjointSet

SORTS = ("insertion", "shell", "bubble", "quick", "selection", "heap", "merge", "radix")


def sort_values(values, algorithm="merge", key=lambda x: x):
    a = list(values)
    if algorithm not in SORTS:
        raise ValueError("unknown sort: " + algorithm)
    if algorithm == "insertion":
        for i in range(1, len(a)):
            v, j = a[i], i - 1
            while j >= 0 and key(a[j]) > key(v):
                a[j + 1], j = a[j], j - 1
            a[j + 1] = v
    elif algorithm == "shell":
        gap = len(a) // 2
        while gap:
            for i in range(gap, len(a)):
                v, j = a[i], i
                while j >= gap and key(a[j - gap]) > key(v):
                    a[j], j = a[j - gap], j - gap
                a[j] = v
            gap //= 2
    elif algorithm == "bubble":
        for end in range(len(a) - 1, 0, -1):
            changed = False
            for i in range(end):
                if key(a[i]) > key(a[i + 1]):
                    a[i], a[i + 1] = a[i + 1], a[i]
                    changed = True
            if not changed:
                break
    elif algorithm == "selection":
        for i in range(len(a)):
            m = i
            for j in range(i + 1, len(a)):
                if key(a[j]) < key(a[m]):
                    m = j
            a[i], a[m] = a[m], a[i]
    elif algorithm == "quick":
        # Three-way partition prevents equal-key degeneration; explicit stack avoids recursion overflow.
        pending = Stack()
        pending.push((0, len(a) - 1))
        while pending:
            lo, hi = pending.pop()
            if lo >= hi:
                continue
            pivot = key(a[(lo + hi) // 2])
            lt = i = lo
            gt = hi
            while i <= gt:
                if key(a[i]) < pivot:
                    a[lt], a[i] = a[i], a[lt]
                    lt, i = lt + 1, i + 1
                elif key(a[i]) > pivot:
                    a[i], a[gt] = a[gt], a[i]
                    gt -= 1
                else:
                    i += 1
            pending.push((lo, lt - 1))
            pending.push((gt + 1, hi))
    elif algorithm == "heap":
        heap = MinHeap(a, key)
        a = [heap.pop() for _ in range(len(heap))]
    elif algorithm == "merge":
        width = 1
        while width < len(a):
            out = []
            for start in range(0, len(a), 2 * width):
                left, right = a[start:start + width], a[start + width:start + 2 * width]
                i = j = 0
                while i < len(left) and j < len(right):
                    if key(left[i]) <= key(right[j]):
                        out.append(left[i]); i += 1
                    else:
                        out.append(right[j]); j += 1
                out.extend(left[i:]); out.extend(right[j:])
            a, width = out, width * 2
    elif a:  # LSD radix: integer keys, including negative keys, stable buckets.
        if any(not isinstance(key(v), int) for v in a):
            raise ValueError("radix requires integer keys")
        offset = min(key(v) for v in a)
        maximum = max(key(v) - offset for v in a)
        place = 1
        while maximum // place:
            buckets = [Queue() for _ in range(10)]
            for v in a:
                buckets[((key(v) - offset) // place) % 10].push(v)
            a = []
            for bucket in buckets:
                while bucket:
                    a.append(bucket.pop())
            place *= 10
    return a


def binary_search(values, target):
    lo, hi = 0, len(values)
    while lo < hi:
        mid = (lo + hi) // 2
        if values[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo  # lower_bound; equal element may not exist


def kmp_table(pattern):
    table = [0] * len(pattern)
    j = 0
    for i in range(1, len(pattern)):
        while j and pattern[i] != pattern[j]:
            j = table[j - 1]
        if pattern[i] == pattern[j]:
            j += 1
        table[i] = j
    return table


def kmp_find(text, pattern):
    if not pattern:
        return 0
    table, j = kmp_table(pattern), 0
    for i, char in enumerate(text):
        while j and char != pattern[j]:
            j = table[j - 1]
        if char == pattern[j]:
            j += 1
        if j == len(pattern):
            return i - j + 1
    return -1


def _huffman_tree(frequencies):
    heap, serial = MinHeap(key=lambda item: (item[0], item[1])), 0
    for symbol, count in sorted(frequencies.items(), key=lambda p: int(p[0])):
        if not isinstance(count, int) or count <= 0 or not 0 <= int(symbol) <= 255:
            raise ValueError("invalid Huffman frequency")
        heap.push((count, serial, int(symbol))); serial += 1
    while len(heap) > 1:
        a, b = heap.pop(), heap.pop()
        heap.push((a[0] + b[0], serial, (a[2], b[2]))); serial += 1
    return heap.pop()[2] if heap else None


def huffman_encode(data):
    freq = HashMap()
    for byte in data:
        freq[byte] = freq.get(byte, 0) + 1
    frequencies = dict(freq.items())
    tree, codes = _huffman_tree(frequencies), {}
    def walk(node, prefix):
        if isinstance(node, int):
            codes[node] = prefix or "0"
        elif node is not None:
            walk(node[0], prefix + "0"); walk(node[1], prefix + "1")
    walk(tree, "")
    packed, value, count, bits = bytearray(), 0, 0, 0
    for byte in data:
        for bit in codes[byte]:
            value, count, bits = (value << 1) | int(bit), count + 1, bits + 1
            if count == 8:
                packed.append(value); value = count = 0
    if count:
        packed.append(value << (8 - count))
    return {"frequencies": frequencies, "bits": bits, "data": base64.b64encode(packed).decode("ascii")}


def huffman_decode(archive, max_bytes=64 * 1024 * 1024):
    frequencies = archive["frequencies"]
    expected = sum(frequencies.values())
    if expected > max_bytes:
        raise ValueError("archive exceeds decompression limit")
    tree = _huffman_tree(frequencies)
    raw = base64.b64decode(archive["data"], validate=True)
    bits = archive["bits"]
    if not isinstance(bits, int) or bits < 0 or len(raw) != (bits + 7) // 8:
        raise ValueError("invalid Huffman length")
    out, node = bytearray(), tree
    for i in range(bits):
        bit = (raw[i // 8] >> (7 - i % 8)) & 1
        if isinstance(tree, int):
            if bit:
                raise ValueError("invalid single-symbol stream")
            out.append(tree)
        else:
            if node is None:
                raise ValueError("invalid empty stream")
            node = node[bit]
            if isinstance(node, int):
                out.append(node); node = tree
        if len(out) > expected:
            raise ValueError("invalid decoded size")
    if len(out) != expected or node != tree:
        raise ValueError("truncated Huffman stream")
    actual = {}
    for byte in out:
        actual[str(byte)] = actual.get(str(byte), 0) + 1
    if actual != {str(k): v for k, v in frequencies.items()}:
        raise ValueError("Huffman frequency mismatch")
    return bytes(out)


class Graph:
    def __init__(self, vertices=()):
        self.adj = {v: {} for v in vertices}

    def add(self, a, b, weight=1, directed=False):
        if weight < 0:
            raise ValueError("nonnegative weights required")
        self.adj.setdefault(a, {})[b] = weight
        self.adj.setdefault(b, {})
        if not directed:
            self.adj[b][a] = weight

    def path(self, source, target, algorithm="bfs"):
        if source not in self.adj or target not in self.adj:
            raise KeyError("unknown graph vertex")
        previous, distance = {source: None}, {source: 0}
        if algorithm == "bfs":
            pending = Queue(); pending.push(source)
            while pending:
                a = pending.pop()
                for b in sorted(self.adj[a]):
                    if b not in previous:
                        previous[b], distance[b] = a, distance[a] + 1
                        pending.push(b)
        elif algorithm == "dijkstra":
            pending = MinHeap([(0, source)])
            while pending:
                dist, a = pending.pop()
                if dist != distance[a]:
                    continue
                for b, weight in self.adj[a].items():
                    candidate = dist + weight
                    if candidate < distance.get(b, float("inf")):
                        distance[b], previous[b] = candidate, a
                        pending.push((candidate, b))
        else:
            raise ValueError("path algorithm must be bfs or dijkstra")
        route = []
        if target in previous:
            node = target
            while node is not None:
                route.append(node); node = previous[node]
        return {"path": route[::-1], "distance": distance.get(target)}

    def dfs(self, source):
        if source not in self.adj:
            raise KeyError(source)
        stack, seen, result = Stack(), set(), []
        stack.push(source)
        while stack:
            a = stack.pop()
            if a in seen:
                continue
            seen.add(a); result.append(a)
            for b in sorted(self.adj[a], reverse=True):
                if b not in seen:
                    stack.push(b)
        return result

    def floyd(self):
        vertices = sorted(self.adj)
        d = {a: {b: (0 if a == b else self.adj[a].get(b, float("inf"))) for b in vertices} for a in vertices}
        for k in vertices:
            for i in vertices:
                for j in vertices:
                    d[i][j] = min(d[i][j], d[i][k] + d[k][j])
        return d

    def topological(self):
        indegree = {v: 0 for v in self.adj}
        for edges in self.adj.values():
            for b in edges:
                indegree[b] += 1
        queue, result = Queue(), []
        for v in sorted(indegree):
            if indegree[v] == 0:
                queue.push(v)
        while queue:
            v = queue.pop(); result.append(v)
            for b in self.adj[v]:
                indegree[b] -= 1
                if indegree[b] == 0:
                    queue.push(b)
        if len(result) != len(self.adj):
            raise ValueError("graph has a cycle; topological order undefined")
        return result

    def critical_path(self):
        order = self.topological()
        early = {v: 0 for v in order}
        for a in order:
            for b, w in self.adj[a].items():
                early[b] = max(early[b], early[a] + w)
        duration = max(early.values(), default=0)
        late = {v: duration for v in order}
        for a in reversed(order):
            for b, w in self.adj[a].items():
                late[a] = min(late[a], late[b] - w)
        edges = [(a, b, w) for a in order for b, w in self.adj[a].items() if early[a] == late[b] - w]
        return {"duration": duration, "early": early, "late": late, "critical_edges": edges}

    def spanning_forest(self, algorithm="kruskal"):
        # Requires an undirected graph, checked rather than silently treating a DAG as undirected.
        for a in self.adj:
            for b, w in self.adj[a].items():
                if self.adj[b].get(a) != w:
                    raise ValueError("spanning forest requires undirected edges")
        result = []
        if algorithm == "kruskal":
            edges = sort_values([(w, a, b) for a in self.adj for b, w in self.adj[a].items() if a < b])
            groups = DisjointSet(self.adj)
            for w, a, b in edges:
                if groups.union(a, b):
                    result.append((a, b, w))
        elif algorithm == "prim":
            seen = set()
            for start in sorted(self.adj):
                if start in seen:
                    continue
                seen.add(start)
                heap = MinHeap((w, start, b) for b, w in self.adj[start].items())
                while heap:
                    w, a, b = heap.pop()
                    if b in seen:
                        continue
                    seen.add(b); result.append((a, b, w))
                    for c, weight in self.adj[b].items():
                        if c not in seen:
                            heap.push((weight, b, c))
        else:
            raise ValueError("forest algorithm must be prim or kruskal")
        return {"edges": result, "weight": sum(edge[2] for edge in result)}
