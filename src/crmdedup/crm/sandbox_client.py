from .base import CRMClient, CRMContact, CRMOrganization, RelatedCounts


class SandboxCRMClient(CRMClient):
    """Default demo backend: an in-memory fake CRM, not a real Pipedrive
    account. Zero network calls, zero credentials. Pre-seeded with two
    genuine duplicate groups (one organization pair sharing a domain, one
    contact pair sharing an email) plus a couple of unique, non-duplicate
    records — so 'crmdedup discover' has real groups to find and a real
    non-match to correctly ignore, not just an empty dataset.
    """

    name = "sandbox"

    def __init__(self) -> None:
        self._orgs: dict[str, CRMOrganization] = {
            "org-1": CRMOrganization(id="org-1", name="Riverside Developments Inc.", website="riverside-example.test"),
            "org-2": CRMOrganization(id="org-2", name="Riverside Developments", website="riverside-example.test"),
            "org-3": CRMOrganization(id="org-3", name="Northgate Holdings", website="northgate-example.test"),
        }
        self._contacts: dict[str, CRMContact] = {
            "contact-1": CRMContact(id="contact-1", email="j.smith@riverside-example.test", name="J. Smith", org_id="org-1"),
            "contact-2": CRMContact(id="contact-2", email="j.smith@riverside-example.test", name="Jane Smith", org_id="org-2"),
            "contact-3": CRMContact(id="contact-3", email="contact@northgate-example.test", name="N. Holder", org_id="org-3"),
        }
        # Deliberately uneven counts, so score-based primary selection
        # (richest wins) has something real to choose between rather than
        # a tie needing a tiebreak rule not yet built.
        self._org_counts: dict[str, RelatedCounts] = {
            "org-1": RelatedCounts(contacts=1, deals=2, notes=3, open_activities=1),
            "org-2": RelatedCounts(contacts=1, deals=0, notes=1, open_activities=0),
            "org-3": RelatedCounts(contacts=1, deals=1, notes=0, open_activities=0),
        }
        self._contact_counts: dict[str, RelatedCounts] = {
            "contact-1": RelatedCounts(deals=2, notes=2, open_activities=1),
            "contact-2": RelatedCounts(deals=0, notes=0, open_activities=0),
            "contact-3": RelatedCounts(deals=1, notes=0, open_activities=0),
        }
        self.merge_calls: list[tuple[str, str, str]] = []
        self.notes: list[tuple[str, str, str]] = []

    def list_organizations(self) -> list[CRMOrganization]:
        return list(self._orgs.values())

    def list_contacts(self) -> list[CRMContact]:
        return list(self._contacts.values())

    def get_organization_related_counts(self, org_id: str) -> RelatedCounts:
        return self._org_counts.get(org_id, RelatedCounts())

    def get_contact_related_counts(self, contact_id: str) -> RelatedCounts:
        return self._contact_counts.get(contact_id, RelatedCounts())

    def merge_organizations(self, primary_id: str, source_id: str) -> None:
        if source_id not in self._orgs:
            raise ValueError(f"source organization {source_id} no longer exists — already merged?")
        self.merge_calls.append(("organization", primary_id, source_id))
        del self._orgs[source_id]

    def merge_contacts(self, primary_id: str, source_id: str) -> None:
        if source_id not in self._contacts:
            raise ValueError(f"source contact {source_id} no longer exists — already merged?")
        self.merge_calls.append(("contact", primary_id, source_id))
        del self._contacts[source_id]

    def add_note(self, entity_type: str, entity_id: str, text: str) -> None:
        self.notes.append((entity_type, entity_id, text))
