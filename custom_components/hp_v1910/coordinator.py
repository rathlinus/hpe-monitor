"""Data coordinator for HP V1910 Switch."""
import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .telnet_client import HPV1910TelnetClient

_LOGGER = logging.getLogger(__name__)


class HPV1910DataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage data fetching from HP V1910 switch."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        username: str,
        password: str,
        port: int,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._host = host
        self._username = username
        self._password = password
        self._port = port
        self._client = HPV1910TelnetClient(host, username, password, port)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the switch."""
        try:
            # Create a new client for each update to avoid stale connections
            client = HPV1910TelnetClient(
                self._host, self._username, self._password, self._port
            )
            data = await client.get_all_data()
            
            if "error" in data:
                raise UpdateFailed(f"Failed to fetch data: {data['error']}")
            
            # Build per-port device mapping
            data["port_devices"] = self._build_port_device_mapping(data)
            
            return data
            
        except Exception as err:
            raise UpdateFailed(f"Error communicating with switch: {err}") from err

    def _build_port_device_mapping(self, data: dict[str, Any]) -> dict[str, list[dict]]:
        """Build a mapping of port -> connected devices (IP/MAC)."""
        port_devices = {}
        
        # Build MAC to IP mapping from ARP table
        mac_to_ip = {}
        for arp_entry in data.get("arp_entries", []):
            mac = arp_entry.get("mac_address", "").lower()
            ip = arp_entry.get("ip_address", "")
            if mac and ip:
                mac_to_ip[mac] = ip
        
        # Build port -> devices mapping from MAC table
        for mac_entry in data.get("mac_entries", []):
            port = mac_entry.get("port", "")
            mac = mac_entry.get("mac_address", "").lower()
            
            # Normalize port name (GigabitEthernet1/0/1 -> GE1/0/1)
            if port.startswith("GigabitEthernet"):
                port = port.replace("GigabitEthernet", "GE")
            
            if port not in port_devices:
                port_devices[port] = []
            
            device_info = {
                "mac_address": mac_entry.get("mac_address", ""),
                "ip_address": mac_to_ip.get(mac, ""),
                "vlan": mac_entry.get("vlan", 1),
                "state": mac_entry.get("state", ""),
            }
            port_devices[port].append(device_info)
        
        return port_devices

    @property
    def host(self) -> str:
        """Return the host address."""
        return self._host
