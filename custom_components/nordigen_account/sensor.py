import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import NordigenDataUpdateCoordinator
from .nordigen_wrapper import NordigenAPIError

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up Nordigen sensors from a config entry."""
    coordinator: NordigenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    new_sensors = []

    @coordinator.async_add_listener
    def _schedule_add_entities():
        entities = []
        existing_entity_ids = {entity.unique_id for entity in new_sensors}

        for account in coordinator.data:
            _LOGGER.debug("Adding sensor for account: %s", account._account_id)
            acct_id = account._account_id
            account_failed = False  # Track if this account has already logged an error

            for bal in account.balances:
                balance_type = bal.get("balanceType", "Unknown")
                unique_id = f"{acct_id}_{balance_type}"

                if unique_id not in existing_entity_ids:
                    sensor = NordigenBalanceSensor(
                        coordinator,
                        entry.entry_id,
                        account,
                        balance_type
                    )
