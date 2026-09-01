"""Real Pipedrive CRM client — implements CRMClient against Pipedrive's
REST API v1, following the same shape already proven in the sibling
data-enrichment-system repo's crm/pipedrive_client.py.

Field-mapping notes, stated honestly rather than assumed:
- Organization related counts use Pipedrive's own native summary fields —
  `people_count`, `open_deals_count`, `undone_activities_count` (the
  closest real equivalent to "open activities"). There is no native
  `notes_count` field on the organization object in API v1, so note count
  is fetched via `GET /notes?org_id=...&limit=1` and read from
  `additional_data.pagination.total_count` rather than a fabricated field.
- Person (Contact) related counts reuse the same three fields where they
  exist on a person object (`open_deals_count`, `undone_activities_count`)
  and the same notes-pagination-count trick for notes. A Contact has no
  meaningful "linked contacts" count of its own, so `RelatedCounts.contacts`
  stays 0 for contacts — it's only meaningful for organizations.
- Both organizations and persons have a native merge endpoint
  (`PUT /organizations/{id}/merge`, `PUT /persons/{id}/merge`) — used
  directly rather than a manual field-by-field consolidation.

No live Pipedrive account was available to test this against in this
session — verified via mocked-HTTP-shape tests only (see
tests/test_pipedrive_client.py), the same honest-limitation pattern used
throughout the sibling repos' own integrations.
"""

import requests

from .base import CRMClient, CRMContact, CRMOrganization, RelatedCounts


class PipedriveError(Exception):
    pass


class PipedriveClient(CRMClient):
    name = "pipedrive"

    def __init__(self, api_token: str, domain: str, timeout: int = 30) -> None:
        self.api_token = api_token
        self.base_url = f"https://{domain}.pipedrive.com/api/v1"
        self.timeout = timeout
        self.session = requests.Session()

    def _request(self, method: str, path: str, *, params: dict | None = None, json: dict | None = None) -> dict:
        params = dict(params or {})
        params["api_token"] = self.api_token
        response = self.session.request(
            method, f"{self.base_url}{path}", params=params, json=json, timeout=self.timeout
        )
        if not response.ok:
            raise PipedriveError(f"{method} {path} failed: {response.status_code} {response.text}")
        data = response.json()
        if not data.get("success", True):
            raise PipedriveError(f"{method} {path} returned success=false: {data}")
        return data

    def _paginate(self, path: str, params: dict | None = None) -> list[dict]:
        items: list[dict] = []
        start = 0
        limit = 500
        while True:
            page_params = dict(params or {})
            page_params.update({"start": start, "limit": limit})
            payload = self._request("GET", path, params=page_params)
            page_items = payload.get("data") or []
            items.extend(page_items)
            pagination = (payload.get("additional_data") or {}).get("pagination") or {}
            if not pagination.get("more_items_in_collection"):
                break
            start = pagination.get("next_start", start + limit)
        return items

    def _notes_count(self, *, org_id: str | None = None, person_id: str | None = None) -> int:
        params: dict = {"limit": 1}
        if org_id is not None:
            params["org_id"] = org_id
        if person_id is not None:
            params["person_id"] = person_id
        payload = self._request("GET", "/notes", params=params)
        pagination = (payload.get("additional_data") or {}).get("pagination") or {}
        return pagination.get("total_count", 0) or 0

    def list_organizations(self) -> list[CRMOrganization]:
        raw = self._paginate("/organizations")
        return [
            CRMOrganization(id=str(org["id"]), name=org.get("name", ""), website=org.get("website"))
            for org in raw
        ]

    def list_contacts(self) -> list[CRMContact]:
        raw = self._paginate("/persons")
        contacts = []
        for person in raw:
            emails = person.get("email") or []
            primary_email = next((e["value"] for e in emails if e.get("primary")), None) or (
                emails[0]["value"] if emails else None
            )
            if not primary_email:
                continue
            org = person.get("org_id")
            org_id = str(org["value"]) if isinstance(org, dict) and org.get("value") is not None else None
            contacts.append(
                CRMContact(id=str(person["id"]), email=primary_email, name=person.get("name"), org_id=org_id)
            )
        return contacts

    def get_organization_related_counts(self, org_id: str) -> RelatedCounts:
        payload = self._request("GET", f"/organizations/{org_id}")
        org = payload.get("data") or {}
        return RelatedCounts(
            contacts=org.get("people_count") or 0,
            deals=org.get("open_deals_count") or 0,
            notes=self._notes_count(org_id=org_id),
            open_activities=org.get("undone_activities_count") or 0,
        )

    def get_contact_related_counts(self, contact_id: str) -> RelatedCounts:
        payload = self._request("GET", f"/persons/{contact_id}")
        person = payload.get("data") or {}
        return RelatedCounts(
            contacts=0,
            deals=person.get("open_deals_count") or 0,
            notes=self._notes_count(person_id=contact_id),
            open_activities=person.get("undone_activities_count") or 0,
        )

    def merge_organizations(self, primary_id: str, source_id: str) -> None:
        self._request("PUT", f"/organizations/{primary_id}/merge", json={"merge_with_id": int(source_id)})

    def merge_contacts(self, primary_id: str, source_id: str) -> None:
        self._request("PUT", f"/persons/{primary_id}/merge", json={"merge_with_id": int(source_id)})

    def add_note(self, entity_type: str, entity_id: str, text: str) -> None:
        payload = {"content": text}
        if entity_type == "organization":
            payload["org_id"] = int(entity_id)
        elif entity_type == "contact":
            payload["person_id"] = int(entity_id)
        else:
            raise ValueError(f"unknown entity_type: {entity_type}")
        self._request("POST", "/notes", json=payload)
