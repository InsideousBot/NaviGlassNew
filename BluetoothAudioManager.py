"""
Bluetooth Audio Manager for NaviGlass
Handles Bluetooth device discovery, pairing, connecting, and setting default audio.
"""

import subprocess
import time
import re
from typing import Optional, List, Dict


class BluetoothAudioManager:
    
    def __init__(self, device_mac: Optional[str] = None):
        self.device_mac = device_mac
        self.connected = False
        
        
    def scan_devices(self, duration: int = 10) -> List[Dict[str, str]]:
        print(f"Scanning for Bluetooth devices for {duration} seconds...")
        
        subprocess.run(["bluetoothctl", "scan", "off"], capture_output=True)
        time.sleep(0.05)

        found_devices = {}

        try:
            proc = subprocess.Popen(
                ["bluetoothctl"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            proc.stdin.write("scan on\n")
            proc.stdin.flush()

            time.sleep(duration)

            proc.stdin.write("scan off\n")
            proc.stdin.flush()

            time.sleep(0.05)

            proc.stdin.write("quit\n")
            proc.stdin.flush()

            stdout, _ = proc.communicate(timeout=5)

            for line in stdout.splitlines():
                if "Device" in line:
                    match = match = re.search(r"Device ([0-9A-Fa-f:]{17}) (.+)", line)
                    if match:
                        mac = match.group(1)
                        name = match.group(2).strip()
                        if name and mac not in found_devices:
                            found_devices[mac] = name

        except subprocess.TimeoutExpired:
            proc.kill()
            print("Scan timed out")
        except Exception as e:
            print(f"Scan error: {e}")

        try:
            result = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "Device" in line:
                    match = match = re.search(r"Device ([0-9A-Fa-f:]{17}) (.+)", line)
                    if match:
                        mac = match.group(1)
                        name = match.group(2).strip()
                        if name and mac not in found_devices:
                            found_devices[mac] = name
        except Exception as e:
            print("Error getting cached devices")

        return [{"mac": k, "name": v} for k, v in found_devices.items()]


    def pair_device(self, mac_address: str) -> bool: 
        if self._is_device_paired(mac_address):
            print(f"Device {mac_address} is already paired.")
            return True

        print(f"Attempting to pair with {mac_address}...")
        subprocess.run(["bluetoothctl", "trust", mac_address], capture_output=True)
        result = subprocess.run(["bluetoothctl", "pair", mac_address], capture_output=True, text=True)
        
        if "pairing successful" in result.stdout.lower() or "already exists" in result.stderr.lower():
            return True
        print(f"Pairing failed: {result.stdout}")
        return False


    def connect_audio(self, mac_address: str) -> bool:
        print(f"Checking connection status for {mac_address}...")

        if self._is_device_connected(mac_address):
            print("Device is already connected via Bluetooth.")
            self.connected = True
            self.device_mac = mac_address
            
            if self._set_default_sink(mac_address):
                self._force_high_quality_profile(mac_address)
                return True
            else:
                print("Warning: Bluetooth connected, but Audio Sink not found.")
                return True # Return True because BT is technically fine

        print("Device not connected. Starting Wake-Up Sequence...")
        
        try: 
            subprocess.run(["bluetoothctl", "disconnect", mac_address], capture_output=True)
        except: pass
        time.sleep(1) 

        try:
            print("Attempt: (Waking device)...")
            subprocess.run(
                ["bluetoothctl", "connect", mac_address],
                capture_output=True,
                text=True,
                timeout=8
            ) 
        except subprocess.TimeoutExpired:
            print("Connection command timed out. Final status check...")
        except Exception as e:
            print(f"Connection error: {e}")

        if self._is_device_connected(mac_address):
            return self._finalize_connection(mac_address)
            
        print("Connection failed.")
        return False


    def disconnect_device(self, mac_address: Optional[str] = None) -> bool:
        target = mac_address if mac_address else self.device_mac
        if not target: return False
        
        print(f"Disconnecting {target}...")
        try:
            subprocess.run(["bluetoothctl", "disconnect", target], capture_output=True, timeout=5)
        except Exception as e:
            print("Disconnect command timed out")
            
        if not self._is_device_connected(target):
            self.connected = False
            if target == self.device_mac: self.device_mac = None
            return True
        return False


    def _finalize_connection(self, mac_address):
        print("Connection Confirmed.")
        self.connected = True
        self.device_mac = mac_address
        if self._set_default_sink(mac_address):
            self._force_high_quality_profile(mac_address)
        return True


    def _is_device_connected(self, mac_address: str) -> bool:
        try:
            res = subprocess.run(
            ["bluetoothctl", "info", mac_address], 
            capture_output=True, 
            text=True,
            timeout=10
        )
            return "Connected: yes" in res.stdout
        except subprocess.TimeoutExpired:
            print("Connection check timed out")
            return False


    def _is_device_paired(self, mac_address: str) -> bool:
        res = subprocess.run(["bluetoothctl", "info", mac_address], capture_output=True, text=True)
        return "Paired: yes" in res.stdout


    def _set_default_sink(self, mac_address: str) -> bool:
        mac_formatted = mac_address.replace(":", "_")
        for i in range(10): 
            result = subprocess.run(["pactl", "list", "short", "sinks"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if mac_formatted in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        sink_name = parts[1]
                    subprocess.run(["pactl", "set-default-sink", sink_name])
                    return True
            time.sleep(0.5)
        return False


    def _force_high_quality_profile(self, mac_address: str):
        mac_formatted = mac_address.replace(":", "_")
        card_name = f"bluez_card.{mac_formatted}"
        profiles = ["a2dp-sink", "a2dp_sink", "a2dp_sink_aac", "a2dp_sink_sbc"]
    
        for profile in profiles:
            try:
                result = subprocess.run(
                    ["pactl", "set-card-profile", card_name, profile], 
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    print(f"Audio profile set to: {profile}")
                    return  # Stop once successful
            except subprocess.TimeoutExpired:
                continue

        print("Warning: Could not set high-quality audio profile")