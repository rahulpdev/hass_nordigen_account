import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.persistent_notification import async_create

from .const import DOMAIN, UPDATE_INTERVAL_HOURS
from .nordigen_wrapper import NordigenWrapper

_LOGGER = logging.getLogger(__name__)

class NordigenDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from Nordigen and store it."""

    def __init__(self, hass: HomeAssistant, wrapper: NordigenWrapper) -> None:
        """
        Initialize the hass coordinator to fetch data from Nordigen API.

        Args:
            wrapper (NordigenWrapper): Small wrapper to manage synchronous Nordigen API calls
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
        )
        self.wrapper = wrapper

    async def _async_update_data(self):
        """Fetch data from Nordigen."""
        try:
            # This will fetch data for all accounts in the wrapper
            await self.hass.async_add_executor_job(self.wrapper.update_all_accounts)
            # Return data that sensors can read: e.g. list of BankAccount objects
            return self.wrapper.accounts

        except RuntimeError as e:
            if "expired" in str(e).lower():
                async_create(
                    self.hass,
                    "Your Nordigen requisition ID has expired. Please update it in the integration settings.",
                    title="Nordigen Integration",
                    notification_id="nordigen_requisition_expired"
                )
            raise UpdateFailed(f"Nordigen API update failed: {e}")

        except Exception as err:
            raise UpdateFailed(f"Error updating from Nordigen: {err}") from err
