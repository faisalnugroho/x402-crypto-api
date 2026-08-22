"""Patched HTTPFacilitatorClient for CDP compatibility.

Fixes:
1. get_supported uses GET (CDP requires GET, not POST)
2. verify/settle send payload.accepted as paymentRequirements
   (CDP expects the selected payment option with scheme/network/asset/amount/payTo,
   not the full PaymentRequirements object)
"""
import logging
from typing import Any
from x402.http.facilitator_client import HTTPFacilitatorClient, _parse_facilitator_response
from x402.http.facilitator_client_base import SupportedResponse, VerifyResponse, SettleResponse
from x402.schemas import PaymentPayload, PaymentPayloadV1, PaymentRequirements, PaymentRequirementsV1

log = logging.getLogger("cdp-facilitator")


class CDPSupportedHTTPFacilitatorClient(HTTPFacilitatorClient):
    """HTTPFacilitatorClient patched for CDP Facilitator compatibility."""

    def get_supported(self) -> SupportedResponse:
        """Override: CDP requires GET for /supported (not POST)."""
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

    def _cdp_requirements_dict(self, payload, requirements) -> dict[str, Any]:
        """Extract the correct paymentRequirements dict for CDP.

        CDP expects paymentRequirements to be the selected payment option
        (with scheme, network, asset, amount, payTo), which is payload.accepted.
        The full PaymentRequirements object (with x402Version, error, resource, accepts[])
        is NOT what CDP wants.
        """
        # payload.accepted is the PaymentOption that was selected by the buyer
        if hasattr(payload, 'accepted') and payload.accepted is not None:
            return payload.accepted.model_dump(by_alias=True, exclude_none=True)
        # Fallback: try to extract from requirements if it has accepts
        if hasattr(requirements, 'accepts') and requirements.accepts:
            return requirements.accepts[0].model_dump(by_alias=True, exclude_none=True)
        # Last resort: use requirements as-is
        return requirements.model_dump(by_alias=True, exclude_none=True)

    async def verify(
        self,
        payload: PaymentPayload | PaymentPayloadV1,
        requirements: PaymentRequirements | PaymentRequirementsV1,
    ) -> VerifyResponse:
        """Override: send payload.accepted as paymentRequirements for CDP."""
        req_dict = self._cdp_requirements_dict(payload, requirements)
        try:
            return await self._verify_http(
                payload.x402_version,
                payload.model_dump(by_alias=True, exclude_none=True),
                req_dict,
            )
        except Exception as e:
            log.error(f"CDP verify FAILED: {e}")
            raise

    async def settle(
        self,
        payload: PaymentPayload | PaymentPayloadV1,
        requirements: PaymentRequirements | PaymentRequirementsV1,
    ) -> SettleResponse:
        """Override: send payload.accepted as paymentRequirements for CDP."""
        return await self._settle_http(
            payload.x402_version,
            payload.model_dump(by_alias=True, exclude_none=True),
            self._cdp_requirements_dict(payload, requirements),
        )
