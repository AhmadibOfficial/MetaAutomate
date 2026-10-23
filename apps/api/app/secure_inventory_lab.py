"""P2-061: gated, local-only, encrypted, tenant-scoped inventory data lab.

This is a working source component, NOT production data storage, PostgreSQL RLS,
an independent identity provider, a public API, or a verified backup lifecycle.
The API wrapper must supply a database-authenticated Principal; no tenant IDs
are accepted from uploaded files or caller-controlled request fields.
"""
from __future__ import annotations

import base64
import binascii
import csv
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import hmac
from io import StringIO
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from uuid import UUID, uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

COLUMNS = ("sku", "name", "stock", "weekly_sales", "unit_price_kobo")
MAX_BYTES = 64 * 1024
MAX_ROWS = 200
MAX_RETENTION_DAYS = 30
MAX_ACTIVE_DOCUMENTS = 25
READ_ROLES = frozenset({"OWNER", "ADMIN", "OPERATOR"})
WRITE_ROLES = frozenset({"OWNER", "ADMIN"})
DELETE_ROLES = frozenset({"OWNER", "ADMIN"})
GENESIS = "0" * 64
SAFE_SKU = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,35}\Z")
NATURAL = re.compile(r"(0|[1-9][0-9]*)\Z")


class DataLabError(ValueError):
    """Invalid input, forbidden cross-tenant access, or compromised evidence."""


def deny(message: str):
    raise DataLabError(message)


def _principal(principal, roles):
    # This class is called after the existing app.authn verified the browser
    # session or local development bearer token through PostgreSQL.
    org, user, role = (getattr(principal, "organization_id", None),
                       getattr(principal, "user_id", None),
                       getattr(principal, "role", None))
    if not isinstance(org, UUID) or not isinstance(user, UUID) or role not in roles:
        deny("Authenticated tenant member with required role is needed")
    return str(org), str(user)


def _integer(value: str, kind: str, maximum: int) -> int:
    if not isinstance(value, str) or len(value) > 15 or NATURAL.fullmatch(value) is None:
        deny("Invalid integer " + kind)
    number = int(value)
    if number > maximum:
        deny("Out of range " + kind)
    return number


def _label(value: str, kind: str, maximum: int) -> str:
    if not isinstance(value, str):
        deny("Invalid " + kind)
    s = value.strip()
    if (not s or len(s) > maximum or
            any(ord(char) < 32 or ord(char) == 127 for char in s) or
            any(char in s for char in "<>") or s[0] in "=+-@"):
        deny("Unsafe or invalid " + kind)
    return s


def parse_inventory(raw: bytes) -> list[dict]:
    if not isinstance(raw, bytes) or not (1 <= len(raw) <= MAX_BYTES):
        deny("Inventory CSV must be 1 to 65536 bytes")
    try:
        contents = raw.decode("utf-8-sig")
        reader = csv.reader(StringIO(contents, newline=""), strict=True)
        header = next(reader)
        if tuple(header) != COLUMNS:
            deny("Inventory CSV headers do not match the approved template")
        items, seen = [], set()
        for row in reader:
            if len(items) >= MAX_ROWS:
                deny("Maximum 200 inventory records")
            if len(row) != len(COLUMNS):
                deny("Invalid inventory record width")
            sku = _label(row[0], "SKU", 36)
            if not SAFE_SKU.fullmatch(sku) or sku.lower() in seen:
                deny("Duplicate or invalid SKU")
            seen.add(sku.lower())
            name = _label(row[1], "name", 90)
            stock = _integer(row[2], "stock", 1_000_000)
            sales = _integer(row[3], "weekly_sales", 1_000_000)
            price = _integer(row[4], "unit_price_kobo", 100_000_000_000)
            if price == 0:
                deny("Unit price must be positive")
            items.append(dict(sku=sku, name=name, stock=stock,
                              weekly_sales=sales, unit_price_kobo=price))
    except (UnicodeDecodeError, csv.Error, StopIteration) as exc:
        raise DataLabError("Malformed UTF-8 inventory CSV") from exc
    if not items:
        deny("At least one inventory item is required")
    return items


def _derive(key: bytes, tenant: str, kind: str) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32,
                salt=UUID(tenant).bytes, info=("metautomate-p2-061:" + kind).encode()).derive(key)


def _seal(key: bytes, tenant: str, identifier: str, items: list[dict]) -> tuple[bytes, bytes]:
    nonce = os.urandom(12)
    payload = json.dumps(items, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    aad = (tenant + ":" + identifier + ":inventory-v1").encode("ascii")
    return nonce, AESGCM(_derive(key, tenant, "inventory-aesgcm-v1")).encrypt(nonce, payload, aad)


def _unseal(key: bytes, tenant: str, identifier: str, nonce: bytes, encrypted: bytes) -> list[dict]:
    aad = (tenant + ":" + identifier + ":inventory-v1").encode("ascii")
    try:
        decoded = AESGCM(_derive(key, tenant, "inventory-aesgcm-v1")).decrypt(nonce, encrypted, aad)
        records = json.loads(decoded)
        if not isinstance(records, list) or not records:
            deny("Stored document failed validation")
        return records
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DataLabError("Encrypted data cannot be verified") from exc
    except Exception as exc:
        # Do not reveal whether a key, tenant or ciphertext was incorrect.
        raise DataLabError("Encrypted data cannot be verified") from exc


def _mac(key: bytes, tenant: str, payload: dict) -> str:
    message = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hmac.new(_derive(key, tenant, "audit-hmac-v1"), message, sha256).hexdigest()


@contextmanager
def _connect(path: Path):
    conn = sqlite3.connect(str(path), timeout=5)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA secure_delete=ON")
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


class SecureInventoryLab:
    """A single local SQLite file, encrypted documents, and authenticated tenant operations.

    Key material must come from a protected environment secret, never a CSV or
    the on-disk database. All write methods are transaction-serialized.
    """

    def __init__(self, path: str | Path, key: bytes):
        if not isinstance(key, bytes) or len(key) != 32:
            deny("Data-lab root key must be exactly 32 bytes")
        self.key = key
        self.path = Path(path)
        if not self.path.is_absolute() or self.path.is_symlink():
            deny("Use a non-symlink absolute SQLite file path")
        if not self.path.parent.is_dir() or self.path.parent.is_symlink():
            deny("Use a real, existing data-lab directory (not a symlink)")
        if self.path.exists() and not self.path.is_file():
            deny("Data-lab path must be a regular file")
        # Avoid process-global umask changes in a multi-request API process.
        # Open a new empty DB with owner-only permissions before SQLite touches it.
        if not self.path.exists():
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            handle = os.open(self.path, flags, 0o600)
            os.close(handle)
        with _connect(self.path) as conn:
                conn.executescript("""
                CREATE TABLE IF NOT EXISTS inventory_documents(
                    document_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    record_count INTEGER NOT NULL,
                    retained_until INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    nonce BLOB NOT NULL,
                    encrypted BLOB NOT NULL,
                    consent_claim TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS tenant_docs ON inventory_documents(tenant_id,created_at);
                CREATE TABLE IF NOT EXISTS inventory_audit(
                    tenant_id TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    actor_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    event_time INTEGER NOT NULL,
                    prior_mac TEXT NOT NULL,
                    mac TEXT NOT NULL,
                    PRIMARY KEY(tenant_id,sequence_number)
                );
                """)
        if self.path.stat().st_mode & 0o077:
            deny("Data-lab database permissions must be owner-only (0600)")

    @classmethod
    def from_environment(cls):
        raw = os.environ.get("MAT_DATA_LAB_KEY_B64", "")
        try:
            key = base64.b64decode(raw, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise DataLabError("Valid base64 data-lab key required") from exc
        path = os.environ.get("MAT_DATA_LAB_SQLITE", "")
        if not path:
            deny("Explicit local data-lab database path required")
        return cls(path, key)

    def _audit(self, conn, tenant: str, actor: str, action: str, doc: str, now: int):
        previous = conn.execute(
            "SELECT sequence_number,mac FROM inventory_audit WHERE tenant_id=? "
            "ORDER BY sequence_number DESC LIMIT 1", (tenant,)
        ).fetchone()
        seq = previous["sequence_number"] + 1 if previous else 1
        prior = previous["mac"] if previous else GENESIS
        data = dict(tenant_id=tenant, sequence_number=seq, actor_id=actor,
                    event=action, document_id=doc, event_time=now, prior_mac=prior)
        conn.execute("INSERT INTO inventory_audit VALUES(?,?,?,?,?,?,?,?)",
                     (tenant, seq, actor, action, doc, now, prior, _mac(self.key, tenant, data)))

    def import_csv(self, principal, raw: bytes, *, retention_days: int,
                   consent_claim: str, now: int | None = None) -> dict:
        tenant, actor = _principal(principal, WRITE_ROLES)
        if type(retention_days) is not int or not 1 <= retention_days <= MAX_RETENTION_DAYS:
            deny("Retention must be between one and 30 days")
        if consent_claim != "OWNER_AUTHORIZED_INVENTORY_NO_PERSONAL_DATA":
            deny("Explicit inventory-only ownership/consent declaration required")
        items = parse_inventory(raw)
        now = int(time.time()) if now is None else now
        if type(now) is not int or now < 1:
            deny("Invalid observation time")
        doc = str(uuid4())
        nonce, encrypted = _seal(self.key, tenant, doc, items)
        digest = sha256(raw).hexdigest()
        expiration = now + retention_days * 86400
        with _connect(self.path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            active_count = conn.execute(
                "SELECT count(*) FROM inventory_documents WHERE tenant_id=? AND retained_until>?",
                (tenant, now)
            ).fetchone()[0]
            if active_count >= MAX_ACTIVE_DOCUMENTS:
                deny("Active inventory-document quota reached (25 per tenant)")
            conn.execute(
                "INSERT INTO inventory_documents VALUES (?,?,?,?,?,?,?,?,?,?)",
                (doc, tenant, actor, digest, len(items), expiration, now,
                 nonce, encrypted, consent_claim))
            self._audit(conn, tenant, actor, "INVENTORY_IMPORTED", doc, now)
        return dict(document_id=doc, record_count=len(items), source_sha256=digest,
                    retained_until=expiration, encrypted_at_rest=True,
                    source_ownership_independently_verified=False,
                    production_available=False)

    def list_documents(self, principal, *, now: int | None = None) -> list[dict]:
        tenant, _ = _principal(principal, READ_ROLES)
        current = int(time.time()) if now is None else now
        with _connect(self.path) as conn:
            rows = conn.execute(
                "SELECT document_id,record_count,source_sha256,retained_until,created_at "
                "FROM inventory_documents WHERE tenant_id=? AND retained_until>? "
                "ORDER BY created_at DESC,document_id DESC LIMIT 200",
                (tenant, current)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_document(self, principal, identifier: UUID, *, now: int | None = None) -> dict:
        tenant, _ = _principal(principal, READ_ROLES)
        if not isinstance(identifier, UUID):
            deny("Invalid document identifier")
        current = int(time.time()) if now is None else now
        with _connect(self.path) as conn:
            row = conn.execute(
                "SELECT nonce,encrypted,record_count,retained_until FROM inventory_documents "
                "WHERE tenant_id=? AND document_id=?", (tenant, str(identifier))
            ).fetchone()
        if row is None or row["retained_until"] <= current:
            deny("Document not found or retention expired")
        items = _unseal(self.key, tenant, str(identifier), row["nonce"], row["encrypted"])
        if len(items) != row["record_count"]:
            deny("Stored document record count altered")
        with _connect(self.path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._audit(conn, tenant, str(principal.user_id), "INVENTORY_READ",
                        str(identifier), current)
        return dict(document_id=str(identifier), record_count=len(items), records=items,
                    retained_until=row["retained_until"],
                    encrypted_at_rest=True, external_execution_authorized=False)

    def delete_document(self, principal, identifier: UUID, *, now: int | None = None) -> dict:
        tenant, actor = _principal(principal, DELETE_ROLES)
        if not isinstance(identifier, UUID):
            deny("Invalid document identifier")
        timestamp = int(time.time()) if now is None else now
        with _connect(self.path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            deleted = conn.execute(
                "DELETE FROM inventory_documents WHERE tenant_id=? AND document_id=?",
                (tenant, str(identifier))
            ).rowcount
            if deleted != 1:
                deny("Document not found in authorized workspace")
            self._audit(conn, tenant, actor, "INVENTORY_DELETED", str(identifier), timestamp)
        return dict(document_id=str(identifier), deleted=True,
                    deletion_scope="ACTIVE_SQLITE_RECORD_ONLY",
                    backup_copies_verified_deleted=False)

    def purge_expired(self, principal, *, now: int | None = None) -> dict:
        tenant, actor = _principal(principal, DELETE_ROLES)
        timestamp = int(time.time()) if now is None else now
        with _connect(self.path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            expired = conn.execute(
                "SELECT document_id FROM inventory_documents WHERE tenant_id=? "
                "AND retained_until<=? ORDER BY document_id", (tenant, timestamp)
            ).fetchall()
            for row in expired:
                conn.execute("DELETE FROM inventory_documents WHERE tenant_id=? AND document_id=?",
                             (tenant, row["document_id"]))
                self._audit(conn, tenant, actor, "INVENTORY_EXPIRED_PURGED",
                            row["document_id"], timestamp)
        return dict(purged=len(expired), scope="AUTHORIZED_TENANT_ONLY",
                    backup_copies_verified_deleted=False)

    def verify_audit(self, principal) -> dict:
        tenant, _ = _principal(principal, READ_ROLES)
        with _connect(self.path) as conn:
            events = conn.execute(
                "SELECT * FROM inventory_audit WHERE tenant_id=? ORDER BY sequence_number",
                (tenant,)
            ).fetchall()
        previous = GENESIS
        for expected, event in enumerate(events, 1):
            data = {field: event[field] for field in (
                "tenant_id", "sequence_number", "actor_id", "event",
                "document_id", "event_time", "prior_mac")}
            checksum = _mac(self.key, tenant, data)
            if (event["sequence_number"] != expected or event["prior_mac"] != previous or
                    not hmac.compare_digest(checksum, event["mac"])):
                deny("Data-lab audit chain integrity verification failed")
            previous = event["mac"]
        return dict(events=len(events), integrity="LOCAL_HMAC_CHAIN_VERIFIED",
                    last_mac=previous, independently_anchored=False,
                    production_audit_ready=False)
