import re
from dataclasses import dataclass

from .crm.base import CRMContact, CRMOrganization, RelatedCounts


def normalize_domain(website: str | None) -> str | None:
    """Strip protocol, www, path/query, port, lowercase — written once,
    applied identically to every website value compared anywhere, to avoid
    the near-duplicate-key bug class this exact normalization was built to
    prevent (see design notes)."""
    if not website:
        return None
    value = website.strip().lower()
    value = re.sub(r"^https?://", "", value)
    value = re.sub(r"^www\.", "", value)
    value = value.split("/")[0].split("?")[0].split(":")[0]
    return value or None


@dataclass
class DuplicateGroup:
    entity_type: str  # "organization" | "contact"
    key: str
    member_ids: list[str]


def group_organizations_by_domain(orgs: list[CRMOrganization]) -> list[DuplicateGroup]:
    buckets: dict[str, list[str]] = {}
    for org in orgs:
        domain = normalize_domain(org.website)
        if not domain:
            continue
        buckets.setdefault(domain, []).append(org.id)
    return [
        DuplicateGroup(entity_type="organization", key=domain, member_ids=ids)
        for domain, ids in buckets.items()
        if len(ids) >= 2
    ]


def group_contacts_by_email(contacts: list[CRMContact]) -> list[DuplicateGroup]:
    buckets: dict[str, list[str]] = {}
    for contact in contacts:
        email = (contact.email or "").strip().lower()
        if not email:
            continue
        buckets.setdefault(email, []).append(contact.id)
    return [
        DuplicateGroup(entity_type="contact", key=email, member_ids=ids)
        for email, ids in buckets.items()
        if len(ids) >= 2
    ]


def is_skipped_pair(member_ids: list[str], skip_pairs: list[dict]) -> bool:
    """A group is skipped entirely if any known false-positive pair from
    config/rules.yaml has both its ids present — known false positives
    (shared mailboxes, ambiguous same-key/different-entity pairs) are data
    the matching logic consults, not a special case buried in the merge
    code, per design notes."""
    id_set = set(member_ids)
    for pair in skip_pairs:
        if pair.get("a") in id_set and pair.get("b") in id_set:
            return True
    return False


def score(counts: RelatedCounts, weights: dict[str, int]) -> int:
    return (
        counts.contacts * weights.get("linked_contacts", 0)
        + counts.deals * weights.get("linked_deals", 0)
        + counts.notes * weights.get("notes", 0)
        + counts.open_activities * weights.get("open_activities", 0)
    )


@dataclass
class ScoredGroup:
    entity_type: str
    key: str
    primary_id: str
    primary_score: int
    absorbed_ids: list[str]


def pick_primary(
    group: DuplicateGroup, counts_by_id: dict[str, RelatedCounts], weights: dict[str, int]
) -> ScoredGroup:
    """Richest member wins — a weighted sum of linked-record counts, the
    same scoring formula for both entity types (see design notes: this was
    independently arrived at twice in the reference system, a signal it's
    a stable rule worth centralizing). Deterministic tiebreak on lowest id
    so a re-run against unchanged data always reaches the same answer."""
    scored = [(member_id, score(counts_by_id[member_id], weights)) for member_id in group.member_ids]
    scored.sort(key=lambda pair: (-pair[1], pair[0]))
    primary_id, primary_score = scored[0]
    absorbed_ids = [member_id for member_id, _ in scored[1:]]
    return ScoredGroup(
        entity_type=group.entity_type,
        key=group.key,
        primary_id=primary_id,
        primary_score=primary_score,
        absorbed_ids=absorbed_ids,
    )
