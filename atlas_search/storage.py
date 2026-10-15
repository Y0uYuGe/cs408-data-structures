"""Checksummed dual snapshots, atomic replacement, and exclusive process locks."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import time

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
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    # POSIX directory fsync makes rename durable. Windows exposes no portable directory fsync.
    if os.name != "nt":
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def process_alive(pid):
    if type(pid) is not int or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        kernel = ctypes.windll.kernel32
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return kernel.GetLastError() == 5  # access denied: assume alive
        status = ctypes.c_ulong()
        try:
            return bool(kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(status))) and status.value == 259
        finally:
            kernel.CloseHandle(ctypes.c_void_p(handle))
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


@contextmanager
def database_lock(directory, timeout=5):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / "writer.lock"
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"pid": os.getpid()}, stream)
            break
        except FileExistsError:
            try:
                owner = json.loads(lock.read_text(encoding="utf-8"))
                if not process_alive(owner.get("pid")):
                    lock.unlink(missing_ok=True)
                    continue
            except (ValueError, OSError):
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError("database busy or incomplete lock; inspect writer.lock before manual removal")
            time.sleep(.05)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


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
