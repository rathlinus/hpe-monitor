"""Binary sensor platform for HP V1910 Switch."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HPV1910DataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HP V1910 binary sensors based on a config entry."""
    coordinator: HPV1910DataCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[BinarySensorEntity] = []

    # Add overall switch connectivity sensor
    entities.append(HPV1910ConnectivitySensor(coordinator, config_entry))

    # Add per-port link binary sensors
    if "ports" in coordinator.data:
        for port_data in coordinator.data["ports"]:
            port_name = port_data.get("name", "Unknown")
            entities.append(
                HPV1910PortLinkSensor(coordinator, config_entry, port_name)
            )

    # Add fan status sensors
    if "fans" in coordinator.data:
        for fan in coordinator.data["fans"]:
            fan_id = fan.get("fan_id", 0)
            entities.append(
                HPV1910FanSensor(coordinator, config_entry, fan_id)
            )

    # Add per-port PoE delivering sensors
    if "poe_ports" in coordinator.data:
        for port_data in coordinator.data["poe_ports"]:
            port_name = port_data.get("name", "Unknown")
            entities.append(
                HPV1910PoEDeliveringSensor(coordinator, config_entry, port_name)
            )

    async_add_entities(entities)


class HPV1910ConnectivitySensor(CoordinatorEntity[HPV1910DataCoordinator], BinarySensorEntity):
    """Representation of HP V1910 connectivity status."""

    _attr_has_entity_name = True
    _attr_name = "Connectivity"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: HPV1910DataCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{config_entry.entry_id}_connectivity"
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
            serial_number=self.coordinator.data.get("serial_number"),
        )

    @property
    def is_on(self) -> bool:
        """Return True if connected."""
        return self.coordinator.last_update_success


class HPV1910PortLinkSensor(CoordinatorEntity[HPV1910DataCoordinator], BinarySensorEntity):
    """Representation of HP V1910 port link status."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: HPV1910DataCoordinator,
        config_entry: ConfigEntry,
        port_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._port_name = port_name
        self._attr_unique_id = f"{config_entry.entry_id}_link_{port_name}"
        self._attr_name = f"Link {port_name}"
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
    def is_on(self) -> bool | None:
        """Return True if port is up."""
        ports = self.coordinator.data.get("ports", [])
        for port in ports:
            if port.get("name") == self._port_name:
                return port.get("link_status") == "UP"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        ports = self.coordinator.data.get("ports", [])
        for port in ports:
            if port.get("name") == self._port_name:
                return {
                    "speed": port.get("speed"),
                    "duplex": port.get("duplex"),
                    "type": port.get("type"),
                    "pvid": port.get("pvid"),
                }
        return None


class HPV1910FanSensor(CoordinatorEntity[HPV1910DataCoordinator], BinarySensorEntity):
    """Representation of HP V1910 fan status."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: HPV1910DataCoordinator,
        config_entry: ConfigEntry,
        fan_id: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._fan_id = fan_id
        self._attr_unique_id = f"{config_entry.entry_id}_fan_{fan_id}"
        self._attr_name = f"Fan {fan_id}"
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
    def is_on(self) -> bool | None:
        """Return True if fan is running normally."""
        fans = self.coordinator.data.get("fans", [])
        for fan in fans:
            if fan.get("fan_id") == self._fan_id:
                status = fan.get("status", "").lower()
                return status in ["normal", "ok", "running"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        fans = self.coordinator.data.get("fans", [])
        for fan in fans:
            if fan.get("fan_id") == self._fan_id:
                return {"status": fan.get("status")}
        return None


class HPV1910PoEDeliveringSensor(CoordinatorEntity[HPV1910DataCoordinator], BinarySensorEntity):
    """Representation of HP V1910 PoE port delivering power status."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.POWER
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
        self._attr_unique_id = f"{config_entry.entry_id}_poe_delivering_{port_name}"
        self._attr_name = f"PoE Delivering {port_name}"
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
    def is_on(self) -> bool | None:
        """Return True if PoE is delivering power."""
        poe_ports = self.coordinator.data.get("poe_ports", [])
        for port in poe_ports:
            if port.get("name") == self._port_name:
                return port.get("operating_status") == "on"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        poe_ports = self.coordinator.data.get("poe_ports", [])
        for port in poe_ports:
            if port.get("name") == self._port_name:
                return {
                    "poe_enabled": port.get("poe_enabled"),
                    "priority": port.get("priority"),
                    "power_watts": port.get("power_watts"),
                    "ieee_class": port.get("ieee_class"),
                    "detection_status": port.get("detection_status"),
                }
        return None

    @property
    def icon(self) -> str:
        """Return icon based on PoE status."""
        poe_ports = self.coordinator.data.get("poe_ports", [])
        for port in poe_ports:
            if port.get("name") == self._port_name:
                if port.get("operating_status") == "on":
                    return "mdi:flash"
                return "mdi:flash-off"
        return "mdi:flash-off"
