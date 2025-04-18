"""The Proxmox VE integration."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ProxmoxAPI
from .const import DOMAIN, PLATFORMS, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Proxmox VE from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Create API client
    api = ProxmoxAPI(
        host=entry.data["host"],
        port=entry.data.get("port", 8006),
        user=entry.data["username"],
        password=entry.data["password"],
        verify_ssl=entry.data.get("verify_ssl", True),
        realm=entry.data.get("realm", "pam"),
    )
    
    # Verify we can connect to the Proxmox server
    try:
        await hass.async_add_executor_job(api.test_connection)
    except Exception as e:
        _LOGGER.error("Failed to connect to Proxmox VE server: %s", e)
        raise ConfigEntryNotReady from e
    
    # Create update coordinator
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"Proxmox VE {entry.data['host']}",
        update_method=lambda: _async_update_data(hass, api),
        update_interval=timedelta(seconds=UPDATE_INTERVAL),
    )
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Store API client and coordinator
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }
    
    # Set up all platforms using the new async_forward_entry_setups method
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Use the new async_unload_platforms method
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def _async_update_data(hass, api):
    """Update data from Proxmox VE API."""
    try:
        # Get all clusters, nodes, VMs, and storages
        data = {}
        data["nodes"] = await hass.async_add_executor_job(api.get_nodes)
        data["vms"] = await hass.async_add_executor_job(api.get_vms)
        data["storages"] = await hass.async_add_executor_job(api.get_storages)
        return data
    except Exception as e:
        _LOGGER.error("Error updating Proxmox VE data: %s", e)
        raise UpdateFailed(f"Error communicating with API: {e}")
