import logging
from datetime import timedelta
from typing import Optional, Dict, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.event import async_call_later
from homeassistant.components.persistent_notification import async_create

from .const import DOMAIN, UPDATE_INTERVAL_HOURS
from .nordigen_wrapper import NordigenWrapper, NordigenAPIError

_LOGGER = logging.getLogger(__name__)

class NordigenDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for fetching and managing Nordigen account data in Home Assistant."""

    def __init__(self, hass: HomeAssistant, entry: Dict[str, Any]) -> None:
        """
        Initialize the coordinator and set up defaults.

        Args:
            hass (HomeAssistant): The Home Assistant instance.
            entry (Dict[str, Any]): The configuration entry containing user credentials and requisition data.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
        )
        self.entry: Dict[str, Any] = entry  # Store entry data for async_initialize()
        self.wrapper: Optional[NordigenWrapper] = None  # Initialize as None

    async def async_initialize(self, hass: HomeAssistant) -> None:
        """
        Initialize the Nordigen API wrapper asynchronously.

        Args:
            hass (HomeAssistant): The Home Assistant instance.

        Raises:
            NordigenAPIError: If the API authentication or requisition retrieval fails.
        """
        secret_id: str = self.entry["secret_id"]
        secret_key: str = self.entry["secret_key"]
        requisition_id: str = self.entry["requisition_id"]
        refresh_token: Optional[str] = self.entry.get("refresh_token")

        self.wrapper = await hass.async_add_executor_job(
            NordigenWrapper,
            secret_id,
            secret_key,
            requisition_id,
            refresh_token
        )

    async def _async_update_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch updated account data from Nordigen.

        This method retrieves account balances and handles rate limits, expired requisitions,
        and missing accounts. It schedules retries in case of temporary API failures.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing updated account data, or None if an error occurs.

        Raises:
            UpdateFailed: If there is an issue retrieving data from the Nordigen API.
        """
        _LOGGER.debug("Nordigen is retrieving accounts!")
        try:
            await self.hass.async_add_executor_job(self.wrapper.update_all_accounts)
            _LOGGER.debug("Nordigen retrieved accounts: %s", self.wrapper.accounts)
            return self.wrapper.accounts

        except NordigenAPIError as e:
            _LOGGER.warning("Nordigen API issue encountered: %s", e)

            # Handle Rate Limit (429 Too Many Requests)
            if e.status_code == 429:
                wait_time = int(e.response_body.get("detail", "").split()[-2])  # Extract wait time from API response
                _LOGGER.warning("Rate limit exceeded. Next update in %d seconds.", wait_time)

                # Prevent scheduled updates from triggering before wait_time elapses
                self.update_interval = timedelta(seconds=wait_time)

                async_call_later(
                    self.hass,
                    wait_time,
                    lambda _: self.async_request_refresh()
                )

                return None  # Ensures HA does not retry immediately

            # Handle Expired Requisition
            elif e.status_code == 428:
                message = "Your Nordigen requisition ID has expired. Please update it in the integration settings."

                async_create(
                    self.hass,
                    message,
                    title="Nordigen Integration",
                    notification_id="nordigen_requisition_expired"
                )

                # Fire an event so Home Assistant automations can use the message
                self.hass.bus.async_fire(
                    "nordigen_requisition_expired",
                    {
                        "entry_id": self.entry.entry_id,
                        "message": message
                    }
                )

            # Handle No Accounts Found
            elif e.status_code == 410:
                _LOGGER.warning("No accounts found for requisition ID. Ensure bank authorization is complete.")

            raise UpdateFailed(f"Nordigen API update failed: {e}")

        except Exception:
            _LOGGER.exception("Unexpected error updating Nordigen data")
            raise UpdateFailed("Error updating from Nordigen")
