"""Binary sensor platform for HP V1910 Switch."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HPV1910DataCoordinator

_LOGGER = logging.getLogger(__name__)


class HPV1910BinaryEntityManager:
    """Manage dynamic binary entities for connected clients."""
    
    def __init__(
        self,
        coordinator: HPV1910DataCoordinator,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Initialize the entity manager."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._async_add_entities = async_add_entities
        self._tracked_clients: set[str] = set()
    
    @callback
    def async_update_items(self) -> None:
        """Update connected client entities."""
        port_devices = self._coordinator.data.get("port_devices", {})
        
        new_entities = []
        
        for port_name, devices in port_devices.items():
            for device in devices:
                mac = device.get("mac_address", "").lower().replace("-", "").replace(":", "")
                if not mac:
                    continue
                
                client_id = f"{mac}"
                
                if client_id not in self._tracked_clients:
                    self._tracked_clients.add(client_id)
                    new_entities.append(
                        HPV1910ClientConnectedSensor(
                            self._coordinator,
                            self._config_entry,
                            mac,
                            device,
                            port_name,
                        )
                    )
        
        if new_entities:
            self._async_add_entities(new_entities)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HP V1910 binary sensors based on a config entry."""
    coordinator: HPV1910DataCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[BinarySensorEntity] = []

    # Add main switch connectivity sensor
    entities.append(HPV1910ConnectivitySensor(coordinator, config_entry))

    # Add fan status sensors for main switch
    if "fans" in coordinator.data:
        for fan in coordinator.data["fans"]:
            fan_id = fan.get("fan_id", 0)
            entities.append(
                HPV1910FanSensor(coordinator, config_entry, fan_id)
            )

    # Add per-port link binary sensors
    if "ports" in coordinator.data:
        for port_data in coordinator.data["ports"]:
            port_name = port_data.get("name", "Unknown")
            entities.append(
                HPV1910PortLinkSensor(coordinator, config_entry, port_name)
            )

    # Add per-port PoE delivering sensors
    if "poe_ports" in coordinator.data:
        for port_data in coordinator.data["poe_ports"]:
            port_name = port_data.get("name", "Unknown")
            entities.append(
                HPV1910PortPoEDeliveringSensor(coordinator, config_entry, port_name)
            )

    # Add connected client binary sensors (connectivity status)
    port_devices = coordinator.data.get("port_devices", {})
    for port_name, devices in port_devices.items():
        for device in devices:
            mac = device.get("mac_address", "")
            if mac:
                entities.append(
                    HPV1910ClientConnectedSensor(coordinator, config_entry, mac, device, port_name)
                )

    async_add_entities(entities)

    # Set up entity manager for dynamic client updates
    entity_manager = HPV1910BinaryEntityManager(coordinator, config_entry, async_add_entities)
    
    # Listen for coordinator updates to add new clients
    config_entry.async_on_unload(
        coordinator.async_add_listener(entity_manager.async_update_items)
    )


class HPV1910ConnectivitySensor(CoordinatorEntity[HPV1910DataCoordinator], BinarySensorEntity):
    """Representation of HP V1910 main switch connectivity status."""

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
        """Return device info for main switch."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name="HP V1910 Switch",
            manufacturer="HP/HPE",
            model=self.coordinator.data.get("device_name", "V1910-24G-PoE"),
            sw_version=self.coordinator.data.get("software_version"),
            hw_version=self.coordinator.data.get("hardware_version"),
            serial_number=self.coordinator.data.get("serial_number"),
            configuration_url=f"http://{self.coordinator.host}",
        )

    @property
    def is_on(self) -> bool:
        """Return True if connected."""
        return self.coordinator.last_update_success


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
        """Return device info for main switch."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name="HP V1910 Switch",
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


class HPV1910PortLinkSensor(CoordinatorEntity[HPV1910DataCoordinator], BinarySensorEntity):
    """Representation of HP V1910 port link status as binary sensor."""

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
        self._port_number = self._extract_port_number(port_name)
        self._attr_unique_id = f"{config_entry.entry_id}_{port_name}_link"
        self._attr_name = "Link"
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
    def is_on(self) -> bool | None:
        """Return True if port is up."""
        port_data = self._get_port_data()
        if port_data:
            return port_data.get("link_status") == "UP"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes including connected devices."""
        port_data = self._get_port_data()
        devices = self._get_connected_devices()
        
        attrs = {}
        
        if port_data:
            attrs["speed"] = port_data.get("speed")
            attrs["duplex"] = port_data.get("duplex")
            attrs["port_type"] = port_data.get("type")
            attrs["pvid"] = port_data.get("pvid")
        
        attrs["connected_device_count"] = len(devices)
        
        if devices:
            ips = [d.get("ip_address") for d in devices if d.get("ip_address")]
            macs = [d.get("mac_address") for d in devices]
            attrs["connected_ips"] = ips
            attrs["connected_macs"] = macs
            if devices:
                first = devices[0]
                attrs["first_device_ip"] = first.get("ip_address", "Unknown")
                attrs["first_device_mac"] = first.get("mac_address", "")
        
        return attrs if attrs else None


class HPV1910PortPoEDeliveringSensor(CoordinatorEntity[HPV1910DataCoordinator], BinarySensorEntity):
    """Representation of HP V1910 port PoE delivering status."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.POWER

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
        self._attr_unique_id = f"{config_entry.entry_id}_{port_name}_poe_delivering"
        self._attr_name = "PoE Delivering"
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
    def is_on(self) -> bool | None:
        """Return True if PoE is delivering power."""
        poe_data = self._get_poe_data()
        if poe_data:
            return poe_data.get("operating_status") == "on"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional PoE attributes."""
        poe_data = self._get_poe_data()
        if poe_data:
            return {
                "power_watts": poe_data.get("power_watts"),
                "poe_enabled": poe_data.get("poe_enabled"),
                "priority": poe_data.get("priority"),
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


class HPV1910ClientConnectedSensor(CoordinatorEntity[HPV1910DataCoordinator], BinarySensorEntity):
    """Binary sensor for connected client status."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: HPV1910DataCoordinator,
        config_entry: ConfigEntry,
        mac_address: str,
        device_info_data: dict,
        port_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._mac_address = mac_address.lower().replace("-", ":").replace(".", ":")
        self._mac_normalized = mac_address.lower().replace("-", "").replace(":", "").replace(".", "")
        self._initial_ip = device_info_data.get("ip_address", "")
        self._initial_port = port_name
        self._port_number = self._extract_port_number(port_name)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_client_{self._mac_normalized}_connected"
        self._attr_name = "Connected"

    def _extract_port_number(self, port_name: str) -> str:
        """Extract port number from name."""
        parts = port_name.split("/")
        if len(parts) >= 3:
            return parts[-1]
        return port_name

    def _get_current_client_data(self) -> tuple[dict | None, str | None]:
        """Find current data for this client across all ports."""
        port_devices = self.coordinator.data.get("port_devices", {})
        for port_name, devices in port_devices.items():
            for device in devices:
                mac = device.get("mac_address", "").lower().replace("-", "").replace(":", "").replace(".", "")
                if mac == self._mac_normalized:
                    return device, port_name
        return None, None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this connected client."""
        device_data, current_port = self._get_current_client_data()
        
        ip = ""
        if device_data:
            ip = device_data.get("ip_address", "")
            current_port = current_port or self._initial_port
        else:
            ip = self._initial_ip
            current_port = self._initial_port
        
        port_number = self._extract_port_number(current_port) if current_port else self._port_number
        
        mac_formatted = ":".join(
            self._mac_normalized[i:i+2].upper() 
            for i in range(0, 12, 2)
        ) if len(self._mac_normalized) == 12 else self._mac_address
        
        if ip:
            name = f"{ip}"
        else:
            name = f"Device {mac_formatted[-8:]}"
        
        port_identifier = f"{self._config_entry.entry_id}_{current_port}"
        
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._config_entry.entry_id}_client_{self._mac_normalized}")},
            connections={("mac", mac_formatted.lower())},
            name=name,
            manufacturer="Network Device",
            model=f"Connected via Port {port_number}",
            via_device=(DOMAIN, port_identifier),
        )

    @property
    def is_on(self) -> bool:
        """Return True if client is currently connected."""
        device_data, _ = self._get_current_client_data()
        return device_data is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional client attributes."""
        device_data, current_port = self._get_current_client_data()
        
        mac_formatted = ":".join(
            self._mac_normalized[i:i+2].upper() 
            for i in range(0, 12, 2)
        ) if len(self._mac_normalized) == 12 else self._mac_address
        
        if device_data:
            return {
                "mac_address": mac_formatted,
                "ip_address": device_data.get("ip_address", "Unknown"),
                "vlan": device_data.get("vlan", 1),
                "port": current_port,
                "port_number": self._extract_port_number(current_port) if current_port else None,
            }
        return {
            "mac_address": mac_formatted,
            "last_known_ip": self._initial_ip or "Unknown",
            "last_known_port": self._initial_port,
        }

    @property
    def icon(self) -> str:
        """Return icon based on connection status."""
        if self.is_on:
            return "mdi:lan-connect"
        return "mdi:lan-disconnect"
