import time
import cv2
from picamera2 import Picamera2
from flask import Flask, Response, jsonify, request # Used for web streaming
from flask_cors import CORS
from ultralytics import YOLO
import threading
import RPi.GPIO as GPIO
import statistics
from SmartNarrator import SmartNarrator
from TTSEngine import TTSEngine
from BluetoothAudioManager import BluetoothAudioManager
import os


_left_pwm = None
_right_pwm = None
_latest_labels = []
_latest_labels_lock = threading.Lock()
SENSOR_TRIG_PIN1 = 13
SENSOR_ECHO_PIN1 = 11
SENSOR_TRIG_PIN2 = 16
SENSOR_ECHO_PIN2 = 18
VIB_MOTOR_PIN1 = 32
VIB_MOTOR_PIN2 = 33
CONFIG_FILE = "last_device.txt"
DETECT_CLASSES = [
    0,   # person
    1,   # bicycle
    2,   # car
    3,   # motorcycle
    5,   # bus
    7,   # truck
    9,   # traffic light
    10,  # fire hydrant
    11,  # stop sign
    13,  # bench
]


app = Flask(__name__)  # Initialize Flask app
CORS(app)  # Enable CORS for GitHub Pages

picam = Picamera2()  # Initialize the camera
print("Camera initialized.")
config = picam.create_preview_configuration(main={'size': (640, 480), 'format': 'RGB888'})
picam.configure(config)
picam.start()  # Start the camera

model = YOLO("yolo11n_ncnn_model")  # Load the model
print("YOLO11n loaded.")

narrator = SmartNarrator() # Initialize the narrator

bt_manager = BluetoothAudioManager()

tts = None



def save_last_device(mac_address):
    try:
        with open(CONFIG_FILE, "w") as f:
            f.write(mac_address.strip())
        print(f"Saved {mac_address} as default device.")
    except Exception as e:
        print(f"Failed to save device config: {e}")


def load_last_device():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return f.read().strip()
        except Exception as e:
            print(f"Failed to read config: {e}")
    return None


def clear_last_device():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)


def setup_bluetooth_auto():
    last_mac = load_last_device()
    
    if not last_mac:
        print("No previous device found. Using system default audio.")
        return False

    print(f"Found saved device: {last_mac}. Auto-connecting...")
    
    if bt_manager.connect_audio(last_mac):
        print("Bluetooth Auto-Connect Successful.")
        return True
    else:
        print("Bluetooth Auto-Connect Failed.")
        return False



def setup_vibration_motor(): # Pin set up
    global _left_pwm, _right_pwm
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(VIB_MOTOR_PIN1, GPIO.OUT)
    GPIO.setup(VIB_MOTOR_PIN2, GPIO.OUT)

    _left_pwm = GPIO.PWM(VIB_MOTOR_PIN1, 100)
    _right_pwm = GPIO.PWM(VIB_MOTOR_PIN2, 100)

    _left_pwm.start(0)
    _right_pwm.start(0)
    print("Vibration setup complete.")


def set_motor_speed(left_dc, right_dc):
    left_dc = max(0, min(100, left_dc))
    right_dc = max(0, min(100, right_dc))
    if _left_pwm and _right_pwm:
        _left_pwm.ChangeDutyCycle(left_dc)
        _right_pwm.ChangeDutyCycle(right_dc)


def calculate_duty_cycle(distance):
    if distance > 400:
        return 10
    else:
        return 45 - distance / 400 * 25  # Linearly map distance to duty cycle


def calculate_spatial_ratio(x_coordinate, duty_cycle):
    left_dc = min(90, 2 * duty_cycle * (1-x_coordinate))
    right_dc = min(90, 2 * duty_cycle * x_coordinate)
    return left_dc, right_dc



def setup_sensor(): # Pin set up
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(SENSOR_TRIG_PIN1, GPIO.OUT)
    GPIO.output(SENSOR_TRIG_PIN1, GPIO.LOW)
    GPIO.setup(SENSOR_ECHO_PIN1, GPIO.IN)
    GPIO.setup(SENSOR_TRIG_PIN2, GPIO.OUT)
    GPIO.output(SENSOR_TRIG_PIN2, GPIO.LOW)
    GPIO.setup(SENSOR_ECHO_PIN2, GPIO.IN)
    print("Distance sensor setup complete.")


def measure_distance(TRIG, ECHO):
    GPIO.output(TRIG, GPIO.HIGH) # Send a 10us pulse to trigger the sensor
    time.sleep(0.00001)
    GPIO.output(TRIG, GPIO.LOW)

    MAX_TIMEOUT = 0.3 # 300 ms timeout
    t_timeout = time.time()

    while GPIO.input(ECHO) == 0: # Wait for the echo start
        if time.time() - t_timeout > MAX_TIMEOUT:
            return 999  # Timeout, return out of range
        pulse_start = time.time()

    t_timeout = time.time()
    while GPIO.input(ECHO) == 1:
        if time.time() - t_timeout > MAX_TIMEOUT:
            return 999  # Timeout, return out of range
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start # Calculate pulse duration and distance
    distance_cm = pulse_duration * 17150

    if distance_cm < 2 or distance_cm > 400:
        return 999  # Out of range
    
    return distance_cm


def generate_distance(TRIG, ECHO): # Make 3 distance measurements
    t=0
    distances = []
    while t<3:
        distance_cm = measure_distance(TRIG, ECHO)
        distances.append(distance_cm)
        t+=1
        time.sleep(0.04)
    median_distance = statistics.median(distances) # Return the median of the 3 measurements
    print("Distance measured: " + str(median_distance)) # Print distance for debugging
    return median_distance



def set_latest_labels(labels): # Safely set the labels
    global _latest_labels
    with _latest_labels_lock:
        _latest_labels = list(labels) if labels is not None else []


def get_latest_labels(): # Safely get the labels
    with _latest_labels_lock:
        return list(_latest_labels)
    

def labels_from_result(result, conf_min: float = 0.70):
    out = []
    if getattr(result, "boxes", None) is None or len(result.boxes) == 0:
        return out
    names = result.names
    for cls_tensor, conf_tensor, box_tensor in zip(result.boxes.cls, result.boxes.conf, result.boxes.xyxyn):
        conf = float(conf_tensor.item())
        if conf >= conf_min: # Check the confidence is higher than the threshold
            x1, y1, x2, y2 = box_tensor.tolist() # Get the coordinates of the center of the bounding box
            width = x2 - x1
            height = y2 - y1
            area = width * height
            if area < 0.0625: # Skip the objects that cover less than 1/16 of the frame
                continue
            cls_id = int(cls_tensor.item())
            label = names.get(cls_id, str(cls_id)) # Get the label
            center_x = x1 + width / 2
            center_y = y1 + height / 2
            out.append({'label': label, 'confidence': conf, 'coordinates': (center_x, center_y), 'area': area})
    return out


def generate_frames():
    while True:
        frame = picam.capture_array() # Capture frame from Picamera2
        t0 = time.perf_counter() # Start time for fps measurement

        results = model(frame, verbose=False, classes=DETECT_CLASSES) # Run the YOLO model on a certain amount of classes
        r = results[0] # Extract the Results object from the list
        labels = labels_from_result(r, conf_min=0.70) # Get labels from the Results object with confidence filtering
        set_latest_labels(labels) # Set the thread-safe variable

        t1 = time.perf_counter() # End time for fps measurement
        elpased_ms = (t1 - t0) * 1000
        fps = 1000 / elpased_ms
        print(f"Inference time: {elpased_ms:.2f} ms, FPS: {fps:.2f}") # Print time for observation

        annotated_frame = r.plot() # Draw bounding boxes
        ret, buffer = cv2.imencode('.jpg', annotated_frame) # Turn the frame into JPEG and send to stream through Flask
        if not ret:
            continue
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.05) # Rest the CPU


def select_biggest_label(labels): # Select the label with the highest area
    if not labels:
        return None
    best = max(labels, key=lambda x: x.get('area', 0.0))
    return best



def narrate_sentence(best_object, distance_cm): # Narrate sentences from the local SmartNarrator class
    sentence = narrator.generate(best_object['label'], distance_cm, best_object['coordinates'][0])
    print(sentence)

    is_urgent = distance_cm < 60
    if tts:
        tts.speak(sentence, interrupt=is_urgent)
    return sentence
    


def main_loop():
    last_label = None
    consecutive_misses = 0
    vib_deadline = 0
    ref_distance = 999
    MAX_MISSES = 10
    VIB_PULSE_TIME = 3
    APPROACH_SENSITIVITY = 10

    print ("Main loop started")

    while True:
        try:
            best = select_biggest_label(get_latest_labels())

            if best:
                consecutive_misses = 0
                label = best['label']
                x, _ = best['coordinates']

                distance1 = generate_distance(SENSOR_TRIG_PIN1, SENSOR_ECHO_PIN1) 
                distance2 = generate_distance(SENSOR_TRIG_PIN2, SENSOR_ECHO_PIN2) # Measure from the two sensors
                distance_cm = min(distance1, distance2)

                should_vibrate = False

                if label != last_label:
                    vib_deadline = time.time() + VIB_PULSE_TIME
                    ref_distance = distance_cm
                    should_vibrate = True
                else:
                    if distance_cm <= 400 and distance_cm < ref_distance - APPROACH_SENSITIVITY:
                        vib_deadline = time.time() + VIB_PULSE_TIME
                        ref_distance = distance_cm
                        should_vibrate = True
                    elif time.time() < vib_deadline:
                        should_vibrate = True
                    elif time.time() >= vib_deadline:
                        vib_deadline = 0
                        should_vibrate = False

                if should_vibrate:
                    duty_cycle = calculate_duty_cycle(distance_cm)
                    left_dc, right_dc = calculate_spatial_ratio(x, duty_cycle)
                    set_motor_speed(left_dc, right_dc)
                else:
                    set_motor_speed(0, 0)
            
                if label != last_label:
                    narrate_sentence(best, distance_cm)
                    last_label = label
            else:
                consecutive_misses += 1
                set_motor_speed(0, 0)
                if consecutive_misses >= MAX_MISSES:
                    last_label = None
                    ref_distance = 999
        
        except Exception as e:
            print(f"Error in main loop: {e}")
        
        time.sleep(0.1) # Main loop delay 



HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>NaviGlass Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #1a1a1a; color: white; text-align: center; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        img { width: 100%; max-width: 640px; border-radius: 8px; border: 2px solid #444; }
        .card { background: #333; padding: 20px; border-radius: 10px; margin-top: 20px; }
        button { padding: 10px 15px; font-size: 14px; border-radius: 5px; border: none; cursor: pointer; margin: 2px; }
        .scan { background: #007bff; color: white; width: 100%; padding: 15px; font-size: 18px; margin-bottom: 10px; }
        .pair { background: #28a745; color: white; }
        .connect { background: #17a2b8; color: white; }
        .disconnect { background: #dc3545; color: white; } 
        li { background: #444; margin: 10px 0; padding: 10px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; text-align: left; }
    </style>
</head>
<body>
    <div class="container">
        <h1>NaviGlass Live View</h1>
        <img src="/video_feed" />
        <div class="card">
            <h2>Bluetooth Manager</h2>
            <div id="status" style="color:#aaa; margin-bottom:10px;">Ready</div>
            <button class="scan" onclick="scanDevices()">Scan for Devices</button>
            <ul id="deviceList"></ul>
        </div>
    </div>
    <script>
        function updateStatus(msg) { document.getElementById('status').innerText = msg; }
        
        async function scanDevices() {
            updateStatus("Scanning...");
            document.querySelector('.scan').disabled = true;
            try {
                const res = await fetch('/api/scan');
                const devs = await res.json();
                const list = document.getElementById('deviceList');
                list.innerHTML = '';
                devs.forEach(d => {
                    const li = document.createElement('li');
                    li.innerHTML = `
                        <span><strong>${d.name}</strong><br><small>${d.mac}</small></span>
                        <div>
                            <button class="pair" onclick="apiCall('/api/pair', '${d.mac}')">Pair</button>
                            <button class="connect" onclick="apiCall('/api/connect', '${d.mac}')">Connect</button>
                            <button class="disconnect" onclick="apiCall('/api/disconnect', '${d.mac}')">Disconnect</button>
                        </div>`;
                    list.appendChild(li);
                });
                updateStatus("Scan complete.");
            } catch(e) { updateStatus("Error: " + e); }
            document.querySelector('.scan').disabled = false;
        }

        async function apiCall(endpoint, mac) {
            updateStatus("Processing " + mac + "...");
            const res = await fetch(endpoint, {
                method: 'POST', 
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({mac: mac})
            });
            const data = await res.json();
            updateStatus(data.message);
        }
    </script>
</body>
</html>
"""


            
@app.route('/')
def index():
    return HTML_PAGE

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Bluetooth API Endpoints ---

@app.route('/api/scan')
def api_scan():
    devices = bt_manager.scan_devices(duration=10)
    return jsonify(devices)

@app.route('/api/pair', methods=['POST'])
def api_pair():
    data = request.json
    mac = data.get('mac')
    if bt_manager.pair_device(mac):
        return jsonify({"status": "success", "message": f"Paired with {mac}"})
    return jsonify({"status": "error", "message": "Pairing failed. Check device mode."}), 500

@app.route('/api/connect', methods=['POST'])
def api_connect():
    global tts # We need to modify the global object
    mac = request.json.get('mac')
    
    if bt_manager.connect_audio(mac):
        save_last_device(mac)
        
        if tts: 
            tts.speak("Audio connected")
        
        print("Waiting for audio subsystem...")
        time.sleep(3) 
        
        return jsonify({"status":"success", "message":f"Connected {mac}"})
        
    return jsonify({"status":"error", "message":"Connection failed"}), 500

@app.route('/api/disconnect', methods=['POST'])
def api_disconnect():
    global tts
    mac = request.json.get('mac')
    
    if bt_manager.disconnect_device(mac):
        
        clear_last_device()
        
        return jsonify({"status":"success", "message":f"Disconnected {mac}"})
    return jsonify({"status":"error", "message":"Disconnect failed"}), 500



if __name__ == '__main__': # Main function
    try:
        setup_sensor()
    except Exception as e:
        print(f"Failed to setup distance sensor: {e}")
        
    try:
        setup_vibration_motor()
    except Exception as e:
        print(f"Failed to setup vibration motor: {e}")

    try:
        setup_bluetooth_auto()
    except Exception as e:
        print(f"Bluetooth setup failed: {e}")

    tts = TTSEngine(volume=0.5)
    tts.start()

    try: # Start the main loop
        runner = main_loop
        t = threading.Thread(target=runner, daemon=True)
        t.start()
    except Exception as e:
        print(f"Failed to start main loop: {e}")

    try:
        app.run(host='0.0.0.0', port=5000) # Start the web server

    finally:
        if _left_pwm: _left_pwm.stop()
        if _right_pwm: _right_pwm.stop()
        GPIO.cleanup() # Cleans up all GPIO ports upon exit

        tts.stop()
        bt_manager.disconnect_device()