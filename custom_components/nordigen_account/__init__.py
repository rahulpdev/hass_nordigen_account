import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import NordigenDataUpdateCoordinator
from .nordigen_wrapper import NordigenWrapper

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Nordigen Account from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    secret_id = entry.data.get("secret_id")
    secret_key = entry.data.get("secret_key")
    requisition_id = entry.data.get("requisition_id")
    refresh_token = entry.data.get("refresh_token")

    # Instantiate the Nordigen API wrapper
    try:
        wrapper = NordigenWrapper(
            secret_id=secret_id,
            secret_key=secret_key,
            requisition_id=requisition_id,
            refresh_token=refresh_token
        )
    except RuntimeError as e:
        _LOGGER.error("Failed to initialize Nordigen wrapper: %s", e)
        return False

    # Create data update coordinator
    coordinator = NordigenDataUpdateCoordinator(hass, wrapper=wrapper)
    await coordinator.async_config_entry_first_refresh()

    # Store them so we can access in other parts (sensors, etc.)
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "wrapper": wrapper,
    }

    # Forward entry setup to platforms (in this case, sensor)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    # Listen for updates to options
    entry.async_on_unload(entry.add_update_listener(update_listener))

    _LOGGER.info("Nordigen Account integration successfully set up.")
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update (if requisition_id or refresh_token changed)."""
    coordinator_data = hass.data[DOMAIN][entry.entry_id]
    if not coordinator_data:
        _LOGGER.error("Coordinator data not found during update.")
        return

    wrapper = coordinator_data["wrapper"]

    new_requisition_id = entry.data.get("requisition_id")
    new_refresh_token = entry.data.get("refresh_token")

    # If the user changed the requisition ID, update the wrapper
    if wrapper.requisition_id != new_requisition_id:
        _LOGGER.info(
            "Updating requisition ID from %s to %s",
            wrapper.requisition_id,
            new_requisition_id
        )
        wrapper.requisition_id = new_requisition_id

    # If user cleared or changed refresh token, set it and re-initialize
    if wrapper.refresh_token != new_refresh_token:
        _LOGGER.info("Updating refresh token.")
        wrapper._refresh_token = new_refresh_token
        try:
            wrapper._initialize_manager()
        except RuntimeError as e:
            _LOGGER.error("Failed to reinitialize Nordigen manager: %s", e)
            return

    # Force the coordinator to refresh
    await coordinator_data["coordinator"].async_request_refresh()
    _LOGGER.info("Nordigen configuration updated successfully.")

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Nordigen integration unloaded successfully.")
    else:
        _LOGGER.error("Failed to unload Nordigen integration.")
    return unload_ok
