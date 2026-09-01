from datetime import datetime, timezone

from ..config import DedupRules
from ..crm.base import CRMClient
from ..dedup import ScoredGroup, group_contacts_by_email, group_organizations_by_domain, is_skipped_pair, pick_primary
from ..storage.models import MergeLog


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_merge_log(scored: ScoredGroup) -> MergeLog:
    now = _utcnow()
    return MergeLog(
        entity_type=scored.entity_type,
        group_key=scored.key,
        primary_record_id=scored.primary_id,
        absorbed_record_ids=",".join(scored.absorbed_ids),
        primary_score=scored.primary_score,
        dry_run=True,
        status="dry_run",
        started_at=now,
        finished_at=now,
    )


def discover(client: CRMClient, session, rules: DedupRules) -> list[MergeLog]:
    """Find duplicate groups (organizations by domain, contacts by email)
    and write one MergeLog row per group.

    Always dry-run in this phase — no merge is ever executed here. This
    mirrors the reference system's core governance principle (dry run
    stops before any write, payload/plan fully reviewable first); merge
    EXECUTION is a deliberately separate, later phase, not an --execute
    flag bolted onto this one.
    """
    logs: list[MergeLog] = []

    orgs = client.list_organizations()
    for group in group_organizations_by_domain(orgs):
        if is_skipped_pair(group.member_ids, rules.skip_pairs):
            continue
        counts_by_id = {mid: client.get_organization_related_counts(mid) for mid in group.member_ids}
        logs.append(_to_merge_log(pick_primary(group, counts_by_id, rules.score_weights)))

    contacts = client.list_contacts()
    for group in group_contacts_by_email(contacts):
        if is_skipped_pair(group.member_ids, rules.skip_pairs):
            continue
        counts_by_id = {mid: client.get_contact_related_counts(mid) for mid in group.member_ids}
        logs.append(_to_merge_log(pick_primary(group, counts_by_id, rules.score_weights)))

    for log in logs:
        session.add(log)
    session.commit()
    return logs
