"""Request-ID journal for irreversible AX actions (send, delete, submit).

Usage:

    journal = OperationJournal(Path.home() / ".config/myapp-ax/operations")
    result = journal.run(
        operation_id="add-001",
        target={"window": "Exact title", "text": text},
        baseline=lambda: read_state(),               # read the UI before acting
        dispatch=lambda: call_bridge("press", ...),  # one native call, never retried
        confirm=lambda base: observed(base),          # read the UI again; True when the change is visible
        wait_seconds=3,
    )

Phases: dispatching -> observed | outcome_unknown | blocked.
The record is written to disk *before* dispatch, so a crash or lost response leaves
"may have happened" behind and the same ID is never dispatched twice.
"""

import hashlib
import json
import os
import re
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

if os.name == "nt":  # Windows: byte-range lock instead of flock, no O_NOFOLLOW, no directory fsync.
    import msvcrt

    def _try_lock(descriptor):
        os.lseek(descriptor, 0, os.SEEK_SET)
        try:
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        except OSError:
            raise BlockingIOError from None
else:
    import fcntl

    def _try_lock(descriptor):
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)

O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
ID_PATTERN = re.compile(r"[A-Za-z0-9_.:-]{1,128}")
FINAL = ("observed", "blocked")


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def save_private(path, value):
    descriptor, temporary = tempfile.mkstemp(prefix=".operation-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class OperationJournal:
    def __init__(self, root):
        self.root = Path(root)

    @contextmanager
    def lock(self):
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(self.root / ".lock", os.O_CREAT | os.O_RDWR | O_NOFOLLOW, 0o600)
        try:
            try:
                _try_lock(descriptor)
            except BlockingIOError:
                raise ValueError("Another operation is in progress") from None
            yield
        finally:
            os.close(descriptor)

    def path(self, operation_id):
        if not isinstance(operation_id, str) or not ID_PATTERN.fullmatch(operation_id):
            raise ValueError("operation_id must be 1..128 letters, digits, dots, underscores, colons or hyphens")
        return self.root / (digest(operation_id) + ".json")

    def load(self, path):
        if not path.exists():
            return None
        descriptor = os.open(path, os.O_RDONLY | O_NOFOLLOW)
        with os.fdopen(descriptor) as stream:
            return json.load(stream)

    @staticmethod
    def output(record, **extra):
        return {"status": record["phase"], "operationId": record["operationId"], "reason": record.get("reason"),
                "native": record.get("native"), "retrySafe": False, **extra}

    def _confirm(self, path, record, confirm, wait_seconds):
        until = time.monotonic() + wait_seconds
        while True:
            try:
                if confirm(record["baseline"]):
                    record.update(phase="observed", reason="expected_change_observed")
                    save_private(path, record)
                    return self.output(record)
            except Exception:
                pass
            if time.monotonic() >= until:
                record.update(phase="outcome_unknown", reason="change_not_observed")
                save_private(path, record)
                return self.output(record)
            time.sleep(min(0.15, max(0, until - time.monotonic())))

    def run(self, operation_id, target, baseline, dispatch, confirm, wait_seconds=3):
        path = self.path(operation_id)
        # Store a fingerprint, not the user's text.
        fingerprint = digest(json.dumps(target, ensure_ascii=False, sort_keys=True))
        with self.lock():
            record = self.load(path)
            if record:
                if record["fingerprint"] != fingerprint:
                    raise ValueError("operation_id is already bound to another target or content")
                if record["phase"] in FINAL:
                    return self.output(record, deduplicated=True, nativeCalls=0)
                return {**self._confirm(path, record, confirm, wait_seconds), "deduplicated": True, "nativeCalls": 0}
            record = {"operationId": operation_id, "fingerprint": fingerprint, "baseline": baseline(),
                      "createdAt": time.time(), "phase": "dispatching"}
            save_private(path, record)
            try:
                native = dispatch()
            except Exception as error:
                native = {"status": "bridge_result_unknown", "errorType": type(error).__name__, "dispatchAttempted": None}
            record["native"] = native
            if native.get("dispatchAttempted") is False:
                record.update(phase="blocked", reason=native.get("reason", native.get("status")))
                save_private(path, record)
                return self.output(record, nativeCalls=1)
            return {**self._confirm(path, record, confirm, wait_seconds), "nativeCalls": 1}

    def result(self, operation_id, confirm, wait_seconds=0):
        """Look up (and optionally re-confirm) an earlier request. Never dispatches."""
        path = self.path(operation_id)
        with self.lock():
            record = self.load(path)
            if not record:
                raise ValueError("Unknown operation_id")
            if record["phase"] in FINAL:
                return self.output(record)
            return self._confirm(path, record, confirm, wait_seconds)
