"""
Separate Web Server for NaviGlass
Reads state from objectDetection.py via JSON files
Provides API and video streaming for static frontend
"""

from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import json
import os
import time
import subprocess

app = Flask(__name__)
CORS(app)  # Enable CORS for GitHub Pages

# File paths
STATE_FILE = "naviglass_state.json"
SETTINGS_FILE = "naviglass_settings.json"
FRAME_FILE = "current_frame.jpg"
CONFIG_FILE = "last_device.txt"


def read_state():
    """Read current state from object detection script."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                # Check if state is stale (older than 5 seconds)
                if time.time() - state.get("timestamp", 0) > 5:
                    return {"distance": 999, "urgent": False, "timestamp": 0, "stale": True}
                return state
        except Exception as e:
            print(f"Failed to read state: {e}")
    
    return {"distance": 999, "urgent": False, "timestamp": 0, "disconnected": True}


def read_settings():
    """Read current settings."""
    defaults = {
        "vibration_intensity": 1.0,
        "bluetooth_mac": None
    }
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                return {**defaults, **settings}
        except Exception as e:
            print(f"Failed to read settings: {e}")
    
    return defaults


def write_settings(settings):
    """Write settings to file."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Failed to write settings: {e}")
        return False


def generate_frames():
    """Stream video frames."""
    # Create a placeholder image if frame file doesn't exist
    placeholder_shown = False
    
    while True:
        if os.path.exists(FRAME_FILE):
            try:
                with open(FRAME_FILE, "rb") as f:
                    frame_data = f.read()
                
                if frame_data:
                    placeholder_shown = False
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
            except Exception as e:
                print(f"Frame read error: {e}")
        else:
            # No frame available - just wait
            if not placeholder_shown:
                print("Warning: No frame file found. Start objectDetection.py first.")
                placeholder_shown = True
        
        time.sleep(0.5)  # Slower polling when no frames


@app.route('/')
def index():
    return jsonify({
        "status": "running", 
        "message": "NaviGlass Web Server. Use the static frontend to interact."
    })


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/status')
def api_status():
    state = read_state()
    settings = read_settings()
    
    return jsonify({
        "distance": state.get("distance", 999),
        "urgent": state.get("urgent", False),
        "vibration_intensity": settings.get("vibration_intensity", 1.0),
        "timestamp": state.get("timestamp", 0)
    })


@app.route('/api/settings/vibration', methods=['POST'])
def api_set_vibration():
    data = request.json
    intensity = data.get('intensity')
    
    if intensity is not None:
        try:
            val = float(intensity)
            if 0.0 <= val <= 1.0:
                settings = read_settings()
                settings['vibration_intensity'] = val
                
                if write_settings(settings):
                    print(f"Vibration intensity set to {val}")
                    return jsonify({"status": "success", "intensity": val})
        except (ValueError, TypeError):
            pass
            
    return jsonify({"status": "error", "message": "Invalid intensity. Must be float 0.0-1.0"}), 400


# --- Bluetooth API Endpoints ---

@app.route('/api/scan')
def api_scan():
    """Scan for Bluetooth devices."""
    try:
        # Use bluetoothctl to scan for devices
        result = subprocess.run(
            ["bluetoothctl", "devices"], 
            capture_output=True, 
            text=True, 
            timeout=12
        )
        
        devices = []
        for line in result.stdout.split('\n'):
            if line.startswith('Device'):
                parts = line.split(' ', 2)
                if len(parts) >= 3:
                    mac = parts[1]
                    name = parts[2] if len(parts) > 2 else "Unknown"
                    devices.append({"mac": mac, "name": name})
        
        return jsonify(devices)
    except Exception as e:
        print(f"Scan error: {e}")
        return jsonify([])


@app.route('/api/pair', methods=['POST'])
def api_pair():
    """Pair with a Bluetooth device."""
    data = request.json
    mac = data.get('mac')
    
    if not mac:
        return jsonify({"status": "error", "message": "No MAC address provided"}), 400
    
    try:
        result = subprocess.run(
            ["bluetoothctl", "pair", mac],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 or "Pairing successful" in result.stdout:
            return jsonify({"status": "success", "message": f"Paired with {mac}"})
        else:
            return jsonify({"status": "error", "message": "Pairing failed"}), 500
    except Exception as e:
        print(f"Pair error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/connect', methods=['POST'])
def api_connect():
    """Connect to a Bluetooth device."""
    data = request.json
    mac = data.get('mac')
    
    if not mac:
        return jsonify({"status": "error", "message": "No MAC address provided"}), 400
    
    try:
        result = subprocess.run(
            ["bluetoothctl", "connect", mac],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 or "Connection successful" in result.stdout:
            # Save to settings
            settings = read_settings()
            settings['bluetooth_mac'] = mac
            write_settings(settings)
            
            # Also save to config file for backward compatibility
            with open(CONFIG_FILE, "w") as f:
                f.write(mac)
            
            return jsonify({"status": "success", "message": f"Connected to {mac}"})
        else:
            return jsonify({"status": "error", "message": "Connection failed"}), 500
    except Exception as e:
        print(f"Connect error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/disconnect', methods=['POST'])
def api_disconnect():
    """Disconnect from a Bluetooth device."""
    data = request.json
    mac = data.get('mac')
    
    if not mac:
        return jsonify({"status": "error", "message": "No MAC address provided"}), 400
    
    try:
        result = subprocess.run(
            ["bluetoothctl", "disconnect", mac],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Clear saved device
        settings = read_settings()
        settings['bluetooth_mac'] = None
        write_settings(settings)
        
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        
        return jsonify({"status": "success", "message": f"Disconnected from {mac}"})
    except Exception as e:
        print(f"Disconnect error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    print("NaviGlass Web Server starting...")
    print("Make sure objectDetection.py is running first!")
    app.run(host='0.0.0.0', port=5000, debug=False)
