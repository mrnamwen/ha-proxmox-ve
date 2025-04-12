"""Support for tracking Proxmox VE VMs."""
import logging
from typing import Any, Dict, List, Optional, Set

from homeassistant.components.device_tracker import SOURCE_TYPE_ROUTER
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, CATEGORY_VM, STATUS_RUNNING

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Proxmox VE device trackers."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    entities = []
    
    # Add VM trackers
    for vm in coordinator.data.get("vms", []):
        entities.append(ProxmoxVMTracker(coordinator, vm["id"], config_entry.entry_id))
    
    async_add_entities(entities)


class ProxmoxVMTracker(CoordinatorEntity, ScannerEntity):
    """Representation of a Proxmox VM tracker."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, vm_id: str, entry_id: str
    ) -> None:
        """Initialize the VM tracker."""
        super().__init__(coordinator)
        self._vm_id = vm_id
        self._entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_tracker"
        self._vm_data = self._get_vm_data()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._vm_data = self._get_vm_data()
        self.async_write_ha_state()

    def _get_vm_data(self) -> Optional[Dict[str, Any]]:
        """Get current VM data from coordinator."""
        for vm in self.coordinator.data.get("vms", []):
            if str(vm["id"]) == str(self._vm_id):
                return vm
        return None

    @property
    def source_type(self) -> str:
        """Return the source type of the device."""
        return SOURCE_TYPE_ROUTER

    @property
    def name(self) -> str:
        """Return the name of the device."""
        if self._vm_data and self._vm_data.get("name"):
            return f"{self._vm_data['name']}"
        return f"VM {self._vm_id}"

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected."""
        if not self._vm_data:
            return False
        return self._vm_data.get("status") == STATUS_RUNNING

    @property
    def icon(self) -> str:
        """Return the icon of the device."""
        if self.is_connected:
            return "mdi:server"
        return "mdi:server-off"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self._vm_data:
            return {}
        
        attrs = {
            "node": self._vm_data.get("node", ""),
            "status": self._vm_data.get("status", "unknown"),
            "vm_id": self._vm_id,
            "device_type": CATEGORY_VM,
        }
        
        if self._vm_data.get("cpu"):
            attrs["cpu_usage"] = self._vm_data["cpu"].get("used", 0)
            attrs["cpu_cores"] = self._vm_data["cpu"].get("total", 0)
        
        if self._vm_data.get("memory"):
            attrs["memory_used"] = self._vm_data["memory"].get("used", 0)
            attrs["memory_total"] = self._vm_data["memory"].get("total", 0)
        
        if self._vm_data.get("disk"):
            attrs["disk_total"] = self._vm_data["disk"].get("total", 0)
        
        if self._vm_data.get("ip_address"):
            attrs["ip_address"] = self._vm_data["ip_address"]
        
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"vm_{self._vm_id}")},
            name=self.name,
            manufacturer="Proxmox VE",
            model="Virtual Machine",
            via_device=(DOMAIN, f"node_{self._vm_data.get('node')}" if self._vm_data else None),
        )
