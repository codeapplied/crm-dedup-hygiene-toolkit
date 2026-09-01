import pytest

from crmdedup.crm.sandbox_client import SandboxCRMClient


@pytest.fixture
def client():
    return SandboxCRMClient()


def test_seeded_data_has_a_real_duplicate_group_by_domain(client):
    orgs = client.list_organizations()
    domains = [o.website for o in orgs]
    assert domains.count("riverside-example.test") == 2
    assert "northgate-example.test" in domains


def test_seeded_data_has_a_real_duplicate_pair_by_email(client):
    contacts = client.list_contacts()
    emails = [c.email for c in contacts]
    assert emails.count("j.smith@riverside-example.test") == 2


def test_related_counts_are_uneven_so_scoring_has_something_to_pick(client):
    richer = client.get_organization_related_counts("org-1")
    poorer = client.get_organization_related_counts("org-2")
    assert (richer.contacts + richer.deals + richer.notes + richer.open_activities) > (
        poorer.contacts + poorer.deals + poorer.notes + poorer.open_activities
    )


def test_merge_organizations_removes_source_and_records_the_call(client):
    client.merge_organizations("org-1", "org-2")
    assert "org-2" not in {o.id for o in client.list_organizations()}
    assert client.merge_calls == [("organization", "org-1", "org-2")]


def test_merge_already_merged_source_raises(client):
    client.merge_organizations("org-1", "org-2")
    with pytest.raises(ValueError):
        client.merge_organizations("org-1", "org-2")


def test_merge_contacts_removes_source(client):
    client.merge_contacts("contact-1", "contact-2")
    assert "contact-2" not in {c.id for c in client.list_contacts()}


def test_add_note_is_recorded(client):
    client.add_note("organization", "org-1", "absorbed 1 contact, 0 deals")
    assert client.notes == [("organization", "org-1", "absorbed 1 contact, 0 deals")]
