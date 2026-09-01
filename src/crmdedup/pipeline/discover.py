from datetime import datetime, timezone

from ..config import DedupRules
from ..crm.base import CRMClient, RelatedCounts
from ..dedup import ScoredGroup, group_contacts_by_email, group_organizations_by_domain, is_skipped_pair, pick_primary
from ..storage.models import MergeLog


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _execute_group(client: CRMClient, scored: ScoredGroup, counts_by_id: dict[str, RelatedCounts]) -> MergeLog:
    """Actually perform the merge for one duplicate group.

    Re-verification that a source record still exists (guarding against a
    merge already applied in an earlier partial run) happens implicitly at
    the merge call itself, not as a separate pre-check: both CRMClient
    implementations raise when the source is already gone (the sandbox
    explicitly; a real backend via its own API error), so a single
    try/except per absorbed id IS the re-verification checkpoint — not a
    redundant extra one. A failure on one member of a group never aborts
    the rest of that group.
    """
    started = _utcnow()
    merge_fn = client.merge_organizations if scored.entity_type == "organization" else client.merge_contacts

    absorbed_ok: list[str] = []
    absorbed_failed: list[tuple[str, str]] = []
    for absorbed_id in scored.absorbed_ids:
        try:
            merge_fn(scored.primary_id, absorbed_id)
            absorbed_ok.append(absorbed_id)
        except Exception as exc:  # noqa: BLE001 - both client backends raise different types; any failure here is a per-record skip, not fatal
            absorbed_failed.append((absorbed_id, str(exc)))

    if absorbed_ok:
        note_lines = [f"crmdedup: merged {len(absorbed_ok)} {scored.entity_type}(s) into this record."]
        for member_id in absorbed_ok:
            counts = counts_by_id[member_id]
            note_lines.append(
                f"- absorbed {member_id}: {counts.contacts} contacts, {counts.deals} deals, "
                f"{counts.notes} notes, {counts.open_activities} open activities"
            )
        client.add_note(scored.entity_type, scored.primary_id, "\n".join(note_lines))

    if absorbed_failed and not absorbed_ok:
        status = "failed"
    elif absorbed_failed:
        status = "partial"
    else:
        status = "merged"

    return MergeLog(
        entity_type=scored.entity_type,
        group_key=scored.key,
        primary_record_id=scored.primary_id,
        absorbed_record_ids=",".join(absorbed_ok),
        primary_score=scored.primary_score,
        dry_run=False,
        status=status,
        started_at=started,
        finished_at=_utcnow(),
        notes="; ".join(f"{mid} failed: {reason}" for mid, reason in absorbed_failed) or None,
    )


def _plan_group(scored: ScoredGroup) -> MergeLog:
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


def discover(client: CRMClient, session, rules: DedupRules, execute: bool = False) -> list[MergeLog]:
    """Find duplicate groups (organizations by domain, contacts by email)
    and write one MergeLog row per group.

    Dry run by default (execute=False): plans every merge and writes a
    'dry_run' row, but calls nothing mutating on the CRM — the exact same
    grouping/scoring the reference system's own scripts print as a
    reviewable diff before anyone commits to --execute. Pass execute=True
    to actually perform each planned merge and post the audit note.
    """
    logs: list[MergeLog] = []

    orgs = client.list_organizations()
    for group in group_organizations_by_domain(orgs):
        if is_skipped_pair(group.member_ids, rules.skip_pairs):
            continue
        counts_by_id = {mid: client.get_organization_related_counts(mid) for mid in group.member_ids}
        scored = pick_primary(group, counts_by_id, rules.score_weights)
        logs.append(_execute_group(client, scored, counts_by_id) if execute else _plan_group(scored))

    contacts = client.list_contacts()
    for group in group_contacts_by_email(contacts):
        if is_skipped_pair(group.member_ids, rules.skip_pairs):
            continue
        counts_by_id = {mid: client.get_contact_related_counts(mid) for mid in group.member_ids}
        scored = pick_primary(group, counts_by_id, rules.score_weights)
        logs.append(_execute_group(client, scored, counts_by_id) if execute else _plan_group(scored))

    for log in logs:
        session.add(log)
    session.commit()
    return logs
