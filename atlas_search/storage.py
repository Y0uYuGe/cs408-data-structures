"""Checksummed dual snapshots, atomic replacement, and exclusive process locks."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import time
import tempfile

SCHEMA = 1


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def envelope(payload):
    return {"sha256": hashlib.sha256(canonical(payload)).hexdigest(), "payload": payload}


def verify(value):
    payload = value["payload"]
    if value["sha256"] != hashlib.sha256(canonical(payload)).hexdigest():
        raise ValueError("snapshot checksum mismatch")
    validate_payload(payload)
    return payload


def validate_payload(payload):
    if payload.get("schema") != SCHEMA:
        raise ValueError("unsupported snapshot schema")
    if type(payload.get("revision")) is not int or payload["revision"] < 0:
        raise ValueError("invalid revision")
    if type(payload.get("next_id")) is not int or payload["next_id"] < 1:
        raise ValueError("invalid next_id")
    if payload.get("posting_backend") not in ("array", "linked"):
        raise ValueError("invalid posting backend")
    docs = payload.get("documents")
    if not isinstance(docs, list):
        raise ValueError("documents must be an array")
    ids = set()
    for doc in docs:
        if type(doc.get("id")) is not int or not 0 < doc["id"] < payload["next_id"] or doc["id"] in ids:
            raise ValueError("duplicate/out-of-range document id")
        ids.add(doc["id"])
        if any(not isinstance(doc.get(k), str) for k in ("title", "text", "source")):
            raise ValueError("invalid document strings")
        if not isinstance(doc.get("links"), list) or any(type(v) is not int for v in doc["links"]):
            raise ValueError("invalid links")
        if len(set(doc["links"])) != len(doc["links"]):
            raise ValueError("duplicate links")
    for doc in docs:
        if any(v not in ids or v == doc["id"] for v in doc["links"]):
            raise ValueError("dangling/self document link")


def atomic_write(path, data):
    path = Path(path)
    descriptor, name = tempfile.mkstemp(prefix=path.name+".tmp-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        deadline = time.monotonic()+2
        while True:
            try:
                os.replace(temporary, path)
                break
            except OSError as exc:
                if os.name != "nt" or getattr(exc, "winerror", None) not in (5,32,33) or time.monotonic() >= deadline:
                    raise
                time.sleep(.02)
    finally:
        temporary.unlink(missing_ok=True)
    # POSIX directory fsync makes rename durable. Windows exposes no portable directory fsync.
    if os.name != "nt":
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


@contextmanager
def database_lock(directory, timeout=5):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / "writer.lock"
    # The file remains at a stable path/inode. Unlinking a PID sentinel has a
    # check-then-delete race: a waiter can delete a newly acquired writer's lock.
    # OS locks are released on process exit, including abnormal termination.
    fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    acquired = False
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("database busy; another process holds the OS file lock")
                time.sleep(.02)
        os.ftruncate(fd, 0)
        os.write(fd, canonical({"pid": os.getpid()}))
        os.fsync(fd)
        yield
    finally:
        if acquired:
            os.lseek(fd, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def load(directory):
    directory = Path(directory)
    candidates, errors, present = [], [], False
    for filename in ("snapshot.json", "snapshot.backup.json"):
        path = directory / filename
        if not path.exists():
            continue
        present = True
        try:
            payload = verify(json.loads(path.read_text(encoding="utf-8")))
            candidates.append((payload["revision"], filename, payload))
        except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
            errors.append(f"{filename}: {exc}")
    if not candidates:
        if present:
            raise ValueError("no valid snapshot: " + "; ".join(errors))
        return {"schema": SCHEMA, "revision": 0, "next_id": 1, "posting_backend": "array", "documents": []}, False
    candidates.sort(key=lambda item: (item[0], item[1] == "snapshot.json"), reverse=True)
    _, filename, payload = candidates[0]
    return payload, filename != "snapshot.json"


def save(directory, payload):
    validate_payload(payload)
    data = canonical(envelope(payload))
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write(directory / "snapshot.json", data)
    atomic_write(directory / "snapshot.backup.json", data)
