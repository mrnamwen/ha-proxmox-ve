# Proxmox VE Integration for Home Assistant

This custom integration allows you to monitor and control your Proxmox VE virtual machines, nodes, and storage from Home Assistant.

## Features

- **Virtual Machines**
  - Monitor status (on/off)
  - Track CPU, memory, and disk usage
  - View IP addresses
  - Control VMs with start, shutdown, restart, force stop, and force restart buttons

- **Nodes**
  - Monitor status (online/offline)
  - Track CPU, memory, and disk usage
  - Control nodes with shutdown and restart buttons

- **Storage**
  - Monitor storage usage across the Proxmox cluster

## Screenshots

(Screenshots will appear here once the integration is installed and configured)

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for "Proxmox VE" and select it
4. Enter your Proxmox VE server details:
   - Host: IP address or hostname
   - Port: API port (default: 8006)
   - Username: Your Proxmox username
   - Password: Your Proxmox password
   - Realm: Authentication realm (default: pam)
   - Verify SSL: Whether to verify SSL certificates

## Requirements

- Home Assistant 2022.5.0 or newer
- Proxmox VE 6.0 or newer
- Network access from Home Assistant to Proxmox VE API
