"""Sensor platform for HP V1910 Switch."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfInformation,
    UnitOfDataRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HPV1910DataCoordinator

_LOGGER = logging.getLogger(__name__)


# Main switch sensors
SWITCH_SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    # CPU Sensors
    SensorEntityDescription(
        key="cpu_usage",
        name="CPU Usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cpu-64-bit",
    ),
    SensorEntityDescription(
        key="cpu_usage_1m",
        name="CPU Usage (1 min)",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cpu-64-bit",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="cpu_usage_5m",
        name="CPU Usage (5 min)",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cpu-64-bit",
        entity_registry_enabled_default=False,
    ),
    # Memory Sensors
    SensorEntityDescription(
        key="memory_usage_percent",
        name="Memory Usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:memory",
    ),
    # Temperature
    SensorEntityDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # PoE Sensors
    SensorEntityDescription(
        key="poe_power_used",
        name="PoE Power Used",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash",
    ),
    SensorEntityDescription(
        key="poe_power_remaining",
        name="PoE Power Remaining",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash-outline",
    ),
    SensorEntityDescription(
        key="poe_power_total",
        name="PoE Power Budget",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash-circle",
    ),
    SensorEntityDescription(
        key="poe_peak_power",
        name="PoE Peak Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash-alert",
    ),
    SensorEntityDescription(
        key="poe_ports_on",
        name="PoE Ports Active",
        icon="mdi:ethernet",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Port Sensors
    SensorEntityDescription(
        key="port_count",
        name="Total Ports",
        icon="mdi:ethernet",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="ports_up",
        name="Ports Up",
        icon="mdi:ethernet",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="ports_down",
        name="Ports Down",
        icon="mdi:ethernet-off",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Network Sensors
    SensorEntityDescription(
        key="mac_count",
        name="MAC Address Count",
        icon="mdi:counter",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="arp_count",
        name="ARP Entry Count",
        icon="mdi:table-network",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # System Info
    SensorEntityDescription(
        key="uptime",
        name="Uptime",
        icon="mdi:clock-outline",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HP V1910 sensors based on a config entry."""
    coordinator: HPV1910DataCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[SensorEntity] = []

    # Add main switch sensors
    for description in SWITCH_SENSOR_DESCRIPTIONS:
        entities.append(HPV1910SwitchSensor(coordinator, description, config_entry))

    # Add per-port sensors (each port is a separate device)
    if "ports" in coordinator.data:
        for port_data in coordinator.data["ports"]:
            port_name = port_data.get("name", "Unknown")
            
            # Add port status sensor
            entities.append(
                HPV1910PortStatusSensor(coordinator, config_entry, port_name)
            )
            
            # Add connected devices sensor
            entities.append(
                HPV1910PortConnectedDevicesSensor(coordinator, config_entry, port_name)
            )

    # Add per-port PoE sensors
    if "poe_ports" in coordinator.data:
        for port_data in coordinator.data["poe_ports"]:
            port_name = port_data.get("name", "Unknown")
            entities.append(
                HPV1910PortPoESensor(coordinator, config_entry, port_name)
            )

    async_add_entities(entities)


class HPV1910SwitchSensor(CoordinatorEntity[HPV1910DataCoordinator], SensorEntity):
    """Representation of a HP V1910 main switch sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HPV1910DataCoordinator,
        description: SensorEntityDescription,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"
        self._config_entry = config_entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the main switch."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=f"HP V1910 Switch",
            manufacturer="HP/HPE",
            model=self.coordinator.data.get("device_name", "V1910-24G-PoE"),
            sw_version=self.coordinator.data.get("software_version"),
            hw_version=self.coordinator.data.get("hardware_version"),
            serial_number=self.coordinator.data.get("serial_number"),
            configuration_url=f"http://{self.coordinator.host}",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)


class HPV1910PortStatusSensor(CoordinatorEntity[HPV1910DataCoordinator], SensorEntity):
    """Representation of a HP V1910 port status sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:ethernet"

    def __init__(
        self,
        coordinator: HPV1910DataCoordinator,
        config_entry: ConfigEntry,
        port_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._port_name = port_name
        self._port_number = self._extract_port_number(port_name)
        self._attr_unique_id = f"{config_entry.entry_id}_{port_name}_status"
        self._attr_name = "Status"
        self._config_entry = config_entry

    def _extract_port_number(self, port_name: str) -> str:
        """Extract port number from name like GE1/0/1 -> 1."""
        parts = port_name.split("/")
        if len(parts) >= 3:
            return parts[-1]
        return port_name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this port."""
        # Get port-specific info
        port_data = self._get_port_data()
        connected_devices = self._get_connected_devices()
        
        # Build model string with connection info
        model = f"Switch Port {self._port_number}"
        if port_data and port_data.get("link_status") == "UP":
            speed = port_data.get("speed", "")
            model = f"Port {self._port_number} ({speed})"
        
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._config_entry.entry_id}_{self._port_name}")},
            name=f"Port {self._port_number}",
            manufacturer="HP/HPE",
            model=model,
            via_device=(DOMAIN, self._config_entry.entry_id),
        )

    def _get_port_data(self) -> dict | None:
        """Get port data from coordinator."""
        ports = self.coordinator.data.get("ports", [])
        for port in ports:
            if port.get("name") == self._port_name:
                return port
        return None

    def _get_connected_devices(self) -> list[dict]:
        """Get connected devices for this port."""
        port_devices = self.coordinator.data.get("port_devices", {})
        return port_devices.get(self._port_name, [])

    @property
    def native_value(self) -> str | None:
        """Return the link status."""
        port_data = self._get_port_data()
        if port_data:
            return port_data.get("link_status")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        port_data = self._get_port_data()
        if port_data:
            return {
                "speed": port_data.get("speed"),
                "duplex": port_data.get("duplex"),
                "port_type": port_data.get("type"),
                "pvid": port_data.get("pvid"),
                "port_name": self._port_name,
            }
        return None

    @property
    def icon(self) -> str:
        """Return icon based on port status."""
        port_data = self._get_port_data()
        if port_data and port_data.get("link_status") == "UP":
            return "mdi:ethernet"
        return "mdi:ethernet-off"


class HPV1910PortConnectedDevicesSensor(CoordinatorEntity[HPV1910DataCoordinator], SensorEntity):
    """Sensor showing connected devices on a port."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:devices"

    def __init__(
        self,
        coordinator: HPV1910DataCoordinator,
        config_entry: ConfigEntry,
        port_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._port_name = port_name
        self._port_number = self._extract_port_number(port_name)
        self._attr_unique_id = f"{config_entry.entry_id}_{port_name}_connected"
        self._attr_name = "Connected Devices"
        self._config_entry = config_entry

    def _extract_port_number(self, port_name: str) -> str:
        """Extract port number from name."""
        parts = port_name.split("/")
        if len(parts) >= 3:
            return parts[-1]
        return port_name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this port."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._config_entry.entry_id}_{self._port_name}")},
            name=f"Port {self._port_number}",
            manufacturer="HP/HPE",
            via_device=(DOMAIN, self._config_entry.entry_id),
        )

    def _get_connected_devices(self) -> list[dict]:
        """Get connected devices for this port."""
        port_devices = self.coordinator.data.get("port_devices", {})
        return port_devices.get(self._port_name, [])

    @property
    def native_value(self) -> int:
        """Return the number of connected devices."""
        return len(self._get_connected_devices())

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return connected devices as attributes."""
        devices = self._get_connected_devices()
        if not devices:
            return {"devices": [], "device_list": "None"}
        
        # Build device list string
        device_list = []
        device_details = []
        
        for i, dev in enumerate(devices):
            ip = dev.get("ip_address", "")
            mac = dev.get("mac_address", "")
            
            if ip:
                device_list.append(f"{ip} ({mac})")
            else:
                device_list.append(mac)
            
            device_details.append({
                "ip": ip or "Unknown",
                "mac": mac,
                "vlan": dev.get("vlan", 1),
            })
        
        # Also add individual device attributes for easy access
        attrs = {
            "device_count": len(devices),
            "device_list": ", ".join(device_list),
            "devices": device_details,
        }
        
        # Add first few devices as direct attributes
        for i, dev in enumerate(devices[:5]):
            prefix = f"device_{i+1}"
            attrs[f"{prefix}_ip"] = dev.get("ip_address", "Unknown")
            attrs[f"{prefix}_mac"] = dev.get("mac_address", "")
        
        return attrs


class HPV1910PortPoESensor(CoordinatorEntity[HPV1910DataCoordinator], SensorEntity):
    """Representation of a HP V1910 port PoE power sensor."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:flash"

    def __init__(
        self,
        coordinator: HPV1910DataCoordinator,
        config_entry: ConfigEntry,
        port_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._port_name = port_name
        self._port_number = self._extract_port_number(port_name)
        self._attr_unique_id = f"{config_entry.entry_id}_{port_name}_poe"
        self._attr_name = "PoE Power"
        self._config_entry = config_entry

    def _extract_port_number(self, port_name: str) -> str:
        """Extract port number from name."""
        parts = port_name.split("/")
        if len(parts) >= 3:
            return parts[-1]
        return port_name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this port."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._config_entry.entry_id}_{self._port_name}")},
            name=f"Port {self._port_number}",
            manufacturer="HP/HPE",
            via_device=(DOMAIN, self._config_entry.entry_id),
        )

    def _get_poe_data(self) -> dict | None:
        """Get PoE data for this port."""
        poe_ports = self.coordinator.data.get("poe_ports", [])
        for port in poe_ports:
            if port.get("name") == self._port_name:
                return port
        return None

    @property
    def native_value(self) -> float | None:
        """Return the PoE power consumption."""
        poe_data = self._get_poe_data()
        if poe_data:
            return poe_data.get("power_watts")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional PoE attributes."""
        poe_data = self._get_poe_data()
        if poe_data:
            return {
                "poe_enabled": poe_data.get("poe_enabled"),
                "priority": poe_data.get("priority"),
                "operating_status": poe_data.get("operating_status"),
                "ieee_class": poe_data.get("ieee_class"),
                "detection_status": poe_data.get("detection_status"),
            }
        return None

    @property
    def icon(self) -> str:
        """Return icon based on PoE status."""
        poe_data = self._get_poe_data()
        if poe_data and poe_data.get("operating_status") == "on":
            return "mdi:flash"
        return "mdi:flash-off"
