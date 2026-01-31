"""Telnet client for HP V1910 Switch."""
import asyncio
import logging
import re
import telnetlib
from typing import Optional

_LOGGER = logging.getLogger(__name__)


class HPV1910TelnetClient:
    """Telnet client for HP V1910 switches."""

    def __init__(self, host: str, username: str, password: str, port: int = 23, timeout: int = 10):
        """Initialize the telnet client."""
        self._host = host
        self._username = username
        self._password = password
        self._port = port
        self._timeout = timeout
        self._telnet: Optional[telnetlib.Telnet] = None

    async def connect(self) -> bool:
        """Connect to the switch via telnet."""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._connect_sync
            )
        except Exception as err:
            _LOGGER.error("Failed to connect to %s: %s", self._host, err)
            return False

    def _connect_sync(self) -> bool:
        """Synchronous connect method."""
        try:
            self._telnet = telnetlib.Telnet(self._host, self._port, self._timeout)
            
            # Wait for login prompt
            self._telnet.read_until(b"Login:", timeout=self._timeout)
            self._telnet.write(self._username.encode('ascii') + b"\n")
            
            # Wait for password prompt
            self._telnet.read_until(b"Password:", timeout=self._timeout)
            self._telnet.write(self._password.encode('ascii') + b"\n")
            
            # Wait for command prompt (usually ends with > or #)
            response = self._telnet.read_until(b">", timeout=self._timeout)
            
            if b">" in response or b"#" in response:
                _LOGGER.info("Successfully connected to HP V1910 at %s", self._host)
                # Disable paging for full output
                self._send_command_sync("screen-length disable")
                return True
            else:
                _LOGGER.error("Login failed - unexpected response")
                return False
                
        except Exception as err:
            _LOGGER.error("Connection error: %s", err)
            return False

    def _send_command_sync(self, command: str) -> str:
        """Send a command and return the response (synchronous)."""
        if not self._telnet:
            return ""
        
        try:
            self._telnet.write(command.encode('ascii') + b"\n")
            # Read until we see the prompt again
            response = self._telnet.read_until(b">", timeout=self._timeout)
            return response.decode('ascii', errors='ignore')
        except Exception as err:
            _LOGGER.error("Error sending command '%s': %s", command, err)
            return ""

    async def send_command(self, command: str) -> str:
        """Send a command and return the response."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._send_command_sync, command
        )

    async def disconnect(self):
        """Disconnect from the switch."""
        if self._telnet:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._telnet.close
                )
            except Exception:
                pass
            self._telnet = None

    async def get_system_info(self) -> dict:
        """Get system information."""
        data = {}
        
        # Get version info
        response = await self.send_command("display version")
        data["version_raw"] = response
        
        # Parse uptime
        uptime_match = re.search(r"uptime is\s+(.+?)(?:\n|$)", response, re.IGNORECASE)
        if uptime_match:
            data["uptime"] = uptime_match.group(1).strip()
        
        # Parse software version
        sw_match = re.search(r"Software Version\s+(.+?)(?:\n|$)", response, re.IGNORECASE)
        if sw_match:
            data["software_version"] = sw_match.group(1).strip()
        
        # Parse hardware version
        hw_match = re.search(r"Hardware Version\s+(.+?)(?:\n|$)", response, re.IGNORECASE)
        if hw_match:
            data["hardware_version"] = hw_match.group(1).strip()
            
        # Parse bootrom version
        boot_match = re.search(r"Boot(?:rom)?\s+Version\s+(.+?)(?:\n|$)", response, re.IGNORECASE)
        if boot_match:
            data["bootrom_version"] = boot_match.group(1).strip()
        
        return data

    async def get_device_info(self) -> dict:
        """Get device manufacturing info."""
        data = {}
        response = await self.send_command("display device manuinfo")
        data["manuinfo_raw"] = response
        
        # Parse serial number
        serial_match = re.search(r"DEVICE_SERIAL_NUMBER\s*:\s*(.+?)(?:\n|$)", response)
        if serial_match:
            data["serial_number"] = serial_match.group(1).strip()
        
        # Parse device name/model
        name_match = re.search(r"DEVICE_NAME\s*:\s*(.+?)(?:\n|$)", response)
        if name_match:
            data["device_name"] = name_match.group(1).strip()
            
        # Parse MAC address
        mac_match = re.search(r"MAC_ADDRESS\s*:\s*(.+?)(?:\n|$)", response)
        if mac_match:
            data["mac_address"] = mac_match.group(1).strip()
        
        return data

    async def get_cpu_usage(self) -> dict:
        """Get CPU usage information."""
        data = {}
        response = await self.send_command("display cpu-usage")
        data["cpu_raw"] = response
        
        # Parse CPU usage percentage - multiple patterns for different firmware versions
        cpu_patterns = [
            r"CPU\s+usage\s*:\s*(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%\s+in\s+last",
            r"Slot\s+\d+\s+CPU\s+\d+\s+CPU\s+usage\s*:\s*(\d+(?:\.\d+)?)\s*%",
            r"CPU\s+utilization\s*:\s*(\d+(?:\.\d+)?)\s*%",
        ]
        
        for pattern in cpu_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                data["cpu_usage"] = float(match.group(1))
                break
        
        return data

    async def get_memory_usage(self) -> dict:
        """Get memory usage information."""
        data = {}
        response = await self.send_command("display memory")
        data["memory_raw"] = response
        
        # Parse memory info - various patterns
        total_match = re.search(r"Total\s*:\s*(\d+)", response, re.IGNORECASE)
        used_match = re.search(r"Used\s*:\s*(\d+)", response, re.IGNORECASE)
        free_match = re.search(r"Free\s*:\s*(\d+)", response, re.IGNORECASE)
        
        if total_match:
            data["memory_total"] = int(total_match.group(1))
        if used_match:
            data["memory_used"] = int(used_match.group(1))
        if free_match:
            data["memory_free"] = int(free_match.group(1))
        
        # Calculate percentage if we have the values
        if "memory_total" in data and "memory_used" in data and data["memory_total"] > 0:
            data["memory_usage_percent"] = round(
                (data["memory_used"] / data["memory_total"]) * 100, 1
            )
        
        # Alternative parsing for different output format
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:used|usage)", response, re.IGNORECASE)
        if pct_match and "memory_usage_percent" not in data:
            data["memory_usage_percent"] = float(pct_match.group(1))
        
        return data

    async def get_interface_status(self) -> dict:
        """Get interface/port status."""
        data = {"ports": [], "ports_up": 0, "ports_down": 0, "port_count": 0}
        response = await self.send_command("display interface brief")
        data["interface_raw"] = response
        
        # Parse interface lines - looking for GigabitEthernet or similar
        port_pattern = re.compile(
            r"(GE|GigabitEthernet|Gi|Ethernet)\s*(\d+/\d+/?\d*)\s+(\w+)\s+(\w+)",
            re.IGNORECASE
        )
        
        for match in port_pattern.finditer(response):
            port_type = match.group(1)
            port_num = match.group(2)
            link_status = match.group(3)
            
            port_info = {
                "name": f"{port_type}{port_num}",
                "port_number": port_num,
                "link_status": link_status.upper(),
            }
            data["ports"].append(port_info)
            data["port_count"] += 1
            
            if link_status.upper() in ["UP", "CONNECTED"]:
                data["ports_up"] += 1
            else:
                data["ports_down"] += 1
        
        return data

    async def get_poe_status(self) -> dict:
        """Get PoE power status."""
        data = {"poe_ports": []}
        
        # Get overall PoE power state
        response = await self.send_command("display poe power-state")
        data["poe_power_raw"] = response
        
        # Parse total power info
        total_match = re.search(r"(?:Maximum|Total)\s+(?:Power|power)\s*:\s*(\d+(?:\.\d+)?)\s*(?:W|Watts)?", response, re.IGNORECASE)
        if total_match:
            data["poe_power_total"] = float(total_match.group(1))
        
        used_match = re.search(r"(?:Consuming|Used|Current)\s+(?:Power|power)\s*:\s*(\d+(?:\.\d+)?)\s*(?:W|Watts)?", response, re.IGNORECASE)
        if used_match:
            data["poe_power_used"] = float(used_match.group(1))
        
        remaining_match = re.search(r"(?:Remaining|Available)\s+(?:Power|power)\s*:\s*(\d+(?:\.\d+)?)\s*(?:W|Watts)?", response, re.IGNORECASE)
        if remaining_match:
            data["poe_power_remaining"] = float(remaining_match.group(1))
        
        # Get per-interface PoE info
        poe_int_response = await self.send_command("display poe interface")
        data["poe_interface_raw"] = poe_int_response
        
        # Parse per-port PoE status
        poe_port_pattern = re.compile(
            r"(GE|GigabitEthernet|Gi)\s*(\d+/\d+/?\d*)\s+(\w+)\s+(\w+)\s+(\d+(?:\.\d+)?)",
            re.IGNORECASE
        )
        
        for match in poe_port_pattern.finditer(poe_int_response):
            port_info = {
                "name": f"{match.group(1)}{match.group(2)}",
                "poe_status": match.group(3),
                "poe_class": match.group(4),
                "power_watts": float(match.group(5)),
            }
            data["poe_ports"].append(port_info)
        
        return data

    async def get_environment(self) -> dict:
        """Get environmental sensors (temperature, fans)."""
        data = {}
        
        # Get fan status
        fan_response = await self.send_command("display fan")
        data["fan_raw"] = fan_response
        
        # Parse fan status
        fan_pattern = re.compile(r"Fan\s*(\d+)\s*:\s*(\w+)", re.IGNORECASE)
        fans = []
        for match in fan_pattern.finditer(fan_response):
            fans.append({
                "fan_id": int(match.group(1)),
                "status": match.group(2)
            })
        if fans:
            data["fans"] = fans
        
        # Get temperature/environment info
        env_response = await self.send_command("display environment")
        data["environment_raw"] = env_response
        
        # Parse temperature
        temp_match = re.search(r"(?:Temperature|Temp)\s*:\s*(\d+(?:\.\d+)?)\s*(?:C|Celsius)?", env_response, re.IGNORECASE)
        if temp_match:
            data["temperature"] = float(temp_match.group(1))
        
        # Alternative temperature parsing
        temp_match2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:degrees|C)", env_response, re.IGNORECASE)
        if temp_match2 and "temperature" not in data:
            data["temperature"] = float(temp_match2.group(1))
        
        return data

    async def get_lldp_neighbors(self) -> dict:
        """Get LLDP neighbor information."""
        data = {"neighbors": []}
        response = await self.send_command("display lldp neighbor-information brief")
        data["lldp_raw"] = response
        
        # Parse LLDP neighbors - format varies
        neighbor_pattern = re.compile(
            r"(GE|GigabitEthernet|Gi)\s*(\d+/\d+/?\d*)\s+(\S+)\s+(\S+)",
            re.IGNORECASE
        )
        
        for match in neighbor_pattern.finditer(response):
            neighbor = {
                "local_port": f"{match.group(1)}{match.group(2)}",
                "neighbor_device": match.group(3),
                "neighbor_port": match.group(4),
            }
            data["neighbors"].append(neighbor)
        
        return data

    async def get_mac_table(self) -> dict:
        """Get MAC address table."""
        data = {"mac_entries": []}
        response = await self.send_command("display mac-address")
        data["mac_raw"] = response
        
        # Parse MAC entries
        mac_pattern = re.compile(
            r"([0-9a-fA-F]{4}[-\.][0-9a-fA-F]{4}[-\.][0-9a-fA-F]{4})\s+(\d+)\s+(\w+)\s+(\S+)",
            re.IGNORECASE
        )
        
        for match in mac_pattern.finditer(response):
            entry = {
                "mac_address": match.group(1),
                "vlan": int(match.group(2)),
                "type": match.group(3),
                "port": match.group(4),
            }
            data["mac_entries"].append(entry)
        
        data["mac_count"] = len(data["mac_entries"])
        return data

    async def get_vlan_info(self) -> dict:
        """Get VLAN information."""
        data = {"vlans": []}
        response = await self.send_command("display vlan all")
        data["vlan_raw"] = response
        
        # Parse VLAN entries
        vlan_pattern = re.compile(r"VLAN\s+(\d+)\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE)
        
        for match in vlan_pattern.finditer(response):
            vlan = {
                "vlan_id": int(match.group(1)),
                "name": match.group(2).strip(),
            }
            data["vlans"].append(vlan)
        
        data["vlan_count"] = len(data["vlans"])
        return data

    async def get_arp_table(self) -> dict:
        """Get ARP table."""
        data = {"arp_entries": []}
        response = await self.send_command("display arp")
        data["arp_raw"] = response
        
        # Parse ARP entries
        arp_pattern = re.compile(
            r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{4}[-\.][0-9a-fA-F]{4}[-\.][0-9a-fA-F]{4})\s+(\d+)\s+(\S+)\s+(\w+)",
            re.IGNORECASE
        )
        
        for match in arp_pattern.finditer(response):
            entry = {
                "ip_address": match.group(1),
                "mac_address": match.group(2),
                "vlan": int(match.group(3)),
                "interface": match.group(4),
                "type": match.group(5),
            }
            data["arp_entries"].append(entry)
        
        data["arp_count"] = len(data["arp_entries"])
        return data

    async def get_all_data(self) -> dict:
        """Get all available data from the switch."""
        if not await self.connect():
            return {"error": "Connection failed"}
        
        try:
            data = {}
            
            # Gather all data
            system_info = await self.get_system_info()
            data.update(system_info)
            
            device_info = await self.get_device_info()
            data.update(device_info)
            
            cpu_info = await self.get_cpu_usage()
            data.update(cpu_info)
            
            memory_info = await self.get_memory_usage()
            data.update(memory_info)
            
            interface_info = await self.get_interface_status()
            data.update(interface_info)
            
            poe_info = await self.get_poe_status()
            data.update(poe_info)
            
            env_info = await self.get_environment()
            data.update(env_info)
            
            lldp_info = await self.get_lldp_neighbors()
            data.update(lldp_info)
            
            mac_info = await self.get_mac_table()
            data.update(mac_info)
            
            vlan_info = await self.get_vlan_info()
            data.update(vlan_info)
            
            arp_info = await self.get_arp_table()
            data.update(arp_info)
            
            return data
            
        finally:
            await self.disconnect()

    async def test_connection(self) -> bool:
        """Test the connection to the switch."""
        result = await self.connect()
        if result:
            await self.disconnect()
        return result
