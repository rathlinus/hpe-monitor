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
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HPV1910DataCoordinator

_LOGGER = logging.getLogger(__name__)


SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="cpu_usage",
        name="CPU Usage",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cpu-64-bit",
    ),
    SensorEntityDescription(
        key="memory_usage_percent",
        name="Memory Usage",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:memory",
    ),
    SensorEntityDescription(
        key="memory_total",
        name="Memory Total",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:memory",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="memory_used",
        name="Memory Used",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:memory",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="memory_free",
        name="Memory Free",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:memory",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
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
        name="PoE Power Total",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash-circle",
    ),
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
    SensorEntityDescription(
        key="mac_count",
        name="MAC Address Count",
        icon="mdi:counter",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="vlan_count",
        name="VLAN Count",
        icon="mdi:lan",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="arp_count",
        name="ARP Entry Count",
        icon="mdi:table-network",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="uptime",
        name="Uptime",
        icon="mdi:clock-outline",
    ),
    SensorEntityDescription(
        key="software_version",
        name="Software Version",
        icon="mdi:package-variant",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="hardware_version",
        name="Hardware Version",
        icon="mdi:chip",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="bootrom_version",
        name="Bootrom Version",
        icon="mdi:chip",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="serial_number",
        name="Serial Number",
        icon="mdi:identifier",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="device_name",
        name="Device Model",
        icon="mdi:switch",
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="mac_address",
        name="MAC Address",
        icon="mdi:ethernet",
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HP V1910 sensors based on a config entry."""
    coordinator: HPV1910DataCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[HPV1910Sensor] = []

    # Add main sensors
    for description in SENSOR_DESCRIPTIONS:
        entities.append(HPV1910Sensor(coordinator, description, config_entry))

    # Add per-port PoE sensors if PoE data is available
    if "poe_ports" in coordinator.data:
        for port_data in coordinator.data["poe_ports"]:
            port_name = port_data.get("name", "Unknown")
            entities.append(
                HPV1910PoEPortSensor(coordinator, config_entry, port_name)
            )

    # Add per-port link status sensors
    if "ports" in coordinator.data:
        for port_data in coordinator.data["ports"]:
            port_name = port_data.get("name", "Unknown")
            entities.append(
                HPV1910PortStatusSensor(coordinator, config_entry, port_name)
            )

    async_add_entities(entities)


class HPV1910Sensor(CoordinatorEntity[HPV1910DataCoordinator], SensorEntity):
    """Representation of a HP V1910 sensor."""

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
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=f"HP V1910 ({self.coordinator.host})",
            manufacturer="HP/HPE",
            model=self.coordinator.data.get("device_name", "V1910-24G-PoE"),
            sw_version=self.coordinator.data.get("software_version"),
            hw_version=self.coordinator.data.get("hardware_version"),
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        attrs = {}
        
        # Add raw data for debugging if available
        key = self.entity_description.key
        if key == "cpu_usage" and "cpu_raw" in self.coordinator.data:
            attrs["raw_output"] = self.coordinator.data.get("cpu_raw", "")[:500]
        elif key == "memory_usage_percent" and "memory_raw" in self.coordinator.data:
            attrs["raw_output"] = self.coordinator.data.get("memory_raw", "")[:500]
        elif key == "temperature" and "environment_raw" in self.coordinator.data:
            attrs["raw_output"] = self.coordinator.data.get("environment_raw", "")[:500]
        
        return attrs if attrs else None


class HPV1910PoEPortSensor(CoordinatorEntity[HPV1910DataCoordinator], SensorEntity):
    """Representation of a HP V1910 PoE port power sensor."""

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
        self._attr_unique_id = f"{config_entry.entry_id}_poe_{port_name}"
        self._attr_name = f"PoE {port_name}"
        self._config_entry = config_entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=f"HP V1910 ({self.coordinator.host})",
            manufacturer="HP/HPE",
            model=self.coordinator.data.get("device_name", "V1910-24G-PoE"),
        )

    @property
    def native_value(self) -> float | None:
        """Return the PoE power consumption for this port."""
        poe_ports = self.coordinator.data.get("poe_ports", [])
        for port in poe_ports:
            if port.get("name") == self._port_name:
                return port.get("power_watts")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        poe_ports = self.coordinator.data.get("poe_ports", [])
        for port in poe_ports:
            if port.get("name") == self._port_name:
                return {
                    "poe_status": port.get("poe_status"),
                    "poe_class": port.get("poe_class"),
                }
        return None


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
        self._attr_unique_id = f"{config_entry.entry_id}_port_{port_name}"
        self._attr_name = f"Port {port_name}"
        self._config_entry = config_entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=f"HP V1910 ({self.coordinator.host})",
            manufacturer="HP/HPE",
            model=self.coordinator.data.get("device_name", "V1910-24G-PoE"),
        )

    @property
    def native_value(self) -> str | None:
        """Return the link status for this port."""
        ports = self.coordinator.data.get("ports", [])
        for port in ports:
            if port.get("name") == self._port_name:
                return port.get("link_status")
        return None

    @property
    def icon(self) -> str:
        """Return icon based on port status."""
        ports = self.coordinator.data.get("ports", [])
        for port in ports:
            if port.get("name") == self._port_name:
                status = port.get("link_status", "").upper()
                if status in ["UP", "CONNECTED"]:
                    return "mdi:ethernet"
                return "mdi:ethernet-off"
        return "mdi:ethernet-off"
