"""Binary sensors for Proxmox VE."""
import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    CATEGORY_NODE,
    CATEGORY_VM,
    STATUS_RUNNING,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Proxmox VE binary sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    entities = []
    
    # Add VM status sensors
    for vm in coordinator.data.get("vms", []):
        entities.append(
            ProxmoxVMStatusSensor(
                coordinator, 
                vm["id"], 
                config_entry.entry_id
            )
        )
    
    # Add Node status sensors
    for node in coordinator.data.get("nodes", []):
        entities.append(
            ProxmoxNodeStatusSensor(
                coordinator, 
                node["id"], 
                config_entry.entry_id
            )
        )
    
    async_add_entities(entities)


class ProxmoxVMStatusSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for Proxmox VM status."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    
    def __init__(
        self, 
        coordinator: DataUpdateCoordinator, 
        vm_id: str, 
        entry_id: str
    ) -> None:
        """Initialize the sensor."""
        # Explicitly initialize the CoordinatorEntity parent class
        CoordinatorEntity.__init__(self, coordinator)
        self.coordinator = coordinator
        self._vm_id = vm_id
        self._entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_status"
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
    def name(self) -> str:
        """Return the name of the entity."""
        if self._vm_data and self._vm_data.get("name"):
            return f"{self._vm_data['name']} Status"
        return f"VM {self._vm_id} Status"

    @property
    def is_on(self) -> bool:
        """Return true if the VM is running."""
        if not self._vm_data:
            return False
        return self._vm_data.get("status") == STATUS_RUNNING

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        if self.is_on:
            return "mdi:server"
        return "mdi:server-off"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self._vm_data:
            return {}
        
        return {
            "node": self._vm_data.get("node", ""),
            "status": self._vm_data.get("status", "unknown"),
            "vm_id": self._vm_id,
            "device_type": CATEGORY_VM,
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"vm_{self._vm_id}")},
            name=self._vm_data.get("name", f"VM {self._vm_id}") if self._vm_data else f"VM {self._vm_id}",
            manufacturer="Proxmox VE",
            model="Virtual Machine",
            via_device=(DOMAIN, f"node_{self._vm_data.get('node')}" if self._vm_data else None),
        )


class ProxmoxNodeStatusSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for Proxmox Node status."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    
    def __init__(
        self, 
        coordinator: DataUpdateCoordinator, 
        node_id: str, 
        entry_id: str
    ) -> None:
        """Initialize the sensor."""
        # Explicitly initialize the CoordinatorEntity parent class
        CoordinatorEntity.__init__(self, coordinator)
        self.coordinator = coordinator
        self._node_id = node_id
        self._entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_node_{node_id}_status"
        self._node_data = self._get_node_data()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._node_data = self._get_node_data()
        self.async_write_ha_state()

    def _get_node_data(self) -> Optional[Dict[str, Any]]:
        """Get current node data from coordinator."""
        for node in self.coordinator.data.get("nodes", []):
            if node["id"] == self._node_id:
                return node
        return None

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        if self._node_data and self._node_data.get("name"):
            return f"{self._node_data['name']} Status"
        return f"Node {self._node_id} Status"

    @property
    def is_on(self) -> bool:
        """Return true if the node is online."""
        if not self._node_data:
            return False
        return self._node_data.get("status") == "online"

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        if self.is_on:
            return "mdi:server-network"
        return "mdi:server-network-off"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self._node_data:
            return {}
        
        return {
            "node_id": self._node_id,
            "status": self._node_data.get("status", "unknown"),
            "uptime": self._node_data.get("uptime", 0),
            "device_type": CATEGORY_NODE,
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"node_{self._node_id}")},
            name=self._node_data.get("name", f"Node {self._node_id}") if self._node_data else f"Node {self._node_id}",
            manufacturer="Proxmox VE",
            model="Node",
        )
