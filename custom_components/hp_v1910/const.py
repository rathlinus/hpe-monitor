"""Constants for HP V1910 Switch integration."""

DOMAIN = "hp_v1910"

# Configuration
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_PORT = 23
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_TIMEOUT = 10

# Telnet commands for HP V1910
CMD_DISPLAY_VERSION = "display version"
CMD_DISPLAY_CPU = "display cpu-usage"
CMD_DISPLAY_MEMORY = "display memory"
CMD_DISPLAY_INTERFACE_BRIEF = "display interface brief"
CMD_DISPLAY_POE_POWER = "display poe power-state"
CMD_DISPLAY_POE_INTERFACE = "display poe interface"
CMD_DISPLAY_DEVICE_MANUINFO = "display device manuinfo"
CMD_DISPLAY_FAN = "display fan"
CMD_DISPLAY_ENVIRONMENT = "display environment"
CMD_DISPLAY_LLDP_NEIGHBOR = "display lldp neighbor-information brief"
CMD_DISPLAY_MAC_ADDRESS = "display mac-address"
CMD_DISPLAY_ARP = "display arp"
CMD_DISPLAY_VLAN_ALL = "display vlan all"
CMD_DISPLAY_POWER = "display power"
CMD_DISPLAY_INTERFACE = "display interface"

# Attributes
ATTR_MODEL = "model"
ATTR_SERIAL = "serial_number"
ATTR_FIRMWARE = "firmware_version"
ATTR_UPTIME = "uptime"
ATTR_CPU_USAGE = "cpu_usage"
ATTR_MEMORY_USAGE = "memory_usage"
ATTR_MEMORY_FREE = "memory_free"
ATTR_MEMORY_TOTAL = "memory_total"
ATTR_POE_POWER_USED = "poe_power_used"
ATTR_POE_POWER_REMAINING = "poe_power_remaining"
ATTR_POE_POWER_TOTAL = "poe_power_total"
ATTR_POE_ENERGY_TOTAL = "poe_energy_total"
ATTR_POE_PORT_ENERGY = "poe_port_energy"
ATTR_TEMPERATURE = "temperature"
ATTR_PORT_COUNT = "port_count"
ATTR_PORTS_UP = "ports_up"
ATTR_PORTS_DOWN = "ports_down"
