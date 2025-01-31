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
                    try:
                        entities.append(sensor)
                        new_sensors.append(sensor)
                        existing_entity_ids.add(unique_id)
                    except NordigenAPIError as e:
                        if not account_failed:
                            _LOGGER.warning(
                                "Failed to retrieve account data for account %s: Nordigen API update failed: %s",
                                acct_id, e
                            )
                            account_failed = True  # Ensure only one log per account
                        sensor._attr_available = False  # Mark sensor as unavailable

        if entities:
            _LOGGER.debug("Adding %d new sensors", len(entities))
            async_add_entities(entities)

    _schedule_add_entities()

class NordigenBalanceSensor(SensorEntity):
    """Sensor for each Nordigen bank account balance."""

    def __init__(self, coordinator, config_entry_id, account, balance_type):
        self.coordinator = coordinator
        self._config_entry_id = config_entry_id
        self._account = account
        self._balance_type = balance_type
        self._attr_unique_id = f"{account._account_id}_{balance_type}"
        self._attr_name = f"{account._account_id}_{balance_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account._account_id)},
            name=account.name,
            manufacturer="Nordigen",
            model=f"Status: {account.status}",
            configuration_url="https://ob.nordigen.com/",
        )

    @property
    def native_unit_of_measurement(self):
        for bal in self._account.balances:
            if bal["balanceType"] == self._balance_type:
                return bal.get("currency", "Unknown")
        return None

    @property
    def native_value(self):
        for bal in self._account.balances:
            if bal["balanceType"] == self._balance_type:
                try:
                    return float(bal.get("amount", 0.0))
                except ValueError:
                    return 0.0
        return 0.0

    @property
    def should_poll(self):
        return False

    def update(self):
        pass

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self):
        if self.coordinator.last_update_failed:
            return False
        return any(bal.get("balanceType") for bal in self._account.balances)
