from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CRMOrganization:
    id: str
    name: str
    website: str | None


@dataclass
class CRMContact:
    id: str
    email: str
    name: str | None
    org_id: str | None


@dataclass
class RelatedCounts:
    """Snapshot of a record's related-record volume, taken *before* any
    merge — the score-based primary-selection rule (see pipeline/discover.py,
    once built) picks the richest candidate as "primary" using exactly these
    counts, and the audit note reports them so a merge log reads "4 contacts,
    2 open deals, 1 note absorbed" instead of a vague "merged records"."""

    contacts: int = 0
    deals: int = 0
    notes: int = 0
    open_activities: int = 0


class CRMClient(ABC):
    """A pluggable CRM backend. Organizations dedup on normalized website
    (domain) — not name, which varies too much in formatting to be a
    reliable key. Contacts dedup on email. See design notes: both dedup
    pipelines share the same fetch → group → snapshot → score → merge →
    audit-note shape, which is why one interface covers both entity types
    rather than two unrelated ones.
    """

    name: str

    @abstractmethod
    def list_organizations(self) -> list[CRMOrganization]:
        raise NotImplementedError

    @abstractmethod
    def list_contacts(self) -> list[CRMContact]:
        raise NotImplementedError

    @abstractmethod
    def get_organization_related_counts(self, org_id: str) -> RelatedCounts:
        raise NotImplementedError

    @abstractmethod
    def get_contact_related_counts(self, contact_id: str) -> RelatedCounts:
        raise NotImplementedError

    @abstractmethod
    def merge_organizations(self, primary_id: str, source_id: str) -> None:
        """Absorb source_id into primary_id via the CRM's native merge
        endpoint. Caller is responsible for snapshotting counts and
        re-verifying source_id still exists before calling this — this
        method performs the merge itself, nothing more."""
        raise NotImplementedError

    @abstractmethod
    def merge_contacts(self, primary_id: str, source_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_note(self, entity_type: str, entity_id: str, text: str) -> None:
        """Post an audit note on a record — the audit trail of record for
        every merge, per design notes."""
        raise NotImplementedError
