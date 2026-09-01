from ..config import Settings
from .base import CRMClient
from .pipedrive_client import PipedriveClient
from .sandbox_client import SandboxCRMClient


def get_crm_client(settings: Settings) -> CRMClient:
    """Real Pipedrive backend if credentials are configured, otherwise the
    zero-network sandbox demo — same selection rule as the sibling
    data-enrichment-system repo."""
    if settings.pipedrive_api_token and settings.pipedrive_domain:
        return PipedriveClient(api_token=settings.pipedrive_api_token, domain=settings.pipedrive_domain)
    return SandboxCRMClient()
