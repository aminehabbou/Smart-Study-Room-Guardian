<div align="center">

# Smart Study Room Guardian

### An IoT Sensor Network for Ambient Comfort and Security Monitoring

**A sensor-driven study-room monitoring system combining local automation, event logging, and a real-time web dashboard.**

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.1.3-000000?logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/Arduino-Uno-00979D?logo=arduino&logoColor=white" alt="Arduino">
  <img src="https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white" alt="HTML5">
  <img src="https://img.shields.io/badge/CSS3-1572B6?logo=css3&logoColor=white" alt="CSS3">
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black" alt="JavaScript">
  <img src="https://img.shields.io/badge/Chart.js-FF6384?logo=chartdotjs&logoColor=white" alt="Chart.js">
  <img src="https://img.shields.io/badge/Jinja2-B41717?logo=jinja&logoColor=white" alt="Jinja2">
</p>

<p>
  <img src="https://img.shields.io/badge/Domain-Internet%20of%20Things-2E8B57" alt="Internet of Things">
  <img src="https://img.shields.io/badge/Focus-Comfort%20%7C%20Automation%20%7C%20Security-6A5ACD" alt="Project focus">
  <img src="https://img.shields.io/badge/Communication-USB%20Serial-64748B" alt="USB serial">
</p>

</div>

---

## Project Overview

**Smart Study Room Guardian** is an IoT prototype designed to monitor a study room's environmental conditions, respond to changes locally, and maintain a record of room activity.

The system connects an **Arduino Uno** to a Python application through a wired USB serial connection. The Arduino reads temperature, ambient light, and motion sensors, then controls a desk-lamp indicator, a servo-operated ventilation flap, and an audible alarm. A Python ingestion process stores sensor readings and state-change events in a local SQLite database. A Flask web application exposes live readings and historical summaries through a browser-based dashboard.

The project addresses three practical aspects of a study environment:

- **Ambient comfort:** monitor room temperature and light conditions.
- **Energy-aware automation:** operate the desk-lamp indicator according to occupancy and ambient light.
- **Room security:** enable an Away Mode that triggers an alert when motion is detected.

## System Capabilities

| Capability | Implementation |
|---|---|
| Environmental monitoring | DHT11 temperature sensor and LDR light sensor |
| Motion detection | PIR motion sensor |
| Occupancy state | Motion tracking with a configurable no-motion timeout |
| Desk-lamp automation | LED output enabled when the room is occupied and dark |
| Thermal response | SG90 servo opens or closes a vent according to the temperature threshold |
| Audible alerts | Piezo buzzer signals intruder and heat-warning conditions |
| Away Mode | Physical push button toggles Home/Away state |
| Data ingestion | Python reads seven-field CSV records over USB serial |
| Persistent storage | SQLite stores raw readings, events, and hourly summaries |
| Live monitoring | Flask API and browser dashboard |
| Historical reporting | Temperature, motion, event, and usage summaries with charts |
| Demo data | `seed.py` generates 24 hours of simulated history |

## System Architecture

```text
┌───────────────────────────────────────────────┐
│                  HARDWARE                     │
│                                               │
│  DHT11 ── Temperature                         │
│  LDR   ── Ambient light                       │
│  PIR   ── Motion                              │
│  Button ── Home / Away mode                   │
│                                               │
│              Arduino Uno                      │
│        Local rules and actuation              │
│                                               │
│  LED ── Desk-lamp indicator                   │
│  Servo ── Vent position                       │
│  Buzzer ── Audible alerts                     │
└──────────────────────┬────────────────────────┘
                       │ USB serial · 9600 baud
                       │ CSV readings
                       ▼
┌───────────────────────────────────────────────┐
│              PYTHON INGESTION                 │
│                  ingest.py                    │
│  Parse readings · Detect transitions          │
│  Generate events · Update hourly summaries   │
└──────────────────────┬────────────────────────┘
                       ▼
┌───────────────────────────────────────────────┐
│                SQLITE DATABASE                │
│  raw_readings · events · summary              │
└──────────────────────┬────────────────────────┘
                       ▼
┌───────────────────────────────────────────────┐
│                FLASK BACKEND                  │
│                dashboard.py                   │
│       HTML pages and JSON API endpoints       │
└──────────────────────┬────────────────────────┘
                       ▼
┌───────────────────────────────────────────────┐
│              WEB DASHBOARD                    │
│  Live status · Sensor charts · Event log      │
│  Daily report · Historical insights           │
└───────────────────────────────────────────────┘
```

A key design choice is that **the Arduino performs sensing and local control independently of the dashboard**. The Flask application reads the stored data; it is not responsible for the real-time hardware control loop.

## Hardware Components

| Component | Role |
|---|---|
| Arduino Uno | Reads sensors, applies control rules, and sends serial data |
| DHT11 | Measures room temperature |
| LDR / photoresistor | Measures ambient light through an analogue voltage divider |
| PIR sensor | Detects movement |
| Push button | Toggles Home and Away modes |
| Red LED and 220 Ω resistor | Represents the desk lamp |
| SG90 micro servo | Opens and closes the ventilation flap |
| Piezo buzzer | Produces heat and intruder alert tones |
| 10 kΩ resistor | LDR voltage-divider pull-down |
| Breadboard and jumper wires | Circuit assembly |
| USB cable | Power and serial communication |

### Arduino Pin Mapping

| Arduino pin | Connected component | Direction |
|---|---|---|
| D2 | DHT11 DATA | Input |
| A0 | LDR voltage-divider output | Analogue input |
| D3 | PIR OUT | Input |
| D4 | Push button | Input with internal pull-up |
| D5 | Piezo buzzer | Output |
| D6 | LED through 220 Ω resistor | Output |
| D8 | SG90 servo signal | Output |
| 5V / GND | Breadboard power rails | Power |

The circuit uses a common ground. Check component polarity and the wiring in the project report before powering the circuit. The servo is connected to the 5V rail rather than being powered directly from a digital I/O pin.

## Control Logic

The Arduino evaluates the sensor readings and applies the following rules:

| Condition | System response |
|---|---|
| Room is occupied and light level is below 600 | Desk-lamp LED turns on |
| Room is unoccupied, sufficiently bright, or Away Mode is enabled | Desk-lamp LED turns off |
| Temperature exceeds 23 °C | Vent servo opens |
| Temperature returns to 23 °C or below | Vent servo closes |
| Temperature exceeds 25 °C | Heat-warning tone is produced |
| Away Mode is enabled and motion is detected | Intruder-alert tone is produced |
| Push button is pressed | Home/Away state is toggled |

The Arduino sends one CSV record every two seconds at **9,600 baud**. The record contains seven values in this order:

```text
temperature,light,motion,occupied,led,vent,away
```

Example:

```text
22.20,624,0,0,0,0,0
```

## Software Stack

### Python backend and data processing

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/PySerial-Serial%20I%2FO-306998" alt="PySerial">
</p>

- **Python** — serial ingestion, event processing, database operations, and backend application logic.
- **Flask** — web server, page rendering, and JSON API endpoints.
- **SQLite** — local relational storage for sensor readings, events, and hourly summaries.
- **Python `sqlite3`** — database access through the Python standard library.
- **Python `datetime`** — timestamp handling and time-based reporting.
- **Python `random`** — synthetic sensor values in the simulator and demo-data generator.
- **Serial communication** — reads the Arduino's CSV stream over USB.

### Firmware and electronics

<p>
  <img src="https://img.shields.io/badge/Arduino%20Uno-00979D?logo=arduino&logoColor=white" alt="Arduino Uno">
  <img src="https://img.shields.io/badge/Arduino%20C%2B%2B-00599C?logo=cplusplus&logoColor=white" alt="Arduino C++">
  <img src="https://img.shields.io/badge/DHT%20Library-Sensor%20Interface-607D8B" alt="DHT library">
  <img src="https://img.shields.io/badge/Servo%20Library-Actuator%20Control-607D8B" alt="Servo library">
</p>

- **Arduino C/C++** — sensor acquisition, state logic, and actuator control.
- **DHT library** — interfaces with the DHT11 temperature sensor.
- **Servo library** — controls the SG90 servo position.
- **Serial interface** — transmits sensor and state values to the host computer.

### Frontend and visualization

<p>
  <img src="https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white" alt="HTML5">
  <img src="https://img.shields.io/badge/CSS3-1572B6?logo=css3&logoColor=white" alt="CSS3">
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black" alt="JavaScript">
  <img src="https://img.shields.io/badge/Chart.js-FF6384?logo=chartdotjs&logoColor=white" alt="Chart.js">
  <img src="https://img.shields.io/badge/Jinja2-B41717?logo=jinja&logoColor=white" alt="Jinja2">
</p>

- **HTML5** — dashboard page structure.
- **CSS3** — responsive layout, styling, and status indicators.
- **JavaScript** — periodic API polling, dashboard updates, and chart data handling.
- **Chart.js** — live sensor charts and historical report visualizations.
- **Jinja2** — server-side HTML templating through Flask.

### Python dependencies

The repository includes a `requirements.txt` file. Install from that file to use the dependency versions specified by the project:

```bash
pip install -r requirements.txt
```

The application also uses Python standard-library modules including `sqlite3`, `datetime`, `time`, and `random`.

## Repository Structure

```text
Smart-Study-Room-Guardian/
├── Arduino_sketch/
│   └── Guardian_Arduino_Code.txt
├── templates/
│   ├── base.html
│   ├── index.html
│   └── report.html
├── dashboard.py
├── ingest.py
├── seed.py
├── requirements.txt
├── guardian.db
├── .gitignore
└── Smart Study Room Guardian--Project Report_Amine_Habbou.pdf
```

| File / directory | Description |
|---|---|
| `Arduino_sketch/Guardian_Arduino_Code.txt` | Arduino firmware for sensor readings, control logic, and serial output |
| `dashboard.py` | Flask application and JSON API |
| `ingest.py` | Serial data ingestion, event detection, and database updates |
| `seed.py` | Generates 24 hours of synthetic readings and events for a dashboard demonstration |
| `templates/base.html` | Shared layout, styling, navigation, and frontend libraries |
| `templates/index.html` | Live sensor dashboard and recent event feed |
| `templates/report.html` | Historical charts, daily metrics, and automatic insights |
| `requirements.txt` | Python package requirements |
| `guardian.db` | SQLite database file |
| Project report PDF | Detailed project documentation, hardware design, architecture, and run instructions |

## Getting Started

### 1. Requirements

- Python 3.10 or later.
- Arduino IDE and an Arduino Uno (for the hardware workflow).
- USB data cable and the required sensors/actuators.
- A serial port available to the computer.
- A modern web browser.

### 2. Clone the repository

Replace the placeholders with your GitHub account and repository name:

```bash
git clone https://github.com/<your-username>/<your-repository>.git
cd <your-repository>
```

### 3. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure and upload the Arduino firmware

1. Open `Arduino_sketch/Guardian_Arduino_Code.txt` in the Arduino IDE (or save it as an `.ino` sketch).
2. Ensure the **DHT** and **Servo** Arduino libraries are installed.
3. Select the correct Arduino board and port.
4. Verify that the pin connections match the mapping documented above.
5. Upload the sketch to the Arduino Uno.

The firmware uses a serial baud rate of `9600` and transmits one sensor record approximately every two seconds.

### 6. Configure the serial connection

Open `ingest.py` and check the configuration near the top of the file:

```python
SIMULATE = False
SERIAL_PORT = "COM9"
BAUD = 9600
DB_FILE = "guardian.db"
```

Set `SERIAL_PORT` to the port assigned to your Arduino. For example, Windows commonly uses `COM3`, `COM4`, or another `COM` port. On macOS or Linux, the device may appear under `/dev/`.

Close the Arduino IDE Serial Monitor before starting ingestion, because the serial port generally cannot be used by both programs at the same time.

### 7. Start data ingestion

With the Arduino connected and the serial port configured:

```bash
python ingest.py
```

The ingestion process reads incoming records, stores valid samples in SQLite, detects state transitions, and records corresponding events.

To run without physical hardware, set `SIMULATE = True` in `ingest.py`. The built-in `FakeArduino` source generates synthetic readings for testing the ingestion and dashboard workflow.

### 8. Launch the dashboard

Open a second terminal in the project directory, activate the same virtual environment, and run:

```bash
python dashboard.py
```

Then open:

- Live dashboard: `http://127.0.0.1:5000/`
- Historical report: `http://127.0.0.1:5000/report`

The live dashboard refreshes its data periodically, while the report page refreshes its statistics on a separate interval.

## Running a Dashboard Demo Without Hardware

The repository includes `seed.py` to populate the SQLite database with approximately 24 hours of synthetic readings and events.

```bash
python seed.py
python dashboard.py
```

Then visit `http://127.0.0.1:5000/report` to inspect the generated report data.

**Note:** `seed.py` adds generated records to the database; it does not clear existing records. If you want a fresh demo dataset, back up and remove the existing `guardian.db` before running the seed script. Do not run the seeding script against data you need to preserve.

## Dashboard and API

The Flask application provides two browser pages and four JSON endpoints.

| Route | Purpose |
|---|---|
| `/` | Live sensor dashboard |
| `/report` | Historical report and analytics |
| `/api/current` | Latest sensor reading and system states |
| `/api/live` | Recent temperature and light samples |
| `/api/events` | Most recent recorded events |
| `/api/stats` | Daily metrics, weekly Away Mode alerts, and grouped chart data |

The live page presents temperature, light, motion, occupancy, LED, ventilation, and Away Mode states. It also displays recent events and a time-series chart. The report page summarizes daily temperature, lamp usage, occupancy, motion, and alert activity, with charts and rule-based insights.

## Database Design

The SQLite database uses three tables:

| Table | Purpose |
|---|---|
| `raw_readings` | Timestamped sensor readings and system states: temperature, light, motion, occupancy, LED, vent, and Away Mode |
| `events` | Discrete events with timestamps, event types, severity, messages, and optional values |
| `summary` | Hourly aggregates such as average/minimum/maximum temperature, average light, motion count, lamp usage, ventilation usage, and Away Mode alert counts |

This separation preserves the raw sensor history while making state changes and aggregated reporting available to the dashboard.

## Simulation

The project report documents a Tinkercad-oriented workflow for circuit simulation. The Python ingestion script also includes a software simulation mode through `FakeArduino`, which can generate CSV-like sensor readings without a physical Arduino connection.

These are different workflows: the built-in Python simulator feeds the ingestion/database pipeline directly, while a circuit simulator is useful for testing hardware logic and wiring. A simulator's serial output is not automatically connected to the local database unless an appropriate serial bridge is configured.

## Notes and Limitations

- The current prototype uses a **wired USB serial connection** and is scoped to one room.
- The configured serial port in `ingest.py` is machine-specific and should be changed before running on another computer.
- Temperature and light thresholds are defined in the firmware and Python ingestion/dashboard code; keep related values consistent when changing system behaviour.
- The DHT11 is sampled at a two-second interval in the firmware.
- The LED represents a desk lamp in the prototype; it is not a mains-powered lighting installation.
- The vent is represented by a servo-driven mechanism. The prototype does not measure actual airflow.
- The dashboard depends on data being written to the SQLite database by the ingestion process or demo seeding script.
- The included SQLite database may contain local/demo records. For a clean deployment, initialize a fresh database rather than relying on bundled runtime data.

## Future Development

Potential extensions identified for the project include:

- Replace the wired Arduino connection with an ESP32-based wireless architecture.
- Add cloud storage and remote monitoring.
- Improve data export and long-term trend analysis.

## Author

**Amine Habbou**  
M.Sc. Data Engineering  
Constructor University  
Bremen, Germany

**Project:** *Smart Study Room Guardian: An IoT Sensor Network for Ambient Comfort and Security Monitoring*  
**Context:** Data Acquisition Technologies and Sensor Networks

---

<div align="center">

**Smart Study Room Guardian**  
*Monitoring the study environment through sensing, automation, and data.*

</div>
