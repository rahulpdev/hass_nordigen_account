import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import NordigenDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up Nordigen sensors from a config entry."""
    coordinator: NordigenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # The coordinator.data will be updated list of BankAccount objects
    # each time coordinator refreshes.
    new_sensors = []

    # We won't know all sensors until the first refresh, so let's set up a listener:
    @coordinator.async_add_listener
    def _schedule_add_entities():
        # Each refresh, we check for new accounts or new balances
        entities = []
        existing_entity_ids = {entity.unique_id for entity in new_sensors}

        for account in coordinator.data:
            # "account_id" from the library
            acct_id = account._account_id  # or account_id property if you wrap it

            # For each balance in account.balances
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
                    entities.append(sensor)
                    new_sensors.append(sensor)
                    existing_entity_ids.add(unique_id)

        if entities:
            _LOGGER.debug("Adding %d new sensors", len(entities))
            async_add_entities(entities)

    # Call it once now to add any sensors from the initial data
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
            name=account.name,    # from BankAccount
            manufacturer="Nordigen",
            model=f"Status: {account.status}",  # or just store it
            configuration_url="https://ob.nordigen.com/",  # example
        )

    @property
    def native_unit_of_measurement(self):
        """Return the currency for this balance."""
        # The library sets account.balances[i]["currency"] for each balance,
        # but if each balance might differ, you can store it in the coordinator data.
        # We can try to find the matching balance:
        for bal in self._account.balances:
            if bal["balanceType"] == self._balance_type:
                return bal.get("currency", "Unknown")
        return None

    @property
    def native_value(self):
        """Return the balance amount for this sensor."""
        for bal in self._account.balances:
            if bal["balanceType"] == self._balance_type:
                try:
                    return float(bal.get("amount", 0.0))
                except ValueError:
                    return 0.0
        return 0.0

    @property
    def should_poll(self):
        """Disable polling, we use the DataUpdateCoordinator for updates."""
        return False

    def update(self):
        """No-op: we do not poll inside the entity."""
        pass

    async def async_added_to_hass(self):
        """When entity is added to hass, register for coordinator updates."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self):
        """Entity availability based on coordinator status."""
        if self.coordinator.last_update_failed:
            return False
        return any(bal.get("balanceType") for bal in self._account.balances)
