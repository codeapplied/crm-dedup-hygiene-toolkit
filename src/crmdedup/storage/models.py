from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Naive UTC timestamp — SQLite doesn't preserve tzinfo on round-trip,
    so a timezone-aware value read back would never equal a freshly-built
    one even when unchanged. Stay naive-UTC everywhere instead."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Organization(Base):
    """A CRM organization record. domain is the normalized dedup key
    (protocol/www/path/port stripped, lowercased) — two organizations
    sharing a domain are a duplicate candidate group."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    crm_org_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Contact(Base):
    """A CRM contact record. email is the dedup key — two contacts sharing
    an email (regardless of organization) are a duplicate candidate pair."""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    organization_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    crm_contact_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class MergeLog(Base):
    """One row per duplicate group processed — what the ops CLI reads for
    history. A dry run still writes a row (status='dry_run') so the planned
    merge is reviewable before anyone commits to --execute."""

    __tablename__ = "merge_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(20), index=True)
    group_key: Mapped[str] = mapped_column(String(320))
    # CRM record id, not a local table PK — opaque string (the sandbox
    # backend uses ids like "org-1"; Pipedrive's are numeric-looking but
    # still handled as strings throughout CRMClient) rather than int.
    primary_record_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    absorbed_record_ids: Mapped[str] = mapped_column(Text, default="")
    primary_score: Mapped[int | None] = mapped_column(nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
