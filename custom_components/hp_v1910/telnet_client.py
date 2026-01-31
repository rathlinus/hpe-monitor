"""Telnet client for HP V1910 Switch."""
import asyncio
import logging
import re
import telnetlib
from typing import Optional

_LOGGER = logging.getLogger(__name__)

# Hidden password to unlock full CLI mode on HP V1910
CMDLINE_MODE_PASSWORD = "512900"


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
            _LOGGER.debug("Attempting telnet connection to %s:%s", self._host, self._port)
            self._telnet = telnetlib.Telnet(self._host, self._port, self._timeout)
            _LOGGER.debug("Telnet connection established, waiting for login prompt")
            
            # Wait for login prompt - handle variations
            response = self._telnet.read_until(b":", timeout=self._timeout)
            response_str = response.decode('ascii', errors='ignore').lower()
            _LOGGER.debug("Initial response: %s", response_str[-200:] if len(response_str) > 200 else response_str)
            
            # Check if this is a login or username prompt
            if "login" in response_str or "username" in response_str or "user" in response_str:
                self._telnet.write(self._username.encode('ascii') + b"\n")
            else:
                _LOGGER.warning("Unexpected prompt (expected login): %s", response_str[-100:])
                self._telnet.write(self._username.encode('ascii') + b"\n")
            
            # Wait for password prompt
            response = self._telnet.read_until(b":", timeout=self._timeout)
            response_str = response.decode('ascii', errors='ignore').lower()
            _LOGGER.debug("Password prompt response: %s", response_str[-100:] if len(response_str) > 100 else response_str)
            
            if "password" in response_str or "pass" in response_str:
                self._telnet.write(self._password.encode('ascii') + b"\n")
            else:
                _LOGGER.warning("Unexpected prompt (expected password): %s", response_str[-100:])
                self._telnet.write(self._password.encode('ascii') + b"\n")
            
            # Wait for command prompt (ends with > or #)
            response = self._telnet.read_until(b">", timeout=self._timeout)
            response_str = response.decode('ascii', errors='ignore')
            _LOGGER.debug("Login response: %s", response_str[-200:] if len(response_str) > 200 else response_str)
            
            # Check for authentication failure indicators
            if "invalid" in response_str.lower() or "failed" in response_str.lower() or "denied" in response_str.lower():
                _LOGGER.error("Authentication failed - invalid credentials")
                return False
            
            if b">" not in response and b"#" not in response:
                _LOGGER.error("Login failed - no command prompt received. Response: %s", response_str[-200:])
                return False
            
            _LOGGER.info("Successfully connected to HP V1910 at %s", self._host)
            
            # Enable full CLI mode with _cmdline-mode on
            if not self._enable_cmdline_mode():
                _LOGGER.warning("Could not enable full CLI mode, some commands may not work")
            
            return True
                
        except ConnectionRefusedError:
            _LOGGER.error("Connection refused by %s:%s - telnet may be disabled", self._host, self._port)
            return False
        except TimeoutError:
            _LOGGER.error("Connection timeout to %s:%s - check network/firewall", self._host, self._port)
            return False
        except OSError as err:
            _LOGGER.error("Network error connecting to %s:%s: %s", self._host, self._port, err)
            return False
        except Exception as err:
            _LOGGER.error("Connection error to %s:%s: %s", self._host, self._port, err)
            return False

    def _enable_cmdline_mode(self) -> bool:
        """Enable full CLI mode using _cmdline-mode on."""
        try:
            self._telnet.write(b"_cmdline-mode on\n")
            response = self._telnet.read_until(b"[Y/N]", timeout=5)
            
            if b"[Y/N]" in response:
                self._telnet.write(b"Y\n")
                response = self._telnet.read_until(b":", timeout=5)
                
                if b"password" in response.lower():
                    self._telnet.write(CMDLINE_MODE_PASSWORD.encode('ascii') + b"\n")
                    response = self._telnet.read_until(b">", timeout=5)
                    
                    if b">" in response:
                        _LOGGER.info("Full CLI mode enabled")
                        return True
            
            return False
        except Exception as err:
            _LOGGER.warning("Error enabling cmdline mode: %s", err)
            return False

    def _send_command_sync(self, command: str) -> str:
        """Send a command and return the response (synchronous)."""
        if not self._telnet:
            return ""
        
        try:
            self._telnet.write(command.encode('ascii') + b"\n")
            
            # Read response and handle paging
            full_response = ""
            for _ in range(20):  # Max 20 pages
                response = self._telnet.read_until(b">", timeout=self._timeout)
                decoded = response.decode('ascii', errors='ignore')
                full_response += decoded
                
                # Check for "More" prompt
                if "---- More ----" in decoded:
                    # Remove the More prompt from output and press space
                    full_response = full_response.replace("---- More ----", "")
                    self._telnet.write(b" ")
                else:
                    break
            
            return full_response
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
        
        # Parse uptime - "uptime is 0 week, 2 days, 0 hour, 1 minute"
        uptime_match = re.search(r"uptime is\s+(.+?)(?:\n|$)", response, re.IGNORECASE)
        if uptime_match:
            data["uptime"] = uptime_match.group(1).strip()
        
        # Parse software version - "Version 5.20 Release 1111P02"
        sw_match = re.search(r"Version\s+(\d+\.\d+\s+Release\s+\S+)", response, re.IGNORECASE)
        if sw_match:
            data["software_version"] = sw_match.group(1).strip()
        
        # Parse hardware version
        hw_match = re.search(r"Hardware Version is\s+(\S+)", response, re.IGNORECASE)
        if hw_match:
            data["hardware_version"] = hw_match.group(1).strip()
            
        # Parse bootrom version
        boot_match = re.search(r"Bootrom Version is\s+(\S+)", response, re.IGNORECASE)
        if boot_match:
            data["bootrom_version"] = boot_match.group(1).strip()
        
        # Parse DRAM
        dram_match = re.search(r"(\d+)M?\s+bytes\s+DRAM", response, re.IGNORECASE)
        if dram_match:
            data["dram_mb"] = int(dram_match.group(1))
        
        return data

    async def get_device_info(self) -> dict:
        """Get device manufacturing info."""
        data = {}
        response = await self.send_command("display device manuinfo")
        data["manuinfo_raw"] = response
        
        # Parse device name/model
        name_match = re.search(r"DEVICE_NAME\s*:\s*(.+?)(?:\n|$)", response)
        if name_match:
            data["device_name"] = name_match.group(1).strip()
        
        # Parse serial number
        serial_match = re.search(r"DEVICE_SERIAL_NUMBER\s*:\s*(.+?)(?:\n|$)", response)
        if serial_match:
            data["serial_number"] = serial_match.group(1).strip()
            
        # Parse MAC address
        mac_match = re.search(r"MAC_ADDRESS\s*:\s*(.+?)(?:\n|$)", response)
        if mac_match:
            data["mac_address"] = mac_match.group(1).strip()
        
        # Parse manufacturing date
        date_match = re.search(r"MANUFACTURING_DATE\s*:\s*(.+?)(?:\n|$)", response)
        if date_match:
            data["manufacturing_date"] = date_match.group(1).strip()
        
        return data

    async def get_cpu_usage(self) -> dict:
        """Get CPU usage information."""
        data = {}
        response = await self.send_command("display cpu-usage")
        data["cpu_raw"] = response
        
        # Parse "9% in last 5 seconds"
        cpu_5s_match = re.search(r"(\d+)%\s+in\s+last\s+5\s+seconds", response, re.IGNORECASE)
        if cpu_5s_match:
            data["cpu_usage"] = int(cpu_5s_match.group(1))
            data["cpu_usage_5s"] = int(cpu_5s_match.group(1))
        
        # Parse "7% in last 1 minute"
        cpu_1m_match = re.search(r"(\d+)%\s+in\s+last\s+1\s+minute", response, re.IGNORECASE)
        if cpu_1m_match:
            data["cpu_usage_1m"] = int(cpu_1m_match.group(1))
        
        # Parse "10% in last 5 minutes"
        cpu_5m_match = re.search(r"(\d+)%\s+in\s+last\s+5\s+minutes", response, re.IGNORECASE)
        if cpu_5m_match:
            data["cpu_usage_5m"] = int(cpu_5m_match.group(1))
        
        return data

    async def get_memory_usage(self) -> dict:
        """Get memory usage information."""
        data = {}
        response = await self.send_command("display memory")
        data["memory_raw"] = response
        
        # Parse "System Total Memory(bytes): 81806560"
        total_match = re.search(r"Total\s+Memory\s*\(bytes\)\s*:\s*(\d+)", response, re.IGNORECASE)
        if total_match:
            data["memory_total"] = int(total_match.group(1))
        
        # Parse "Total Used Memory(bytes): 26663832"
        used_match = re.search(r"Used\s+Memory\s*\(bytes\)\s*:\s*(\d+)", response, re.IGNORECASE)
        if used_match:
            data["memory_used"] = int(used_match.group(1))
        
        # Parse "Used Rate: 32%"
        rate_match = re.search(r"Used\s+Rate\s*:\s*(\d+)%", response, re.IGNORECASE)
        if rate_match:
            data["memory_usage_percent"] = int(rate_match.group(1))
        
        # Calculate free memory
        if "memory_total" in data and "memory_used" in data:
            data["memory_free"] = data["memory_total"] - data["memory_used"]
        
        return data

    async def get_interface_status(self) -> dict:
        """Get interface/port status."""
        data = {"ports": [], "ports_up": 0, "ports_down": 0, "port_count": 0}
        response = await self.send_command("display brief interface")
        data["interface_raw"] = response
        
        # Parse interface lines under bridge mode
        # GE1/0/1              UP   1G(a)   F(a)   A    1
        port_pattern = re.compile(
            r"(GE\d+/\d+/\d+)\s+(UP|DOWN)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\d+)",
            re.IGNORECASE
        )
        
        for match in port_pattern.finditer(response):
            port_name = match.group(1)
            link_status = match.group(2).upper()
            speed = match.group(3)
            duplex = match.group(4)
            port_type = match.group(5)
            pvid = match.group(6)
            
            port_info = {
                "name": port_name,
                "link_status": link_status,
                "speed": speed,
                "duplex": duplex,
                "type": port_type,
                "pvid": int(pvid),
            }
            data["ports"].append(port_info)
            data["port_count"] += 1
            
            if link_status == "UP":
                data["ports_up"] += 1
            else:
                data["ports_down"] += 1
        
        return data

    async def get_poe_interface_status(self) -> dict:
        """Get per-port PoE status."""
        data = {"poe_ports": []}
        response = await self.send_command("display poe interface")
        data["poe_interface_raw"] = response
        
        # Parse: GE1/0/1      enabled  low      4.7      on         4      delivering-power
        poe_pattern = re.compile(
            r"(GE\d+/\d+/\d+)\s+(enabled|disabled)\s+(\w+)\s+([\d.]+)\s+(\w+)\s+(\d+)\s+(\S+)",
            re.IGNORECASE
        )
        
        for match in poe_pattern.finditer(response):
            port_info = {
                "name": match.group(1),
                "poe_enabled": match.group(2).lower() == "enabled",
                "priority": match.group(3),
                "power_watts": float(match.group(4)),
                "operating_status": match.group(5),
                "ieee_class": int(match.group(6)),
                "detection_status": match.group(7),
            }
            data["poe_ports"].append(port_info)
        
        # Parse summary line: "---  3 port(s) on,    17.9 (W) consumed,   352.1 (W) remaining ---"
        summary_match = re.search(
            r"(\d+)\s+port\(s\)\s+on,\s+([\d.]+)\s+\(W\)\s+consumed,\s+([\d.]+)\s+\(W\)\s+remaining",
            response,
            re.IGNORECASE
        )
        if summary_match:
            data["poe_ports_on"] = int(summary_match.group(1))
            data["poe_power_used"] = float(summary_match.group(2))
            data["poe_power_remaining"] = float(summary_match.group(3))
        
        return data

    async def get_poe_pse_status(self) -> dict:
        """Get PSE (Power Sourcing Equipment) status."""
        data = {}
        response = await self.send_command("display poe pse")
        data["poe_pse_raw"] = response
        
        # Parse PSE Current Power: 18 W
        current_match = re.search(r"PSE Current Power\s*:\s*(\d+)\s*W", response, re.IGNORECASE)
        if current_match:
            data["poe_current_power"] = int(current_match.group(1))
        
        # Parse PSE Average Power: 18 W
        avg_match = re.search(r"PSE Average Power\s*:\s*(\d+)\s*W", response, re.IGNORECASE)
        if avg_match:
            data["poe_average_power"] = int(avg_match.group(1))
        
        # Parse PSE Peak Power: 27 W
        peak_match = re.search(r"PSE Peak Power\s*:\s*(\d+)\s*W", response, re.IGNORECASE)
        if peak_match:
            data["poe_peak_power"] = int(peak_match.group(1))
        
        # Parse PSE Max Power: 370 W
        max_match = re.search(r"PSE Max Power\s*:\s*(\d+)\s*W", response, re.IGNORECASE)
        if max_match:
            data["poe_power_total"] = int(max_match.group(1))
        
        # Parse PSE Remaining Guaranteed: 370 W
        remaining_match = re.search(r"PSE Remaining Guaranteed\s*:\s*(\d+)\s*W", response, re.IGNORECASE)
        if remaining_match:
            data["poe_power_guaranteed_remaining"] = int(remaining_match.group(1))
        
        # Parse utilization threshold
        util_match = re.search(r"PSE Utilization-threshold\s*:\s*(\d+)", response, re.IGNORECASE)
        if util_match:
            data["poe_utilization_threshold"] = int(util_match.group(1))
        
        return data

    async def get_environment(self) -> dict:
        """Get environmental sensors (temperature, fans)."""
        data = {}
        
        # Get fan status
        fan_response = await self.send_command("display fan")
        data["fan_raw"] = fan_response
        
        # Parse "Fan   1 State: Normal"
        fan_pattern = re.compile(r"Fan\s+(\d+)\s+State:\s*(\w+)", re.IGNORECASE)
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
        
        # Parse temperature table
        # hotspot 1      45        NA              85          95         NA
        temp_pattern = re.compile(
            r"hotspot\s+(\d+)\s+(\d+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(\S+)",
            re.IGNORECASE
        )
        
        temperatures = []
        for match in temp_pattern.finditer(env_response):
            temp_info = {
                "sensor_id": int(match.group(1)),
                "temperature": int(match.group(2)),
                "warning_limit": int(match.group(4)),
                "alarm_limit": int(match.group(5)),
            }
            temperatures.append(temp_info)
        
        if temperatures:
            data["temperatures"] = temperatures
            # Use highest temperature as main value
            data["temperature"] = max(t["temperature"] for t in temperatures)
        
        return data

    async def get_mac_table(self) -> dict:
        """Get MAC address table."""
        data = {"mac_entries": []}
        response = await self.send_command("display mac-address")
        data["mac_raw"] = response
        
        # Parse: 001b-e018-8c69  1        LEARNED         GigabitEthernet1/0/10     AGING
        mac_pattern = re.compile(
            r"([0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4})\s+(\d+)\s+(\w+)\s+(GigabitEthernet\d+/\d+/\d+)\s+(\w+)",
            re.IGNORECASE
        )
        
        for match in mac_pattern.finditer(response):
            entry = {
                "mac_address": match.group(1),
                "vlan": int(match.group(2)),
                "state": match.group(3),
                "port": match.group(4),
                "aging": match.group(5),
            }
            data["mac_entries"].append(entry)
        
        # Parse count: "---  29 MAC address(es) found  ---"
        count_match = re.search(r"(\d+)\s+MAC\s+address", response, re.IGNORECASE)
        if count_match:
            data["mac_count"] = int(count_match.group(1))
        else:
            data["mac_count"] = len(data["mac_entries"])
        
        return data

    async def get_vlan_info(self) -> dict:
        """Get VLAN information."""
        data = {"vlans": []}
        response = await self.send_command("display vlan all")
        data["vlan_raw"] = response
        
        # Parse VLAN entries
        vlan_pattern = re.compile(
            r"VLAN ID:\s*(\d+).*?Name:\s*(.+?)(?:\n|Tagged)",
            re.IGNORECASE | re.DOTALL
        )
        
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
        
        # Parse: 192.168.1.112    88a2-9e1a-0791  1        GE1/0/1                20    D
        arp_pattern = re.compile(
            r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4})\s+(\d+)\s+(GE\d+/\d+/\d+)\s+(\d+)\s+(\w)",
            re.IGNORECASE
        )
        
        for match in arp_pattern.finditer(response):
            entry = {
                "ip_address": match.group(1),
                "mac_address": match.group(2),
                "vlan": int(match.group(3)),
                "interface": match.group(4),
                "aging": int(match.group(5)),
                "type": "Dynamic" if match.group(6).upper() == "D" else "Static",
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
            
            poe_interface_info = await self.get_poe_interface_status()
            data.update(poe_interface_info)
            
            poe_pse_info = await self.get_poe_pse_status()
            data.update(poe_pse_info)
            
            env_info = await self.get_environment()
            data.update(env_info)
            
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
