from unittest.mock import MagicMock, patch

import pytest

from crmdedup.crm.pipedrive_client import PipedriveClient


@pytest.fixture
def client():
    return PipedriveClient(api_token="TOK123", domain="mycompany")


def test_list_organizations_single_page(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(
            ok=True,
            json=lambda: {
                "success": True,
                "data": [{"id": 1, "name": "Acme", "website": "acme.example"}],
                "additional_data": {"pagination": {"more_items_in_collection": False}},
            },
        )
        orgs = client.list_organizations()

    assert len(orgs) == 1
    assert orgs[0].id == "1"
    assert orgs[0].website == "acme.example"
    assert mock_req.call_count == 1


def test_list_organizations_paginates_across_multiple_pages(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.side_effect = [
            MagicMock(
                ok=True,
                json=lambda: {
                    "success": True,
                    "data": [{"id": 1, "name": "Acme", "website": "acme.example"}],
                    "additional_data": {"pagination": {"more_items_in_collection": True, "next_start": 500}},
                },
            ),
            MagicMock(
                ok=True,
                json=lambda: {
                    "success": True,
                    "data": [{"id": 2, "name": "Beta", "website": "beta.example"}],
                    "additional_data": {"pagination": {"more_items_in_collection": False}},
                },
            ),
        ]
        orgs = client.list_organizations()

    assert [o.id for o in orgs] == ["1", "2"]
    assert mock_req.call_count == 2
    second_call_params = mock_req.call_args_list[1].kwargs["params"]
    assert second_call_params["start"] == 500


def test_list_contacts_picks_primary_email_and_skips_emailless(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(
            ok=True,
            json=lambda: {
                "success": True,
                "data": [
                    {
                        "id": 7,
                        "name": "Jamie Okoye",
                        "email": [
                            {"value": "jamie-old@acme.example", "primary": False},
                            {"value": "jamie@acme.example", "primary": True},
                        ],
                        "org_id": {"value": 1},
                    },
                    {"id": 8, "name": "No Email Person", "email": []},
                ],
                "additional_data": {"pagination": {"more_items_in_collection": False}},
            },
        )
        contacts = client.list_contacts()

    assert len(contacts) == 1
    assert contacts[0].email == "jamie@acme.example"
    assert contacts[0].org_id == "1"


def test_get_organization_related_counts_uses_native_fields_and_notes_pagination(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.side_effect = [
            MagicMock(
                ok=True,
                json=lambda: {
                    "success": True,
                    "data": {
                        "id": 1,
                        "people_count": 4,
                        "open_deals_count": 2,
                        "undone_activities_count": 1,
                    },
                },
            ),
            MagicMock(
                ok=True,
                json=lambda: {"success": True, "data": [], "additional_data": {"pagination": {"total_count": 3}}},
            ),
        ]
        counts = client.get_organization_related_counts("1")

    assert counts.contacts == 4
    assert counts.deals == 2
    assert counts.open_activities == 1
    assert counts.notes == 3
    notes_call_params = mock_req.call_args_list[1].kwargs["params"]
    assert notes_call_params["org_id"] == "1"


def test_get_contact_related_counts_has_zero_contacts_field(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.side_effect = [
            MagicMock(
                ok=True,
                json=lambda: {"success": True, "data": {"open_deals_count": 1, "undone_activities_count": 0}},
            ),
            MagicMock(
                ok=True,
                json=lambda: {"success": True, "data": [], "additional_data": {"pagination": {"total_count": 0}}},
            ),
        ]
        counts = client.get_contact_related_counts("7")

    assert counts.contacts == 0
    assert counts.deals == 1


def test_merge_organizations_request_shape(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(ok=True, json=lambda: {"success": True, "data": {}})
        client.merge_organizations("1", "2")

    call = mock_req.call_args
    assert call.args[0] == "PUT"
    assert call.args[1] == "https://mycompany.pipedrive.com/api/v1/organizations/1/merge"
    assert call.kwargs["json"] == {"merge_with_id": 2}


def test_merge_contacts_request_shape(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(ok=True, json=lambda: {"success": True, "data": {}})
        client.merge_contacts("5", "6")

    call = mock_req.call_args
    assert call.args[1] == "https://mycompany.pipedrive.com/api/v1/persons/5/merge"
    assert call.kwargs["json"] == {"merge_with_id": 6}


def test_add_note_organization_shape(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(ok=True, json=lambda: {"success": True, "data": {}})
        client.add_note("organization", "1", "absorbed 2 contacts")

    call = mock_req.call_args
    assert call.kwargs["json"] == {"content": "absorbed 2 contacts", "org_id": 1}


def test_add_note_contact_shape(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(ok=True, json=lambda: {"success": True, "data": {}})
        client.add_note("contact", "7", "duplicate merged")

    call = mock_req.call_args
    assert call.kwargs["json"] == {"content": "duplicate merged", "person_id": 7}


def test_add_note_unknown_entity_type_raises(client):
    with pytest.raises(ValueError):
        client.add_note("deal", "1", "text")
