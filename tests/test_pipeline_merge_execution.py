from crmdedup.config import DedupRules
from crmdedup.crm.sandbox_client import SandboxCRMClient
from crmdedup.pipeline.discover import discover
from crmdedup.storage.models import MergeLog

WEIGHTS = {"linked_contacts": 3, "linked_deals": 3, "notes": 1, "open_activities": 2}


def test_execute_true_actually_merges(db_session):
    client = SandboxCRMClient()
    rules = DedupRules(score_weights=WEIGHTS, skip_pairs=[])

    logs = discover(client, db_session, rules, execute=True)

    assert all(not log.dry_run for log in logs)
    assert all(log.status == "merged" for log in logs)
    assert ("organization", "org-1", "org-2") in client.merge_calls
    assert ("contact", "contact-1", "contact-2") in client.merge_calls
    # source records are actually gone from the CRM now
    assert "org-2" not in {o.id for o in client.list_organizations()}
    assert "contact-2" not in {c.id for c in client.list_contacts()}


def test_execute_true_posts_an_audit_note_on_the_primary(db_session):
    client = SandboxCRMClient()
    rules = DedupRules(score_weights=WEIGHTS, skip_pairs=[])

    discover(client, db_session, rules, execute=True)

    org_notes = [n for n in client.notes if n[0] == "organization" and n[1] == "org-1"]
    assert len(org_notes) == 1
    assert "org-2" in org_notes[0][2] or "1 organization" in org_notes[0][2]


def test_execute_false_never_calls_merge_or_add_note(db_session):
    client = SandboxCRMClient()
    rules = DedupRules(score_weights=WEIGHTS, skip_pairs=[])

    discover(client, db_session, rules, execute=False)

    assert client.merge_calls == []
    assert client.notes == []


def test_execute_persists_merged_status_to_db(db_session):
    client = SandboxCRMClient()
    rules = DedupRules(score_weights=WEIGHTS, skip_pairs=[])

    discover(client, db_session, rules, execute=True)

    persisted = db_session.query(MergeLog).all()
    assert len(persisted) == 2
    assert all(log.status == "merged" for log in persisted)
    assert all(not log.dry_run for log in persisted)


def test_a_source_already_gone_records_failed_status_without_crashing(db_session):
    client = SandboxCRMClient()
    rules = DedupRules(score_weights=WEIGHTS, skip_pairs=[])

    # Simulate a race: org-2 is still present when discover() fetches the
    # initial list (so the group is still planned), but has been absorbed
    # by another process by the time the actual merge call happens —
    # exactly the scenario the design notes' "re-verify source still
    # exists" rule guards against. Patching the merge call itself (rather
    # than deleting org-2 up front, which would just remove it from the
    # list and never plan a merge for it at all) is what actually
    # reproduces that race in a single-threaded test.
    real_merge = client.merge_organizations

    def merge_that_fails_for_org_2(primary_id, source_id):
        if source_id == "org-2":
            raise ValueError("source organization org-2 no longer exists — already merged?")
        return real_merge(primary_id, source_id)

    client.merge_organizations = merge_that_fails_for_org_2

    logs = discover(client, db_session, rules, execute=True)

    org_log = next(log for log in logs if log.entity_type == "organization")
    assert org_log.status == "failed"
    assert org_log.absorbed_record_ids == ""
    assert org_log.notes is not None and "org-2" in org_log.notes
    # the contact group is unaffected by the org failure
    contact_log = next(log for log in logs if log.entity_type == "contact")
    assert contact_log.status == "merged"
