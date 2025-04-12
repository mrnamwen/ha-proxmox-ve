"""Constants for the Proxmox VE integration."""

DOMAIN = "proxmox_ve"
PLATFORMS = ["device_tracker", "binary_sensor", "sensor", "switch", "button"]
UPDATE_INTERVAL = 30  # seconds

# Configuration
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_REALM = "realm"
CONF_VERIFY_SSL = "verify_ssl"

# Default values
DEFAULT_PORT = 8006
DEFAULT_REALM = "pam"
DEFAULT_VERIFY_SSL = True

# Entity attributes
ATTR_STATUS = "status"
ATTR_NODE = "node"
ATTR_CPU = "cpu"
ATTR_RAM = "ram"
ATTR_DISK = "disk"
ATTR_IP = "ip_address"

# VM Status
STATUS_RUNNING = "running"
STATUS_STOPPED = "stopped"
STATUS_PAUSED = "paused"

# Entity categories
CATEGORY_VM = "vm"
CATEGORY_NODE = "node"
CATEGORY_STORAGE = "storage"

# Service names
SERVICE_START = "start"
SERVICE_SHUTDOWN = "shutdown"
SERVICE_RESTART = "restart"
SERVICE_FORCE_STOP = "force_stop"
SERVICE_FORCE_RESTART = "force_restart"
