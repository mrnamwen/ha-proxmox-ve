"""API client for Proxmox VE."""
import logging
from typing import Dict, List, Optional

import proxmoxer
import requests
from requests.exceptions import ConnectTimeout, SSLError

_LOGGER = logging.getLogger(__name__)


class ProxmoxAPI:
    """API client for Proxmox VE."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        realm: str = "pam",
        verify_ssl: bool = True,
    ):
        """Initialize the API client."""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.realm = realm
        self.verify_ssl = verify_ssl
        self._proxmox = None
        # Don't connect here, we'll connect on first use
        # to avoid blocking calls in the constructor

    def _connect(self) -> None:
        """Connect to Proxmox API."""
        # This method should only be called from methods
        # that are executed in an executor
        if self._proxmox is not None:
            return

        try:
            self._proxmox = proxmoxer.ProxmoxAPI(
                self.host,
                port=self.port,
                user=f"{self.user}@{self.realm}",
                password=self.password,
                verify_ssl=self.verify_ssl,
            )
        except (ConnectTimeout, SSLError) as error:
            _LOGGER.error("Error connecting to Proxmox VE: %s", error)
            raise

    def test_connection(self) -> bool:
        """Test connection to Proxmox VE."""
        # Always call _connect() first in methods that use the API
        # This ensures lazy initialization of the connection
        try:
            self._connect()
            self._proxmox.nodes.get()
            return True
        except Exception as error:
            _LOGGER.error("Connection test failed: %s", error)
            raise

    def get_nodes(self) -> List[Dict]:
        """Get all nodes in the cluster."""
        self._connect()
        nodes = []
        
        for node in self._proxmox.nodes.get():
            node_id = node["node"]
            try:
                # Get node status
                status = self._proxmox.nodes(node_id).status.get()
                
                # Get resource usage
                usage = {
                    "cpu": status.get("cpu", 0),
                    "memory": {
                        "used": status.get("memory", {}).get("used", 0),
                        "total": status.get("memory", {}).get("total", 0),
                    },
                    "uptime": status.get("uptime", 0),
                }
                
                # Add disk usage info
                disk_usage = {}
                for disk in self._proxmox.nodes(node_id).disks.list.get():
                    if "mount" in disk and disk["mount"] == "/":
                        disk_usage = {
                            "used": disk.get("used", 0),
                            "total": disk.get("size", 0),
                        }
                        break
                
                nodes.append({
                    "id": node_id,
                    "name": node.get("name", node_id),
                    "status": node.get("status", "unknown"),
                    "cpu": usage["cpu"],
                    "memory": usage["memory"],
                    "disk": disk_usage,
                    "uptime": usage["uptime"],
                })
            except Exception as error:
                _LOGGER.error("Error getting status for node %s: %s", node_id, error)
        
        return nodes

    def get_vms(self) -> List[Dict]:
        """Get all VMs in the cluster."""
        self._connect()
        vms = []
        
        for vm in self._proxmox.cluster.resources.get(type="vm"):
            vm_id = vm["vmid"]
            node = vm["node"]
            
            try:
                # Get more detailed VM info
                config = self._proxmox.nodes(node).qemu(vm_id).config.get()
                
                # Try to get IP address
                ip_address = None
                try:
                    agent_network = self._proxmox.nodes(node).qemu(vm_id).agent.get("network-get-interfaces")
                    for interface in agent_network.get("result", []):
                        for ip_info in interface.get("ip-addresses", []):
                            if ip_info.get("ip-address-type") == "ipv4":
                                ip_address = ip_info.get("ip-address")
                                break
                        if ip_address:
                            break
                except Exception:
                    # Agent might not be running
                    pass
                
                # Get disks for storage info
                disks = {}
                for key, value in config.items():
                    if key.startswith(("ide", "sata", "scsi", "virtio")):
                        if "size" in value:
                            disks[key] = value
                
                total_disk = 0
                for disk in disks.values():
                    # Parse size string (e.g., "32G")
                    size_str = disk.get("size", "0")
                    try:
                        if size_str.endswith("G"):
                            size = float(size_str[:-1]) * 1024 * 1024 * 1024
                        elif size_str.endswith("M"):
                            size = float(size_str[:-1]) * 1024 * 1024
                        else:
                            size = float(size_str)
                        total_disk += size
                    except ValueError:
                        pass
                
                vms.append({
                    "id": vm_id,
                    "name": vm.get("name", f"VM {vm_id}"),
                    "node": node,
                    "status": vm.get("status", "unknown"),
                    "cpu": {
                        "used": vm.get("cpu", 0),
                        "total": config.get("cores", 1),
                    },
                    "memory": {
                        "used": vm.get("mem", 0),
                        "total": config.get("memory", 0) * 1024 * 1024,  # Convert to bytes
                    },
                    "disk": {
                        "total": total_disk,
                    },
                    "ip_address": ip_address,
                })
            except Exception as error:
                _LOGGER.error("Error getting details for VM %s: %s", vm_id, error)
        
        return vms

    def get_storages(self) -> List[Dict]:
        """Get all storage devices in the cluster."""
        self._connect()
        storages = []
        
        for storage in self._proxmox.cluster.resources.get(type="storage"):
            storage_id = storage["storage"]
            node = storage.get("node")
            
            # Skip if not node-specific storage
            if not node:
                continue
            
            try:
                storages.append({
                    "id": storage_id,
                    "node": node,
                    "type": storage.get("type", "unknown"),
                    "status": storage.get("status", "unknown"),
                    "disk": {
                        "used": storage.get("used", 0),
                        "total": storage.get("total", 0),
                    },
                })
            except Exception as error:
                _LOGGER.error("Error getting storage %s: %s", storage_id, error)
        
        return storages

    def start_vm(self, node_id: str, vm_id: int) -> bool:
        """Start a VM."""
        try:
            self._connect()
            self._proxmox.nodes(node_id).qemu(vm_id).status.start.post()
            return True
        except Exception as error:
            _LOGGER.error("Error starting VM %s: %s", vm_id, error)
            return False

    def shutdown_vm(self, node_id: str, vm_id: int) -> bool:
        """Shutdown a VM gracefully."""
        try:
            self._connect()
            self._proxmox.nodes(node_id).qemu(vm_id).status.shutdown.post()
            return True
        except Exception as error:
            _LOGGER.error("Error shutting down VM %s: %s", vm_id, error)
            return False

    def restart_vm(self, node_id: str, vm_id: int) -> bool:
        """Restart a VM gracefully."""
        try:
            self._connect()
            self._proxmox.nodes(node_id).qemu(vm_id).status.reboot.post()
            return True
        except Exception as error:
            _LOGGER.error("Error restarting VM %s: %s", vm_id, error)
            return False

    def force_stop_vm(self, node_id: str, vm_id: int) -> bool:
        """Force stop a VM."""
        try:
            self._connect()
            self._proxmox.nodes(node_id).qemu(vm_id).status.stop.post()
            return True
        except Exception as error:
            _LOGGER.error("Error force stopping VM %s: %s", vm_id, error)
            return False

    def force_restart_vm(self, node_id: str, vm_id: int) -> bool:
        """Force restart a VM."""
        try:
            self._connect()
            # First stop, then start
            self._proxmox.nodes(node_id).qemu(vm_id).status.stop.post()
            self._proxmox.nodes(node_id).qemu(vm_id).status.start.post()
            return True
        except Exception as error:
            _LOGGER.error("Error force restarting VM %s: %s", vm_id, error)
            return False

    def shutdown_node(self, node_id: str) -> bool:
        """Shutdown a Proxmox node."""
        try:
            self._connect()
            self._proxmox.nodes(node_id).status.shutdown.post()
            return True
        except Exception as error:
            _LOGGER.error("Error shutting down node %s: %s", node_id, error)
            return False

    def restart_node(self, node_id: str) -> bool:
        """Restart a Proxmox node."""
        try:
            self._connect()
            self._proxmox.nodes(node_id).status.reboot.post()
            return True
        except Exception as error:
            _LOGGER.error("Error restarting node %s: %s", node_id, error)
            return False
