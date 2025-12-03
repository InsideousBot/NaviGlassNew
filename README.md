# NaviGlass - Separated Architecture

This project now uses a **completely separated architecture** with three distinct components:

## Architecture Overview

```
┌─────────────────────────┐
│  objectDetection.py     │  ← Main NaviGlass logic (NO Flask)
│  - YOLO object detection│
│  - Distance sensing     │
│  - Vibration control    │
│  - TTS & Bluetooth      │
└───────────┬─────────────┘
            │ Writes to
            ▼
┌─────────────────────────┐
│  Shared JSON Files      │
│  - naviglass_state.json │  ← Current status
│  - naviglass_settings.json│  ← User settings
│  - current_frame.jpg    │  ← Latest frame
└───────────┬─────────────┘
            │ Reads from
            ▼
┌─────────────────────────┐
│  web_server.py          │  ← Flask API server
│  - REST API endpoints   │
│  - Video streaming      │
│  - CORS enabled         │
└───────────┬─────────────┘
            │ HTTP requests
            ▼
┌─────────────────────────┐
│  web/index.html         │  ← Static frontend (GitHub Pages)
│  - Live video feed      │
│  - Emergency alerts     │
│  - Bluetooth controls   │
│  - Vibration settings   │
└─────────────────────────┘
```

## Files

### Core Detection (No Web)
- **objectDetection.py** - Main NaviGlass object detection and control
  - No Flask dependency
  - Reads settings from `naviglass_settings.json`
  - Writes state to `naviglass_state.json`
  - Saves frames to `current_frame.jpg`

### Web Server (Separate Process)
- **web_server.py** - Flask API server
  - Reads state from JSON files
  - Provides REST API endpoints
  - Streams video feed
  - CORS enabled for GitHub Pages

### Static Frontend
- **web/index.html** - Standalone HTML page
  - Can be hosted on GitHub Pages
  - Configurable server URL
  - Premium dark theme with glassmorphism
  - Real-time telemetry
  - Bluetooth management
  - Vibration control

## Setup

### 1. Install Dependencies

```bash
# For object detection
pip install opencv-python picamera2 ultralytics RPi.GPIO

# For web server
pip install flask flask-cors
```

### 2. Run Object Detection (Optional - on Raspberry Pi)

```bash
python objectDetection.py
```

This runs the main NaviGlass functionality WITHOUT any web server.

> **Note:** This step is OPTIONAL! The web server will work even if the Pi isn't running.

### 3. Run Web Server

**Can run on any computer (Mac, Windows, Linux, or Pi):**

```bash
python web_server.py
```

**Example output:**
```
NaviGlass Web Server starting...
Make sure objectDetection.py is running first!
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.1.X:5000
```

The server will:
- ✅ Start successfully even if objectDetection.py isn't running  
- ✅ Show "dead" features (no video, distance shows ">400") until Pi connects
- ✅ Be accessible from other devices on your network

### 4. Open Frontend

#### Option A: Locally
```bash
# Open in browser
open web/index.html
# or
python -m http.server 8000
# Then visit http://localhost:8000/web/
```

#### Option B: GitHub Pages
1. Push the `web/` folder to GitHub
2. Enable GitHub Pages
3. Access from any device
4. Configure server URL to point to your Raspberry Pi's IP

## Configuration

### Vibration Intensity
Create `naviglass_settings.json`:
```json
{
  "vibration_intensity": 0.8,
  "bluetooth_mac": "XX:XX:XX:XX:XX:XX"
}
```

Or use the web interface to adjust settings dynamically.

## API Endpoints

All endpoints provided by `web_server.py`:

- `GET /api/status` - Current status (distance, urgent, vibration intensity)
- `POST /api/settings/vibration` - Set vibration intensity (0.0-1.0)
- `GET /api/scan` - Scan for Bluetooth devices
- `POST /api/pair` - Pair with Bluetooth device
- `POST /api/connect` - Connect to Bluetooth device
- `POST /api/disconnect` - Disconnect from Bluetooth device
- `GET /video_feed` - MJPEG video stream

## Features

### Object Detection Script
- ✅ Runs independently without web server
- ✅ Reads settings from JSON (with defaults)
- ✅ Writes state for external monitoring
- ✅ All original NaviGlass functionality preserved

### Web Interface
- ✅ Server URL configuration
- ✅ Live camera feed with detection boxes
- ✅ Emergency mode (red screen + warning)
- ✅ Distance telemetry
- ✅ Vibration intensity slider (0-100%)
- ✅ Bluetooth device scanning
- ✅ Bluetooth pairing/connection controls
- ✅ Premium dark theme with glassmorphism
- ✅ Responsive design
- ✅ Can be hosted on GitHub Pages

## Deployment

### For GitHub Pages

1. Copy the `web/` folder to your repository
2. Push to GitHub
3. Go to Settings → Pages → Enable for `main` branch
4. Access your page at `https://yourusername.github.io/yourrepo/web/`
5. In the web interface, enter your Raspberry Pi's IP (e.g., `http://192.168.1.100:5000`)

**Note:** If hosting on HTTPS (GitHub Pages), you may need to:
- Set up HTTPS on your Pi, OR
- Allow mixed content in your browser, OR
- Use the frontend locally

## Troubleshooting

### Can't connect to server
- Ensure `web_server.py` is running
- Check firewall settings
- Verify IP address and port
- For GitHub Pages: ensure browser allows mixed content (HTTP backend with HTTPS frontend)

### Video feed not loading
- Check that `objectDetection.py` is running first
- Verify `current_frame.jpg` is being updated
- Check console for errors

### Settings not persisting
- Ensure write permissions for JSON files
- Check `naviglass_settings.json` exists and is valid JSON

## License

MIT