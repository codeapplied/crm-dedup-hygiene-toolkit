from crmdedup.config import DedupRules
from crmdedup.crm.sandbox_client import SandboxCRMClient
from crmdedup.pipeline.discover import discover
from crmdedup.storage.models import MergeLog

WEIGHTS = {"linked_contacts": 3, "linked_deals": 3, "notes": 1, "open_activities": 2}


def test_discover_finds_the_seeded_org_and_contact_groups(db_session):
    client = SandboxCRMClient()
    rules = DedupRules(score_weights=WEIGHTS, skip_pairs=[])

    logs = discover(client, db_session, rules)

    entity_types = {log.entity_type for log in logs}
    assert entity_types == {"organization", "contact"}
    org_log = next(log for log in logs if log.entity_type == "organization")
    assert org_log.group_key == "riverside-example.test"
    assert org_log.primary_record_id == "org-1"  # richer counts, per sandbox seed data
    assert org_log.absorbed_record_ids == "org-2"


def test_discover_is_always_dry_run_and_never_calls_merge(db_session):
    client = SandboxCRMClient()
    rules = DedupRules(score_weights=WEIGHTS, skip_pairs=[])

    logs = discover(client, db_session, rules)

    assert all(log.dry_run for log in logs)
    assert all(log.status == "dry_run" for log in logs)
    assert client.merge_calls == []  # discover only plans — never merges


def test_discover_persists_merge_logs_to_the_database(db_session):
    client = SandboxCRMClient()
    rules = DedupRules(score_weights=WEIGHTS, skip_pairs=[])

    discover(client, db_session, rules)

    persisted = db_session.query(MergeLog).all()
    assert len(persisted) == 2  # one org group, one contact group


def test_discover_respects_skip_pairs(db_session):
    client = SandboxCRMClient()
    # org-1/org-2 are the seeded duplicate pair — skip it explicitly.
    rules = DedupRules(score_weights=WEIGHTS, skip_pairs=[{"a": "org-1", "b": "org-2", "reason": "test skip"}])

    logs = discover(client, db_session, rules)

    org_logs = [log for log in logs if log.entity_type == "organization"]
    assert org_logs == []
    contact_logs = [log for log in logs if log.entity_type == "contact"]
    assert len(contact_logs) == 1  # contact group is untouched by the org-only skip pair
