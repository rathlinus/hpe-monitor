# HP V1910 Switch Monitor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

A Home Assistant custom integration for monitoring HP V1910-24G-PoE (and similar) switches via Telnet.

## Features

This integration provides comprehensive monitoring of your HP V1910 switch:

### System Sensors
- **CPU Usage** - Current CPU utilization percentage
- **Memory Usage** - Memory utilization percentage
- **Memory Total/Used/Free** - Detailed memory statistics
- **Temperature** - Switch temperature
- **Uptime** - System uptime
- **Software/Hardware Version** - Firmware information
- **Serial Number** - Device serial number
- **Device Model** - Model name

### PoE Monitoring
- **PoE Power Used** - Total PoE power consumption (Watts)
- **PoE Power Remaining** - Available PoE power (Watts)
- **PoE Power Total** - Maximum PoE power budget (Watts)
- **Per-port PoE Power** - Individual port power consumption
- **Per-port PoE Status** - PoE enabled/delivering status per port

### Port Monitoring
- **Total Ports** - Number of ports
- **Ports Up** - Number of connected ports
- **Ports Down** - Number of disconnected ports
- **Per-port Link Status** - Individual port link status sensors
- **Per-port Binary Sensors** - Up/Down status as binary sensors

### Network Information
- **MAC Address Count** - Number of learned MAC addresses
- **VLAN Count** - Number of configured VLANs
- **ARP Entry Count** - Number of ARP table entries
- **LLDP Neighbors** - Discovered LLDP neighbors (in attributes)

### Hardware Monitoring
- **Fan Status** - Fan operational status (binary sensors)
- **Connectivity** - Overall switch connectivity status

## Installation

### HACS Installation (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots menu in the top right
4. Select "Custom repositories"
5. Add this repository URL with category "Integration"
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/hp_v1910` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "HP V1910"
4. Enter your switch details:
   - **Host**: IP address of your switch (e.g., `192.168.1.10`)
   - **Username**: Telnet username (e.g., `api`)
   - **Password**: Telnet password
   - **Port**: Telnet port (default: 23)
   - **Scan Interval**: How often to poll the switch (default: 30 seconds)

## Requirements

- HP V1910 series switch (or compatible HP/H3C switch)
- Telnet access enabled on the switch
- Valid credentials with read access

## Supported Commands

The integration uses the following telnet commands to gather data:

| Command | Data Retrieved |
|---------|----------------|
| `display version` | Uptime, software/hardware version |
| `display device manuinfo` | Serial number, model, MAC address |
| `display cpu-usage` | CPU utilization |
| `display memory` | Memory statistics |
| `display interface brief` | Port status |
| `display poe power-state` | PoE power budget |
| `display poe interface` | Per-port PoE status |
| `display fan` | Fan status |
| `display environment` | Temperature |
| `display lldp neighbor-information brief` | LLDP neighbors |
| `display mac-address` | MAC address table |
| `display vlan all` | VLAN configuration |
| `display arp` | ARP table |

## Troubleshooting

### Cannot Connect
- Ensure telnet is enabled on your switch
- Verify the IP address is correct
- Check that the credentials are valid
- Ensure no firewall is blocking port 23

### Missing Data
- Some data may not be available depending on your switch model and firmware
- Check the raw output in sensor attributes for debugging
- Enable debug logging for more details

### Enable Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.hp_v1910: debug
```

## Example Dashboard Card

```yaml
type: entities
title: HP V1910 Switch
entities:
  - entity: binary_sensor.hp_v1910_192_168_1_10_connectivity
  - entity: sensor.hp_v1910_192_168_1_10_cpu_usage
  - entity: sensor.hp_v1910_192_168_1_10_memory_usage
  - entity: sensor.hp_v1910_192_168_1_10_temperature
  - entity: sensor.hp_v1910_192_168_1_10_poe_power_used
  - entity: sensor.hp_v1910_192_168_1_10_poe_power_remaining
  - entity: sensor.hp_v1910_192_168_1_10_ports_up
  - entity: sensor.hp_v1910_192_168_1_10_uptime
```

## License

MIT License

## Contributing

Contributions are welcome! Please open an issue or pull request.
