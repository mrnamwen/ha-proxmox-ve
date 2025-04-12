# Proxmox VE Integration for Home Assistant

This custom integration allows you to monitor and control your Proxmox VE virtual machines, LXC containers, nodes, and storage from Home Assistant.

## Features

- Monitor VM/container status, CPU, RAM, disk usage, and IP addresses
- Control VMs and containers with start, shutdown, restart, force stop, and force restart buttons
- Monitor Proxmox nodes with CPU, memory, and disk usage sensors
- Control nodes with shutdown and restart buttons
- Monitor storage usage
- Automatically detects and supports both QEMU VMs and LXC containers

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the "+ Explore & Download Repositories" button
4. Search for "Proxmox VE"
5. Click on "Proxmox VE" in the search results
6. Click "Download"
7. Restart Home Assistant

### Manual Installation

1. Download or clone this repository
2. Copy the `custom_components/proxmox_ve` directory to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to Settings -> Devices & Services
2. Click "Add Integration"
3. Search for "Proxmox VE"
4. Enter your Proxmox VE server details:
   - Host: The hostname or IP address of your Proxmox VE server
   - Port: The port of your Proxmox VE API (default: 8006)
   - Username: Your Proxmox VE username
   - Password: Your Proxmox VE password
   - Realm: The authentication realm (default: pam)
   - Verify SSL: Whether to verify the SSL certificate (recommended)

## Entities

After configuration, the following entities will be created:

### For each VM/Container:

- Device tracker: Shows if the VM/container is running
- Binary sensor: VM/container status (running/stopped)
- Sensors: CPU usage, memory usage, disk size, IP address (if available)
- Switches: Start, shutdown, restart, force stop, force restart

### For each node:

- Binary sensor: Node status (online/offline)
- Sensors: CPU usage, memory usage, disk usage
- Switches: Shutdown, restart

### For each storage:

- Sensor: Storage usage

## Requirements

- Home Assistant 2022.5.0 or newer
- Proxmox VE 6.0 or newer
- Network access from Home Assistant to Proxmox VE API

## Troubleshooting

- Make sure your Proxmox VE API is accessible from Home Assistant
- Check that your username has sufficient permissions in Proxmox VE
- If you see authentication errors, try using username@realm format
- For SSL issues, you may need to disable SSL verification (not recommended for production)

## Support

If you encounter any issues, please report them on the GitHub repository.
