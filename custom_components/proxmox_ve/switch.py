"""Switch platform for Proxmox VE."""
import logging
from typing import Any, Dict, List, Optional, Callable

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
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
    SERVICE_START,
    SERVICE_SHUTDOWN,
    SERVICE_RESTART,
    SERVICE_FORCE_STOP,
    SERVICE_FORCE_RESTART,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Proxmox VE switches."""
    # All switch functionality has been replaced with buttons
    # This setup function remains for backward compatibility
    # but no longer creates any entities
    return


class ProxmoxSwitchBase(CoordinatorEntity, SwitchEntity):
    """Base switch for Proxmox VE actions."""

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
        """Initialize the switch."""
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
        self._is_on = False
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        # Call turn_on_action in an executor to prevent blocking
        if await self.hass.async_add_executor_job(self._turn_on_action):
            self._is_on = True
            self.async_write_ha_state()
            # Schedule turn off after a short delay since these are momentary actions
            self.hass.async_create_task(self._async_turn_off_later())
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        # These are momentary switches, so no real turn off action
        self._is_on = False
        self.async_write_ha_state()
    
    async def _async_turn_off_later(self) -> None:
        """Turn off the switch after a short delay."""
        await self.hass.async_add_job(self.async_turn_off)
    
    def _turn_on_action(self) -> bool:
        """Action to perform when turning on."""
        return False
    
    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on
    
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


class ProxmoxVMStartSwitch(ProxmoxSwitchBase):
    """Switch to start a VM or container."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        vm_id: str,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the switch."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._vm_id = vm_id
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        SwitchEntity.__init__(self)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_start"
        self._attr_unique_id = unique_id
        self._attr_name = "Start"
        self._attr_icon = "mdi:play"
        self._device_type = CATEGORY_VM
        self._device_id = f"vm_{vm_id}"
        self._available = True
        self._is_on = False
        
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
    
    def _turn_on_action(self) -> bool:
        """Start the VM."""
        return self._api.start_vm(self._node_id, self._vm_id)


class ProxmoxVMShutdownSwitch(ProxmoxSwitchBase):
    """Switch to shutdown a VM or container."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        vm_id: str,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the switch."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._vm_id = vm_id
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        SwitchEntity.__init__(self)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_shutdown"
        self._attr_unique_id = unique_id
        self._attr_name = "Shutdown"
        self._attr_icon = "mdi:stop"
        self._device_type = CATEGORY_VM
        self._device_id = f"vm_{vm_id}"
        self._available = True
        self._is_on = False
        
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
    
    def _turn_on_action(self) -> bool:
        """Shutdown the VM."""
        return self._api.shutdown_vm(self._node_id, self._vm_id)


class ProxmoxVMRestartSwitch(ProxmoxSwitchBase):
    """Switch to restart a VM or container."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        vm_id: str,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the switch."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._vm_id = vm_id
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        SwitchEntity.__init__(self)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_restart"
        self._attr_unique_id = unique_id
        self._attr_name = "Restart"
        self._attr_icon = "mdi:restart"
        self._device_type = CATEGORY_VM
        self._device_id = f"vm_{vm_id}"
        self._available = True
        self._is_on = False
        
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
    
    def _turn_on_action(self) -> bool:
        """Restart the VM."""
        return self._api.restart_vm(self._node_id, self._vm_id)


class ProxmoxVMForceStopSwitch(ProxmoxSwitchBase):
    """Switch to force stop a VM or container."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        vm_id: str,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the switch."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._vm_id = vm_id
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        SwitchEntity.__init__(self)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_force_stop"
        self._attr_unique_id = unique_id
        self._attr_name = "Force Stop"
        self._attr_icon = "mdi:stop-circle"
        self._device_type = CATEGORY_VM
        self._device_id = f"vm_{vm_id}"
        self._available = True
        self._is_on = False
        
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
    
    def _turn_on_action(self) -> bool:
        """Force stop the VM."""
        return self._api.force_stop_vm(self._node_id, self._vm_id)


class ProxmoxVMForceRestartSwitch(ProxmoxSwitchBase):
    """Switch to force restart a VM or container."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        vm_id: str,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the switch."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._vm_id = vm_id
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        SwitchEntity.__init__(self)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_vm_{vm_id}_force_restart"
        self._attr_unique_id = unique_id
        self._attr_name = "Force Restart"
        self._attr_icon = "mdi:restart-alert"
        self._device_type = CATEGORY_VM
        self._device_id = f"vm_{vm_id}"
        self._available = True
        self._is_on = False
        
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
    
    def _turn_on_action(self) -> bool:
        """Force restart the VM."""
        return self._api.force_restart_vm(self._node_id, self._vm_id)


class ProxmoxNodeShutdownSwitch(ProxmoxSwitchBase):
    """Switch to shutdown a Proxmox node."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the switch."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        SwitchEntity.__init__(self)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_node_{node_id}_shutdown"
        self._attr_unique_id = unique_id
        self._attr_name = "Shutdown"
        self._attr_icon = "mdi:power"
        self._device_type = CATEGORY_NODE
        self._device_id = f"node_{node_id}"
        self._available = True
        self._is_on = False
        
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
    
    def _turn_on_action(self) -> bool:
        """Shutdown the node."""
        return self._api.shutdown_node(self._node_id)


class ProxmoxNodeRestartSwitch(ProxmoxSwitchBase):
    """Switch to restart a Proxmox node."""
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: ProxmoxAPI,
        node_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the switch."""
        # Set up basic attributes and coordinator first
        self.coordinator = coordinator
        self._api = api
        self._node_id = node_id
        self._entry_id = entry_id
        
        # Set up parent classes
        CoordinatorEntity.__init__(self, coordinator)
        SwitchEntity.__init__(self)
        
        # Set basic attributes
        unique_id = f"{DOMAIN}_{entry_id}_node_{node_id}_restart"
        self._attr_unique_id = unique_id
        self._attr_name = "Restart"
        self._attr_icon = "mdi:restart"
        self._device_type = CATEGORY_NODE
        self._device_id = f"node_{node_id}"
        self._available = True
        self._is_on = False
        
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
    
    def _turn_on_action(self) -> bool:
        """Restart the node."""
        return self._api.restart_node(self._node_id)
