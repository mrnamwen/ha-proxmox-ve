"""Sensors for Proxmox VE."""
import logging
from typing import Any, Dict, Optional, Union, cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfInformation,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
# Remove import that doesn't exist

from .const import (
    DOMAIN,
    CATEGORY_NODE,
    CATEGORY_STORAGE,
    CATEGORY_VM,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Proxmox VE sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    entities = []
    
    # Add VM sensors
    for vm in coordinator.data.get("vms", []):
        vm_id = vm["id"]
        # CPU sensor
        entities.append(
            ProxmoxVMCpuSensor(coordinator, vm_id, config_entry.entry_id)
        )
        # Memory sensor
        entities.append(
            ProxmoxVMMemorySensor(coordinator, vm_id, config_entry.entry_id)
        )
        # Disk sensor
        entities.append(
            ProxmoxVMDiskSensor(coordinator, vm_id, config_entry.entry_id)
        )
        # IP Address sensor (if available)
        if vm.get("ip_address"):
            entities.append(
                ProxmoxVMIpSensor(coordinator, vm_id, config_entry.entry_id)
            )
    
    # Add Node sensors
    for node in coordinator.data.get("nodes", []):
        node_id = node["id"]
        # CPU sensor
        entities.append(
            ProxmoxNodeCpuSensor(coordinator, node_id, config_entry.entry_id)
        )
        # Memory sensor
        entities.append(
            ProxmoxNodeMemorySensor(coordinator, node_id, config_entry.entry_id)
        )
        # Disk sensor
        entities.append(
            ProxmoxNodeDiskSensor(coordinator, node_id, config_entry.entry_id)
        )
    
    # Add Storage sensors
    for storage in coordinator.data.get("storages", []):
        storage_id = storage["id"]
        node_id = storage["node"]
        entities.append(
            ProxmoxStorageSensor(coordinator, storage_id, node_id, config_entry.entry_id)
        )
    
    async_add_entities(entities)


class ProxmoxSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Proxmox VE sensors."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, unique_id: str, name: str
    ) -> None:
        """Initialize the sensor."""
        # Explicitly initialize the CoordinatorEntity parent class
        CoordinatorEntity.__init__(self, coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._state: Any = None
        self._available = True


class ProxmoxVMCpuSensor(ProxmoxSensorBase):
    """Sensor for Proxmox VM CPU usage."""

    _attr_device_class = "cpu"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    
    def __init__(
        self, coordinator: DataUpdateCoordinator, vm_id: str, entry_id: str
    ) -> None:
        """Initialize the sensor."""
        self._vm_id = vm_id
        self._entry_id = entry_id
        self._vm_data = self._get_vm_data()
        
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_cpu"
        name = f"{self._vm_data.get('name', f'VM {vm_id}')} CPU" if self._vm_data else f"VM {vm_id} CPU"
        
        super().__init__(coordinator, unique_id, name)
        self._update_state()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._vm_data = self._get_vm_data()
        self._update_state()
        self.async_write_ha_state()

    def _get_vm_data(self) -> Optional[Dict[str, Any]]:
        """Get current VM data from coordinator."""
        for vm in self.coordinator.data.get("vms", []):
            if str(vm["id"]) == str(self._vm_id):
                return vm
        return None

    def _update_state(self) -> None:
        """Update the state from the data."""
        if not self._vm_data or not self._vm_data.get("cpu"):
            self._available = False
            return
        
        cpu_data = self._vm_data["cpu"]
        self._state = round(cpu_data.get("used", 0) * 100, 2)
        self._available = True

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self._available:
            return None
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = {
            "device_type": CATEGORY_VM,
            "vm_id": self._vm_id,
        }
        
        if self._vm_data and self._vm_data.get("cpu"):
            attrs["cores"] = self._vm_data["cpu"].get("total", 0)
        
        return attrs

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


class ProxmoxVMMemorySensor(ProxmoxSensorBase):
    """Sensor for Proxmox VM memory usage."""

    _attr_device_class = "memory"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    
    def __init__(
        self, coordinator: DataUpdateCoordinator, vm_id: str, entry_id: str
    ) -> None:
        """Initialize the sensor."""
        self._vm_id = vm_id
        self._entry_id = entry_id
        self._vm_data = self._get_vm_data()
        
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_memory"
        name = f"{self._vm_data.get('name', f'VM {vm_id}')} Memory" if self._vm_data else f"VM {vm_id} Memory"
        
        super().__init__(coordinator, unique_id, name)
        self._update_state()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._vm_data = self._get_vm_data()
        self._update_state()
        self.async_write_ha_state()

    def _get_vm_data(self) -> Optional[Dict[str, Any]]:
        """Get current VM data from coordinator."""
        for vm in self.coordinator.data.get("vms", []):
            if str(vm["id"]) == str(self._vm_id):
                return vm
        return None

    def _update_state(self) -> None:
        """Update the state from the data."""
        if not self._vm_data or not self._vm_data.get("memory"):
            self._available = False
            return
        
        memory_data = self._vm_data["memory"]
        self._state = memory_data.get("used", 0)
        self._available = True

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self._available:
            return None
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = {
            "device_type": CATEGORY_VM,
            "vm_id": self._vm_id,
        }
        
        if self._vm_data and self._vm_data.get("memory"):
            attrs["total_memory"] = self._vm_data["memory"].get("total", 0)
            if self._state is not None and self._vm_data["memory"].get("total", 0) > 0:
                attrs["memory_percent"] = round(
                    self._state / self._vm_data["memory"].get("total", 1) * 100, 2
                )
        
        return attrs

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


class ProxmoxVMDiskSensor(ProxmoxSensorBase):
    """Sensor for Proxmox VM disk usage."""

    _attr_device_class = "data_size"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    
    def __init__(
        self, coordinator: DataUpdateCoordinator, vm_id: str, entry_id: str
    ) -> None:
        """Initialize the sensor."""
        self._vm_id = vm_id
        self._entry_id = entry_id
        self._vm_data = self._get_vm_data()
        
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_disk"
        name = f"{self._vm_data.get('name', f'VM {vm_id}')} Disk" if self._vm_data else f"VM {vm_id} Disk"
        
        super().__init__(coordinator, unique_id, name)
        self._update_state()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._vm_data = self._get_vm_data()
        self._update_state()
        self.async_write_ha_state()

    def _get_vm_data(self) -> Optional[Dict[str, Any]]:
        """Get current VM data from coordinator."""
        for vm in self.coordinator.data.get("vms", []):
            if str(vm["id"]) == str(self._vm_id):
                return vm
        return None

    def _update_state(self) -> None:
        """Update the state from the data."""
        if not self._vm_data or not self._vm_data.get("disk"):
            self._available = False
            return
        
        disk_data = self._vm_data["disk"]
        self._state = disk_data.get("total", 0)
        self._available = True

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self._available:
            return None
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "device_type": CATEGORY_VM,
            "vm_id": self._vm_id,
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


class ProxmoxVMIpSensor(ProxmoxSensorBase):
    """Sensor for Proxmox VM IP address."""

    _attr_device_class = None
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(
        self, coordinator: DataUpdateCoordinator, vm_id: str, entry_id: str
    ) -> None:
        """Initialize the sensor."""
        self._vm_id = vm_id
        self._entry_id = entry_id
        self._vm_data = self._get_vm_data()
        
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_ip"
        name = f"{self._vm_data.get('name', f'VM {vm_id}')} IP" if self._vm_data else f"VM {vm_id} IP"
        
        super().__init__(coordinator, unique_id, name)
        self._update_state()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._vm_data = self._get_vm_data()
        self._update_state()
        self.async_write_ha_state()

    def _get_vm_data(self) -> Optional[Dict[str, Any]]:
        """Get current VM data from coordinator."""
        for vm in self.coordinator.data.get("vms", []):
            if str(vm["id"]) == str(self._vm_id):
                return vm
        return None

    def _update_state(self) -> None:
        """Update the state from the data."""
        if not self._vm_data:
            self._available = False
            return
        
        self._state = self._vm_data.get("ip_address")
        self._available = bool(self._state)

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if not self._available:
            return None
        return self._state

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:ip-network"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "device_type": CATEGORY_VM,
            "vm_id": self._vm_id,
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


class ProxmoxNodeCpuSensor(ProxmoxSensorBase):
    """Sensor for Proxmox Node CPU usage."""

    _attr_device_class = "cpu"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    
    def __init__(
        self, coordinator: DataUpdateCoordinator, node_id: str, entry_id: str
    ) -> None:
        """Initialize the sensor."""
        self._node_id = node_id
        self._entry_id = entry_id
        self._node_data = self._get_node_data()
        
        unique_id = f"{DOMAIN}_{entry_id}_node_{node_id}_cpu"
        name = f"{self._node_data.get('name', f'Node {node_id}')} CPU" if self._node_data else f"Node {node_id} CPU"
        
        super().__init__(coordinator, unique_id, name)
        self._update_state()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._node_data = self._get_node_data()
        self._update_state()
        self.async_write_ha_state()

    def _get_node_data(self) -> Optional[Dict[str, Any]]:
        """Get current node data from coordinator."""
        for node in self.coordinator.data.get("nodes", []):
            if node["id"] == self._node_id:
                return node
        return None

    def _update_state(self) -> None:
        """Update the state from the data."""
        if not self._node_data:
            self._available = False
            return
        
        self._state = round(self._node_data.get("cpu", 0) * 100, 2)
        self._available = True

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self._available:
            return None
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "device_type": CATEGORY_NODE,
            "node_id": self._node_id,
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


class ProxmoxNodeMemorySensor(ProxmoxSensorBase):
    """Sensor for Proxmox Node memory usage."""

    _attr_device_class = "memory"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    
    def __init__(
        self, coordinator: DataUpdateCoordinator, node_id: str, entry_id: str
    ) -> None:
        """Initialize the sensor."""
        self._node_id = node_id
        self._entry_id = entry_id
        self._node_data = self._get_node_data()
        
        unique_id = f"{DOMAIN}_{entry_id}_node_{node_id}_memory"
        name = f"{self._node_data.get('name', f'Node {node_id}')} Memory" if self._node_data else f"Node {node_id} Memory"
        
        super().__init__(coordinator, unique_id, name)
        self._update_state()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._node_data = self._get_node_data()
        self._update_state()
        self.async_write_ha_state()

    def _get_node_data(self) -> Optional[Dict[str, Any]]:
        """Get current node data from coordinator."""
        for node in self.coordinator.data.get("nodes", []):
            if node["id"] == self._node_id:
                return node
        return None

    def _update_state(self) -> None:
        """Update the state from the data."""
        if not self._node_data or not self._node_data.get("memory"):
            self._available = False
            return
        
        memory_data = self._node_data["memory"]
        self._state = memory_data.get("used", 0)
        self._available = True

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self._available:
            return None
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = {
            "device_type": CATEGORY_NODE,
            "node_id": self._node_id,
        }
        
        if self._node_data and self._node_data.get("memory"):
            attrs["total_memory"] = self._node_data["memory"].get("total", 0)
            if self._state is not None and self._node_data["memory"].get("total", 0) > 0:
                attrs["memory_percent"] = round(
                    self._state / self._node_data["memory"].get("total", 1) * 100, 2
                )
        
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"node_{self._node_id}")},
            name=self._node_data.get("name", f"Node {self._node_id}") if self._node_data else f"Node {self._node_id}",
            manufacturer="Proxmox VE",
            model="Node",
        )


class ProxmoxNodeDiskSensor(ProxmoxSensorBase):
    """Sensor for Proxmox Node disk usage."""

    _attr_device_class = "data_size"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    
    def __init__(
        self, coordinator: DataUpdateCoordinator, node_id: str, entry_id: str
    ) -> None:
        """Initialize the sensor."""
        self._node_id = node_id
        self._entry_id = entry_id
        self._node_data = self._get_node_data()
        
        unique_id = f"{DOMAIN}_{entry_id}_node_{node_id}_disk"
        name = f"{self._node_data.get('name', f'Node {node_id}')} Disk" if self._node_data else f"Node {node_id} Disk"
        
        super().__init__(coordinator, unique_id, name)
        self._update_state()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._node_data = self._get_node_data()
        self._update_state()
        self.async_write_ha_state()

    def _get_node_data(self) -> Optional[Dict[str, Any]]:
        """Get current node data from coordinator."""
        for node in self.coordinator.data.get("nodes", []):
            if node["id"] == self._node_id:
                return node
        return None

    def _update_state(self) -> None:
        """Update the state from the data."""
        if not self._node_data or not self._node_data.get("disk"):
            self._available = False
            return
        
        disk_data = self._node_data["disk"]
        self._state = disk_data.get("used", 0)
        self._available = True

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self._available:
            return None
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = {
            "device_type": CATEGORY_NODE,
            "node_id": self._node_id,
        }
        
        if self._node_data and self._node_data.get("disk"):
            attrs["total_space"] = self._node_data["disk"].get("total", 0)
            if self._state is not None and self._node_data["disk"].get("total", 0) > 0:
                attrs["disk_percent"] = round(
                    self._state / self._node_data["disk"].get("total", 1) * 100, 2
                )
        
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"node_{self._node_id}")},
            name=self._node_data.get("name", f"Node {self._node_id}") if self._node_data else f"Node {self._node_id}",
            manufacturer="Proxmox VE",
            model="Node",
        )


class ProxmoxStorageSensor(ProxmoxSensorBase):
    """Sensor for Proxmox storage usage."""

    _attr_device_class = "data_size"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    
    def __init__(
        self, coordinator: DataUpdateCoordinator, storage_id: str, node_id: str, entry_id: str
    ) -> None:
        """Initialize the sensor."""
        self._storage_id = storage_id
        self._node_id = node_id
        self._entry_id = entry_id
        self._storage_data = self._get_storage_data()
        
        unique_id = f"{DOMAIN}_{entry_id}_storage_{storage_id}_{node_id}"
        name = f"Storage {storage_id} ({node_id})"
        
        super().__init__(coordinator, unique_id, name)
        self._update_state()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._storage_data = self._get_storage_data()
        self._update_state()
        self.async_write_ha_state()

    def _get_storage_data(self) -> Optional[Dict[str, Any]]:
        """Get current storage data from coordinator."""
        for storage in self.coordinator.data.get("storages", []):
            if storage["id"] == self._storage_id and storage["node"] == self._node_id:
                return storage
        return None

    def _update_state(self) -> None:
        """Update the state from the data."""
        if not self._storage_data or not self._storage_data.get("disk"):
            self._available = False
            return
        
        disk_data = self._storage_data["disk"]
        self._state = disk_data.get("used", 0)
        self._available = True

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self._available:
            return None
        return self._state

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:harddisk"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = {
            "device_type": CATEGORY_STORAGE,
            "storage_id": self._storage_id,
            "node_id": self._node_id,
        }
        
        if self._storage_data:
            attrs["type"] = self._storage_data.get("type", "unknown")
            attrs["status"] = self._storage_data.get("status", "unknown")
            
            if self._storage_data.get("disk"):
                attrs["total_space"] = self._storage_data["disk"].get("total", 0)
                if self._state is not None and self._storage_data["disk"].get("total", 0) > 0:
                    attrs["disk_percent"] = round(
                        self._state / self._storage_data["disk"].get("total", 1) * 100, 2
                    )
        
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"storage_{self._storage_id}_{self._node_id}")},
            name=f"Storage {self._storage_id}",
            manufacturer="Proxmox VE",
            model=self._storage_data.get("type", "Storage") if self._storage_data else "Storage",
            via_device=(DOMAIN, f"node_{self._node_id}"),
        )
