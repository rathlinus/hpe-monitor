# HP V1910 Switch Monitor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

A Home Assistant custom integration for monitoring HP V1910-24G-PoE (365W) and similar HP/H3C switches via Telnet.

## Features

This integration provides comprehensive monitoring of your HP V1910 switch:

### System Sensors
- **CPU Usage** - Current CPU utilization (5s, 1min, 5min averages)
- **Memory Usage** - Memory utilization percentage and bytes
- **Temperature** - Switch temperature from multiple sensors
- **Uptime** - System uptime
- **Software/Hardware/Bootrom Version** - Firmware information
- **Serial Number** - Device serial number
- **Manufacturing Date** - Device build date

### PoE Monitoring (24 ports)
- **PoE Power Used** - Total PoE power consumption (Watts)
- **PoE Power Remaining** - Available PoE power (Watts)
- **PoE Power Budget** - Maximum PoE power (370W)
- **PoE Current/Average/Peak Power** - Power statistics
- **PoE Ports Active** - Number of ports delivering power
- **Per-port PoE Power** - Individual port power consumption with IEEE class, priority, and status

### Port Monitoring (28 ports: 24 GE + 4 SFP)
- **Total Ports** - Number of ports (28)
- **Ports Up/Down** - Connected vs disconnected ports
- **Per-port Link Status** - Speed, duplex, VLAN for each port
- **Per-port Binary Sensors** - Up/Down status as binary sensors

### Network Information
- **MAC Address Count** - Number of learned MAC addresses
- **VLAN Count** - Number of configured VLANs
- **ARP Entry Count** - Number of ARP table entries

### Hardware Monitoring
- **Fan Status** - Fan operational status (binary sensor)
- **Connectivity** - Overall switch connectivity status
- **Multiple Temperature Sensors** - Per-hotspot temperature readings

## Requirements

- HP V1910 series switch (or compatible HP/H3C Comware switch)
- **Telnet access enabled** on the switch
- **Management-level user account** (not just User level)

### Important: User Privileges

The telnet user account **must have Management or Admin privileges**. A basic "User" level account only has access to limited commands like `ping` and cannot read switch statistics.

To check/change user privileges:
1. Log into the switch web interface (http://your-switch-ip)
2. Go to **Device → Users** or **System → User Management**
3. Ensure your API user has **Management** level access

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
   - **Username**: Telnet username with Management privileges
   - **Password**: Telnet password
   - **Port**: Telnet port (default: 23)
   - **Scan Interval**: How often to poll the switch (default: 30 seconds)

## How It Works

The integration uses a special command `_cmdline-mode on` to unlock the full HP Comware CLI, which is normally hidden on V1910 switches. This allows access to detailed monitoring commands that aren't available in the standard menu-based interface.

### Commands Used

| Command | Data Retrieved |
|---------|----------------|
| `display version` | Uptime, software/hardware version, DRAM |
| `display device manuinfo` | Serial number, model, MAC address, manufacturing date |
| `display cpu-usage` | CPU utilization (5s, 1min, 5min) |
| `display memory` | Memory total, used, free, percentage |
| `display brief interface` | All port status, speed, duplex, VLAN |
| `display poe interface` | Per-port PoE power, class, status |
| `display poe pse` | PSE power budget, current/average/peak power |
| `display fan` | Fan status |
| `display environment` | Temperature sensors with warning/alarm limits |
| `display mac-address` | MAC address table |
| `display vlan all` | VLAN configuration |
| `display arp` | ARP table |

## Sensors Created

The integration creates the following entities:

### Main Sensors (always enabled)
- `sensor.hp_v1910_*_cpu_usage`
- `sensor.hp_v1910_*_memory_usage`
- `sensor.hp_v1910_*_temperature`
- `sensor.hp_v1910_*_poe_power_used`
- `sensor.hp_v1910_*_poe_power_remaining`
- `sensor.hp_v1910_*_poe_power_budget`
- `sensor.hp_v1910_*_poe_peak_power`
- `sensor.hp_v1910_*_poe_ports_active`
- `sensor.hp_v1910_*_ports_up`
- `sensor.hp_v1910_*_ports_down`
- `sensor.hp_v1910_*_uptime`
- `sensor.hp_v1910_*_mac_address_count`
- `sensor.hp_v1910_*_arp_entry_count`
- `binary_sensor.hp_v1910_*_connectivity`
- `binary_sensor.hp_v1910_*_fan_1`

### Per-Port Sensors (24 PoE ports)
- `sensor.hp_v1910_*_poe_ge1_0_1` through `ge1_0_24`
- `binary_sensor.hp_v1910_*_poe_delivering_ge1_0_1` through `ge1_0_24`
- `binary_sensor.hp_v1910_*_link_ge1_0_1` through `ge1_0_28`

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

## Troubleshooting

### Cannot Connect
- Ensure telnet is enabled on your switch (via web interface)
- Verify the IP address is correct and reachable (`ping your-switch-ip`)
- Check that port 23 is open (`Test-NetConnection your-switch-ip -Port 23`)
- Ensure no firewall is blocking port 23

### Limited Data / Commands Not Working
- Your user account likely only has "User" level access
- Upgrade the account to "Management" level in the switch web interface
- The integration needs `_cmdline-mode on` access which requires Management privileges

### Enable Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.hp_v1910: debug
```

## Tested Hardware

- **HP V1910-24G-PoE (365W)** - Model JE007A
  - Firmware: Comware 5.20 Release 1111P02
  - 24 Gigabit Ethernet PoE ports + 4 SFP ports

Should also work with:
- HP V1910-8G-PoE
- HP V1910-16G
- HP V1910-24G (non-PoE)
- HP V1910-48G
- Other HP/H3C Comware 5.x switches

## License

MIT License

## Contributing

Contributions are welcome! Please open an issue or pull request.

## Acknowledgments

- Uses the `_cmdline-mode on` with password `512900` to unlock full CLI access on HP V1910 switches
- Based on HP/H3C Comware 5.x command structure
