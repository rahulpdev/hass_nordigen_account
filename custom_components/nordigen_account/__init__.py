import logging
from typing import Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import NordigenDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up the Nordigen Account integration.

    This method initializes the integration by creating and storing the data coordinator,
    ensuring platform setups are forwarded, and triggering the first data refresh.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry containing user-defined settings.

    Returns:
        bool: True if the integration is successfully set up.
    """
    hass.data.setdefault(DOMAIN, {})

    coordinator: NordigenDataUpdateCoordinator = NordigenDataUpdateCoordinator(hass, entry)
    await coordinator.async_initialize(hass)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id]: Dict[str, NordigenDataUpdateCoordinator] = {"coordinator": coordinator}

    _LOGGER.info("Setting up Nordigen sensors...")
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    _LOGGER.info("Nordigen Account integration successfully set up.")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload the Nordigen Account integration.

    Removes the integration’s platforms and cleans up resources when the config entry is removed.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry being unloaded.

    Returns:
        bool: True if the integration is successfully unloaded.
    """
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])
