"""Button platform for Proxmox VE."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import ProxmoxAPI
from .const import (
    DOMAIN,
    CATEGORY_VM,
    CATEGORY_NODE,
    STATUS_RUNNING,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Proxmox VE buttons."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][config_entry.entry_id]["api"]
    
    entities = []
    
    # Add VM buttons
    for vm in coordinator.data.get("vms", []):
        vm_id = vm["id"]
        node_id = vm["node"]
        
        # Start button (only for stopped VMs)
        entities.append(
            ProxmoxVMStartButton(coordinator, api, vm_id, node_id, config_entry.entry_id)
        )
        
        # Shutdown button (only for running VMs)
        entities.append(
            ProxmoxVMShutdownButton(coordinator, api, vm_id, node_id, config_entry.entry_id)
        )
        
        # Restart button
        entities.append(
            ProxmoxVMRestartButton(coordinator, api, vm_id, node_id, config_entry.entry_id)
        )
        
        # Force stop button
        entities.append(
            ProxmoxVMForceStopButton(coordinator, api, vm_id, node_id, config_entry.entry_id)
        )
        
        # Force restart button
        entities.append(
            ProxmoxVMForceRestartButton(coordinator, api, vm_id, node_id, config_entry.entry_id)
        )
    
    # Add Node buttons
    for node in coordinator.data.get("nodes", []):
        node_id = node["id"]
        
        # Shutdown node button
        entities.append(
            ProxmoxNodeShutdownButton(coordinator, api, node_id, config_entry.entry_id)
        )
        
        # Restart node button
        entities.append(
            ProxmoxNodeRestartButton(coordinator, api, node_id, config_entry.entry_id)
        )
    
    async_add_entities(entities)


class ProxmoxButtonBase(CoordinatorEntity, ButtonEntity):
    """Base button for Proxmox VE actions."""

    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        unique_id: str,
        name: str,
        icon: str,
        device_type: str,
        device_id: str,
        device_name: str,
        via_device: Optional[tuple] = None,
    ) -> None:
        """Initialize the button."""
        # Explicitly initialize the CoordinatorEntity parent class
        CoordinatorEntity.__init__(self, coordinator)
        self.coordinator = coordinator
        self._api = api
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_icon = icon
        self._device_type = device_type
        self._device_id = device_id
        self._device_name = device_name
        self._via_device = via_device
        self._available = True
    
    async def async_press(self) -> None:
        """Press the button."""
        await self.hass.async_add_executor_job(self._action)
    
    def _action(self) -> None:
        """Action to perform when pressing the button."""
        pass
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._available
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
            manufacturer="Proxmox VE",
        )
        
        if self._device_type == CATEGORY_VM:
            device_info["model"] = "Virtual Machine"
            if self._via_device:
                device_info["via_device"] = self._via_device
        elif self._device_type == CATEGORY_NODE:
            device_info["model"] = "Node"
        
        return device_info


class ProxmoxVMStartButton(ProxmoxButtonBase):
    """Button to start a VM or container."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        vm_id: str,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the button."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._vm_id = vm_id
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_start"
        self._attr_unique_id = unique_id
        self._attr_name = "Start"
        self._attr_icon = "mdi:play"
        self._device_type = CATEGORY_VM
        self._device_id = f"vm_{vm_id}"
        self._available = True
        
        # Now get VM data after coordinator is available
        self._vm_data = self._get_vm_data()
        
        # Set device name based on VM data
        self._device_name = self._vm_data.get("name", f"VM {vm_id}") if self._vm_data else f"VM {vm_id}"
        self._via_device = (DOMAIN, f"node_{node_id}")
        
        # Update availability based on VM state
        self._update_availability()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._vm_data = self._get_vm_data()
        self._update_availability()
        self.async_write_ha_state()
    
    def _get_vm_data(self) -> Optional[Dict[str, Any]]:
        """Get current VM data from coordinator."""
        for vm in self.coordinator.data.get("vms", []):
            if str(vm["id"]) == str(self._vm_id):
                return vm
        return None
    
    def _update_availability(self) -> None:
        """Update availability based on VM status."""
        if not self._vm_data:
            self._available = False
            return
        
        # Start button is only available when VM is stopped
        self._available = self._vm_data.get("status") != STATUS_RUNNING
    
    def _action(self) -> None:
        """Start the VM."""
        self._api.start_vm(self._node_id, self._vm_id)


class ProxmoxVMShutdownButton(ProxmoxButtonBase):
    """Button to shutdown a VM or container."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        vm_id: str,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the button."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._vm_id = vm_id
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_shutdown"
        self._attr_unique_id = unique_id
        self._attr_name = "Shutdown"
        self._attr_icon = "mdi:stop"
        self._device_type = CATEGORY_VM
        self._device_id = f"vm_{vm_id}"
        self._available = True
        
        # Now get VM data after coordinator is available
        self._vm_data = self._get_vm_data()
        
        # Set device name based on VM data
        self._device_name = self._vm_data.get("name", f"VM {vm_id}") if self._vm_data else f"VM {vm_id}"
        self._via_device = (DOMAIN, f"node_{node_id}")
        
        # Update availability based on VM state
        self._update_availability()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._vm_data = self._get_vm_data()
        self._update_availability()
        self.async_write_ha_state()
    
    def _get_vm_data(self) -> Optional[Dict[str, Any]]:
        """Get current VM data from coordinator."""
        for vm in self.coordinator.data.get("vms", []):
            if str(vm["id"]) == str(self._vm_id):
                return vm
        return None
    
    def _update_availability(self) -> None:
        """Update availability based on VM status."""
        if not self._vm_data:
            self._available = False
            return
        
        # Shutdown button is only available when VM is running
        self._available = self._vm_data.get("status") == STATUS_RUNNING
    
    def _action(self) -> None:
        """Shutdown the VM."""
        self._api.shutdown_vm(self._node_id, self._vm_id)


class ProxmoxVMRestartButton(ProxmoxButtonBase):
    """Button to restart a VM or container."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        vm_id: str,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the button."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._vm_id = vm_id
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_restart"
        self._attr_unique_id = unique_id
        self._attr_name = "Restart"
        self._attr_icon = "mdi:restart"
        self._device_type = CATEGORY_VM
        self._device_id = f"vm_{vm_id}"
        self._available = True
        
        # Now get VM data after coordinator is available
        self._vm_data = self._get_vm_data()
        
        # Set device name based on VM data
        self._device_name = self._vm_data.get("name", f"VM {vm_id}") if self._vm_data else f"VM {vm_id}"
        self._via_device = (DOMAIN, f"node_{node_id}")
        
        # Update availability based on VM state
        self._update_availability()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._vm_data = self._get_vm_data()
        self._update_availability()
        self.async_write_ha_state()
    
    def _get_vm_data(self) -> Optional[Dict[str, Any]]:
        """Get current VM data from coordinator."""
        for vm in self.coordinator.data.get("vms", []):
            if str(vm["id"]) == str(self._vm_id):
                return vm
        return None
    
    def _update_availability(self) -> None:
        """Update availability based on VM status."""
        if not self._vm_data:
            self._available = False
            return
        
        # Restart button is only available when VM is running
        self._available = self._vm_data.get("status") == STATUS_RUNNING
    
    def _action(self) -> None:
        """Restart the VM."""
        self._api.restart_vm(self._node_id, self._vm_id)


class ProxmoxVMForceStopButton(ProxmoxButtonBase):
    """Button to force stop a VM or container."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        vm_id: str,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the button."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._vm_id = vm_id
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_force_stop"
        self._attr_unique_id = unique_id
        self._attr_name = "Force Stop"
        self._attr_icon = "mdi:stop-circle"
        self._device_type = CATEGORY_VM
        self._device_id = f"vm_{vm_id}"
        self._available = True
        
        # Now get VM data after coordinator is available
        self._vm_data = self._get_vm_data()
        
        # Set device name based on VM data
        self._device_name = self._vm_data.get("name", f"VM {vm_id}") if self._vm_data else f"VM {vm_id}"
        self._via_device = (DOMAIN, f"node_{node_id}")
        
        # Update availability based on VM state
        self._update_availability()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._vm_data = self._get_vm_data()
        self._update_availability()
        self.async_write_ha_state()
    
    def _get_vm_data(self) -> Optional[Dict[str, Any]]:
        """Get current VM data from coordinator."""
        for vm in self.coordinator.data.get("vms", []):
            if str(vm["id"]) == str(self._vm_id):
                return vm
        return None
    
    def _update_availability(self) -> None:
        """Update availability based on VM status."""
        if not self._vm_data:
            self._available = False
            return
        
        # Force stop button is only available when VM is running
        self._available = self._vm_data.get("status") == STATUS_RUNNING
    
    def _action(self) -> None:
        """Force stop the VM."""
        self._api.force_stop_vm(self._node_id, self._vm_id)


class ProxmoxVMForceRestartButton(ProxmoxButtonBase):
    """Button to force restart a VM or container."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        vm_id: str,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the button."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._vm_id = vm_id
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_force_restart"
        self._attr_unique_id = unique_id
        self._attr_name = "Force Restart"
        self._attr_icon = "mdi:restart-alert"
        self._device_type = CATEGORY_VM
        self._device_id = f"vm_{vm_id}"
        self._available = True
        
        # Now get VM data after coordinator is available
        self._vm_data = self._get_vm_data()
        
        # Set device name based on VM data
        self._device_name = self._vm_data.get("name", f"VM {vm_id}") if self._vm_data else f"VM {vm_id}"
        self._via_device = (DOMAIN, f"node_{node_id}")
        
        # Update availability based on VM state
        self._update_availability()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._vm_data = self._get_vm_data()
        self._update_availability()
        self.async_write_ha_state()
    
    def _get_vm_data(self) -> Optional[Dict[str, Any]]:
        """Get current VM data from coordinator."""
        for vm in self.coordinator.data.get("vms", []):
            if str(vm["id"]) == str(self._vm_id):
                return vm
        return None
    
    def _update_availability(self) -> None:
        """Update availability based on VM status."""
        if not self._vm_data:
            self._available = False
            return
        
        # Force restart button is available regardless of status
        self._available = True
    
    def _action(self) -> None:
        """Force restart the VM."""
        self._api.force_restart_vm(self._node_id, self._vm_id)


class ProxmoxNodeShutdownButton(ProxmoxButtonBase):
    """Button to shutdown a Proxmox node."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the button."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_node_{node_id}_shutdown"
        self._attr_unique_id = unique_id
        self._attr_name = "Shutdown"
        self._attr_icon = "mdi:power"
        self._device_type = CATEGORY_NODE
        self._device_id = f"node_{node_id}"
        self._available = True
        
        # Now get node data after coordinator is available
        self._node_data = self._get_node_data()
        
        # Set device name based on node data
        self._device_name = self._node_data.get("name", f"Node {node_id}") if self._node_data else f"Node {node_id}"
        
        # Update availability based on node state
        self._update_availability()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._node_data = self._get_node_data()
        self._update_availability()
        self.async_write_ha_state()
    
    def _get_node_data(self) -> Optional[Dict[str, Any]]:
        """Get current node data from coordinator."""
        for node in self.coordinator.data.get("nodes", []):
            if node["id"] == self._node_id:
                return node
        return None
    
    def _update_availability(self) -> None:
        """Update availability based on node status."""
        if not self._node_data:
            self._available = False
            return
        
        # Node shutdown button is only available when node is online
        self._available = self._node_data.get("status") == "online"
    
    def _action(self) -> None:
        """Shutdown the node."""
        self._api.shutdown_node(self._node_id)


class ProxmoxNodeRestartButton(ProxmoxButtonBase):
    """Button to restart a Proxmox node."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the button."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_node_{node_id}_restart"
        self._attr_unique_id = unique_id
        self._attr_name = "Restart"
        self._attr_icon = "mdi:restart"
        self._device_type = CATEGORY_NODE
        self._device_id = f"node_{node_id}"
        self._available = True
        
        # Now get node data after coordinator is available
        self._node_data = self._get_node_data()
        
        # Set device name based on node data
        self._device_name = self._node_data.get("name", f"Node {node_id}") if self._node_data else f"Node {node_id}"
        
        # Update availability based on node state
        self._update_availability()
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._node_data = self._get_node_data()
        self._update_availability()
        self.async_write_ha_state()
    
    def _get_node_data(self) -> Optional[Dict[str, Any]]:
        """Get current node data from coordinator."""
        for node in self.coordinator.data.get("nodes", []):
            if node["id"] == self._node_id:
                return node
        return None
    
    def _update_availability(self) -> None:
        """Update availability based on node status."""
        if not self._node_data:
            self._available = False
            return
        
        # Node restart button is only available when node is online
        self._available = self._node_data.get("status") == "online"
    
    def _action(self) -> None:
        """Restart the node."""
        self._api.restart_node(self._node_id)
