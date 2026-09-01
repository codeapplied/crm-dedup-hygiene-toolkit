from crmdedup.crm.base import CRMContact, CRMOrganization, RelatedCounts
from crmdedup.dedup import (
    DuplicateGroup,
    group_contacts_by_email,
    group_organizations_by_domain,
    is_skipped_pair,
    normalize_domain,
    pick_primary,
    score,
)


def test_normalize_domain_strips_protocol_www_path_query_port():
    assert normalize_domain("https://www.Acme.com/about?ref=1") == "acme.com"
    assert normalize_domain("http://acme.com:8080") == "acme.com"
    assert normalize_domain("acme.com") == "acme.com"


def test_normalize_domain_handles_none_and_empty():
    assert normalize_domain(None) is None
    assert normalize_domain("") is None


def test_group_organizations_by_domain_only_returns_groups_of_2_plus():
    orgs = [
        CRMOrganization(id="1", name="A", website="acme.com"),
        CRMOrganization(id="2", name="A Inc", website="www.acme.com"),
        CRMOrganization(id="3", name="Solo", website="solo.com"),
        CRMOrganization(id="4", name="No site", website=None),
    ]
    groups = group_organizations_by_domain(orgs)
    assert len(groups) == 1
    assert groups[0].key == "acme.com"
    assert set(groups[0].member_ids) == {"1", "2"}


def test_group_contacts_by_email_is_case_insensitive():
    contacts = [
        CRMContact(id="a", email="Jamie@Acme.com", name="Jamie", org_id=None),
        CRMContact(id="b", email="jamie@acme.com", name="Jamie O.", org_id=None),
        CRMContact(id="c", email="other@acme.com", name="Other", org_id=None),
    ]
    groups = group_contacts_by_email(contacts)
    assert len(groups) == 1
    assert set(groups[0].member_ids) == {"a", "b"}


def test_is_skipped_pair_true_when_both_ids_present():
    assert is_skipped_pair(["1", "2", "3"], [{"a": "1", "b": "2", "reason": "shared mailbox"}])


def test_is_skipped_pair_false_when_only_one_id_present():
    assert not is_skipped_pair(["1", "3"], [{"a": "1", "b": "2"}])


def test_score_is_a_weighted_sum():
    counts = RelatedCounts(contacts=2, deals=1, notes=3, open_activities=1)
    weights = {"linked_contacts": 3, "linked_deals": 3, "notes": 1, "open_activities": 2}
    assert score(counts, weights) == 2 * 3 + 1 * 3 + 3 * 1 + 1 * 2


def test_score_missing_weight_defaults_to_zero():
    counts = RelatedCounts(contacts=5)
    assert score(counts, {}) == 0


def test_pick_primary_richest_wins():
    group = DuplicateGroup(entity_type="organization", key="acme.com", member_ids=["1", "2"])
    counts_by_id = {
        "1": RelatedCounts(contacts=1, deals=0, notes=1, open_activities=0),
        "2": RelatedCounts(contacts=1, deals=2, notes=3, open_activities=1),
    }
    weights = {"linked_contacts": 3, "linked_deals": 3, "notes": 1, "open_activities": 2}
    result = pick_primary(group, counts_by_id, weights)
    assert result.primary_id == "2"
    assert result.absorbed_ids == ["1"]
    assert result.primary_score == 1 * 3 + 2 * 3 + 3 * 1 + 1 * 2


def test_pick_primary_tiebreak_is_deterministic_lowest_id():
    group = DuplicateGroup(entity_type="contact", key="j@acme.com", member_ids=["b", "a"])
    counts_by_id = {"a": RelatedCounts(), "b": RelatedCounts()}
    result = pick_primary(group, counts_by_id, {})
    assert result.primary_id == "a"
    assert result.absorbed_ids == ["b"]
