import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.persistent_notification import async_create

from .const import DOMAIN, UPDATE_INTERVAL_HOURS
from .nordigen_wrapper import NordigenWrapper, NordigenAPIError

_LOGGER = logging.getLogger(__name__)


class NordigenDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from Nordigen and store it."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.entry = entry
        self.wrapper = NordigenWrapper(
            secret_id=entry.data["secret_id"],
            secret_key=entry.data["secret_key"],
            requisition_id=entry.data["requisition_id"],
            refresh_token=entry.data["refresh_token"]
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
        )

    async def _async_update_data(self):
        try:
            await self.hass.async_add_executor_job(self.wrapper.update_all_accounts)
            return self.wrapper.accounts

        except NordigenAPIError as e:
            _LOGGER.warning("Nordigen API issue encountered: %s", e)

            # **Handle Expired Requisition**
            if e.status_code == 428:  # Expired Requisition ID
                async_create(
                    self.hass,
                    "Your Nordigen requisition ID has expired. Please update it in the integration settings.",
                    title="Nordigen Integration",
                    notification_id="nordigen_requisition_expired"
                )

            # **Handle No Accounts Found**
            elif e.status_code == 410:  # No Accounts Found
                _LOGGER.warning("No accounts found for requisition ID. Ensure bank authorization is complete.")

            raise UpdateFailed(f"Nordigen API update failed: {e}")

        except Exception:
            _LOGGER.exception("Unexpected error updating Nordigen data")
            raise UpdateFailed("Error updating from Nordigen")
