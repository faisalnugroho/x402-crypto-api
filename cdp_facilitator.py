"""Patched HTTPFacilitatorClient that uses GET for /supported (CDP compat)."""
from x402.http.facilitator_client import HTTPFacilitatorClient, _parse_facilitator_response
from x402.http.facilitator_client_base import SupportedResponse

class CDPSupportedHTTPFacilitatorClient(HTTPFacilitatorClient):
    """Override get_supported to use GET (CDP requires GET, not POST)."""
    
    def get_supported(self) -> SupportedResponse:
        with self._get_sync_client() as client:
            response = client.get(
                f"{self._url}/supported",
                headers=self._get_supported_headers(),
            )
            if response.status_code != 200:
                raise ValueError(
                    f"Facilitator get_supported failed ({response.status_code}): {response.text}"
                )
            return _parse_facilitator_response(response, SupportedResponse, "supported")
