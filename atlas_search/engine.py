"""Small local search system tying the data structures into one workload."""
import hashlib
import json
from pathlib import Path
import re
from .structures import DynamicArray, LinkedList, HashMap, AVLTree, Trie, Stack, MinHeap
from .algorithms import sort_values, binary_search, kmp_find, huffman_encode, huffman_decode, Graph
from .query import parse, combine
from . import storage


def tokenize(text):
    """Latin words + CJK unigrams/bigrams; deterministic, not linguistic segmentation."""
    tokens = DynamicArray()
    for part in re.findall(r"[a-z0-9_]+|[\u3400-\u9fff]+", text.lower()):
        if "\u3400" <= part[0] <= "\u9fff":
            for char in part:
                tokens.append(char)
            for i in range(len(part) - 1):
                tokens.append(part[i:i + 2])
        else:
            tokens.append(part)
    return list(tokens)


class Engine:
    def __init__(self, directory):
        self.directory = Path(directory)
        payload, self.recovered = storage.load(directory)
        self._restore(payload)

    def _restore(self, payload):
        self.revision, self.next_id = payload["revision"], payload["next_id"]
        self.posting_backend = payload["posting_backend"]
        self.documents = HashMap()
        for doc in payload["documents"]:
            self.documents[doc["id"]] = doc
        self.rebuild()

    def payload(self):
        return {"schema": storage.SCHEMA, "revision": self.revision, "next_id": self.next_id,
                "posting_backend": self.posting_backend,
                "documents": [doc for _, doc in sort_values(self.documents.items(), key=lambda item: item[0])]}

    def commit(self):
        self.revision += 1
        storage.save(self.directory, self.payload())
        self.recovered = False

    def rebuild(self):
        self.postings, self.frequencies = HashMap(), HashMap()
        self.sizes, self.trie = AVLTree(), Trie()
        for doc_id, doc in sort_values(self.documents.items(), key=lambda item: item[0]):
            self._index(doc)

    def _index(self, doc):
        doc_id, freq = doc["id"], HashMap()
        for token in tokenize(doc["title"] + " " + doc["text"]):
            freq[token] = freq.get(token, 0) + 1
        self.frequencies[doc_id] = freq
        for token in freq:
            if token not in self.postings:
                self.postings[token] = DynamicArray() if self.posting_backend == "array" else LinkedList()
                self.trie.add(token)
            posting = self.postings[token]
            if isinstance(posting, DynamicArray):
                posting.insert(binary_search(posting, doc_id), doc_id)
            else:
                # Linked alternative deliberately pays O(n) rebuilding ordered links.
                values = sort_values([*posting, doc_id])
                self.postings[token] = LinkedList(values)
        self.sizes.put((len(doc["text"]), doc_id), doc_id)

    def _unindex(self, doc):
        doc_id = doc["id"]
        for token in self.frequencies[doc_id]:
            posting = self.postings[token]
            if isinstance(posting, DynamicArray):
                posting.pop(binary_search(posting, doc_id))
            else:
                posting.remove(doc_id)
            if not posting:
                del self.postings[token]
                self.trie.remove(token)
        del self.frequencies[doc_id]
        self.sizes.delete((len(doc["text"]), doc_id))

    def _links(self, links, doc_id=None):
        links = sort_values(set(links))
        if any(v not in self.documents or v == doc_id for v in links):
            raise ValueError("links must reference existing other documents")
        return links

    def add(self, title, text, source="", links=()):
        links = self._links(links)
        doc_id = self.next_id
        self.next_id += 1
        self.documents[doc_id] = {"id": doc_id, "title": title, "text": text, "source": source, "links": links}
        self._index(self.documents[doc_id]); self.commit()
        return doc_id

    def update(self, doc_id, title=None, text=None, links=None):
        old = self.documents[doc_id]
        doc = dict(old)
        if title is not None:
            doc["title"] = title
        if text is not None:
            doc["text"] = text
        if links is not None:
            doc["links"] = self._links(links, doc_id)
        self._unindex(old)
        self.documents[doc_id] = doc
        self._index(doc); self.commit()

    def delete(self, doc_id):
        self._unindex(self.documents[doc_id])
        del self.documents[doc_id]
        for _, doc in self.documents.items():
            doc["links"] = [v for v in doc["links"] if v != doc_id]
        self.commit()

    def index_directory(self, directory):
        """Upsert UTF-8 .txt/.md; source deletion is explicit via delete, never implicit."""
        root = Path(directory).resolve()
        if not root.is_dir():
            raise ValueError("index directory does not exist")
        source_map = {doc["source"]: doc["id"] for _, doc in self.documents.items() if doc["source"]}
        added = updated = 0
        # Read all files before mutating to make decoding failures leave the database unchanged.
        files = [(path, path.read_text(encoding="utf-8")) for path in sorted(root.rglob("*"))
                 if path.is_file() and path.suffix.lower() in (".txt", ".md")]
        for path, text in files:
            source = str(path.resolve())
            doc_id = source_map.get(source)
            if doc_id is None:
                doc_id = self.next_id; self.next_id += 1; added += 1
                self.documents[doc_id] = {"id": doc_id, "title": path.stem, "text": text, "source": source, "links": []}
            else:
                doc = self.documents[doc_id]
                self.documents[doc_id] = {**doc, "title": path.stem, "text": text}
                updated += 1
        self.rebuild(); self.commit()
        return {"added": added, "updated": updated}

    def term(self, operand):
        if operand.startswith('"'):
            phrase = operand[1:-1].lower()
            if not phrase:
                raise ValueError("empty phrase")
            return sort_values([doc_id for doc_id, doc in self.documents.items()
                if kmp_find((doc["title"] + " " + doc["text"]).lower(), phrase) >= 0])
        tokens = tokenize(operand)
        if not tokens:
            return []
        result = list(self.postings.get(tokens[0], []))
        for token in tokens[1:]:
            result = combine(result, list(self.postings.get(token, [])), "AND")
        return result

    def search(self, expression, limit=10, sort="heap"):
        if limit < 0:
            raise ValueError("limit must be nonnegative")
        rpn, stack = parse(expression), Stack()
        universe = sort_values(self.documents)
        query_terms = HashMap()
        for token in rpn:
            if token == "NOT":
                stack.push(combine(universe, stack.pop(), "DIFF"))
            elif token in ("AND", "OR"):
                right, left = stack.pop(), stack.pop()
                stack.push(combine(left, right, token))
            else:
                stack.push(self.term(token))
                for term in tokenize(token.strip('"')):
                    query_terms[term] = True
        if len(stack) != 1:
            raise ValueError("malformed query")
        rows = []
        for doc_id in stack.pop():
            doc, freq = self.documents[doc_id], self.frequencies[doc_id]
            score = sum(freq.get(term, 0) for term in query_terms)
            rows.append({"id": doc_id, "title": doc["title"], "score": score, "source": doc["source"], "snippet": doc["text"][:160]})
        # Encoding total order into one integer also gives radix a meaningful comparable key.
        key = lambda row: -row["score"] * self.next_id + row["id"]
        if sort == "heap":
            heap = MinHeap(rows, key=key)
            return [heap.pop() for _ in range(min(limit, len(heap)))]
        return sort_values(rows, sort, key=key)[:limit]

    def range(self, minimum, maximum):
        if minimum < 0 or maximum < minimum:
            raise ValueError("range requires 0 <= min <= max")
        return [self.documents[doc_id] for _, doc_id in self.sizes.range((minimum, 0), (maximum, self.next_id))]

    def locate_id(self, doc_id):
        """Binary-search selector contrasts ordered sequential lookup with hash lookup."""
        ids = sort_values(self.documents)
        position = binary_search(ids, doc_id)
        return self.documents[ids[position]] if position < len(ids) and ids[position] == doc_id else None

    def graph(self, directed=False):
        ids = sort_values(self.documents)
        graph = Graph(ids)
        if directed:
            for a, doc in self.documents.items():
                for b in doc["links"]:
                    graph.add(a, b, max(1, len(self.documents[b]["text"])), True)
        else:
            terms = {doc_id: sort_values(self.frequencies[doc_id]) for doc_id in ids}
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    overlap = len(combine(terms[a], terms[b], "AND"))
                    if overlap:
                        graph.add(a, b, max(1, 100 // overlap))
        return graph

    def export_archive(self, path):
        raw = storage.canonical(self.payload())
        archive = {"format": "atlas-huffman-1", "sha256": hashlib.sha256(raw).hexdigest(), "content": huffman_encode(raw)}
        storage.atomic_write(path, storage.canonical(archive))
        return {"raw_bytes": len(raw), "archive_bytes": Path(path).stat().st_size}

    def import_archive(self, path, replace=False):
        if len(self.documents) and not replace:
            raise ValueError("database is not empty; use --replace to restore archive")
        archive = json.loads(Path(path).read_text(encoding="utf-8"))
        if archive.get("format") != "atlas-huffman-1":
            raise ValueError("unsupported archive format")
        raw = huffman_decode(archive["content"])
        if hashlib.sha256(raw).hexdigest() != archive["sha256"]:
            raise ValueError("archive checksum mismatch")
        payload = json.loads(raw)
        storage.validate_payload(payload)
        revision = self.revision
        self._restore(payload)
        self.revision = revision
        self.commit()

    def check(self):
        storage.validate_payload(self.payload())
        self.sizes.validate()
        expected = {}
        for doc_id, doc in self.documents.items():
            counts = {}
            for token in tokenize(doc["title"] + " " + doc["text"]):
                expected.setdefault(token, set()).add(doc_id)
                counts[token] = counts.get(token, 0) + 1
            if dict(self.frequencies[doc_id].items()) != counts:
                raise AssertionError("document frequency mismatch")
        if sort_values(self.frequencies) != sort_values(self.documents):
            raise AssertionError("frequency document ids mismatch")
        actual = {token: list(posting) for token, posting in self.postings.items()}
        if actual != {token: sort_values(ids) for token, ids in expected.items()}:
            raise AssertionError("posting index mismatch")
        if self.trie.prefix("", limit=len(actual) + 1) != sort_values(actual):
            raise AssertionError("Trie vocabulary mismatch")
        actual_sizes = list(self.sizes.range((0, 0), (float("inf"), float("inf"))))
        expected_sizes = sort_values([((len(doc["text"]), doc_id), doc_id) for doc_id, doc in self.documents.items()])
        if actual_sizes != expected_sizes:
            raise AssertionError("size index mismatch")
        return {"ok": True, "documents": len(self.documents), "terms": len(self.postings), "revision": self.revision,
                "posting_backend": self.posting_backend, "recovered_from_backup": self.recovered}
