"""
ingest.py — reads the Arduino CSV stream (DHT11 version) and writes it into
guardian.db, generating discrete events on state transitions.

For the real lab demo:    set SIMULATE = False and adjust SERIAL_PORT
For testing without hardware:   set SIMULATE = True
"""
import serial
import sqlite3
import time
import random
from datetime import datetime

# ---------------- config ----------------
SIMULATE    = False          # False = real Arduino DHT11 | True = simulator
SERIAL_PORT = "COM9"
BAUD        = 9600
DB_FILE     = "guardian.db"

# Tunable thresholds
TEMP_HIGH       = 23          
TEMP_ALERT      = 25          
LIGHT_THRESHOLD = 600           
# ----------------------------------------


# ---------------- database ----------------
def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS raw_readings (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ts           TEXT NOT NULL,
            temperature  REAL,
            light        INTEGER,
            motion       INTEGER,
            occupied     INTEGER,
            led          INTEGER,
            vent         INTEGER,
            away         INTEGER
        );

        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT NOT NULL,
            event_type  TEXT NOT NULL,
            severity    TEXT NOT NULL,
            message     TEXT,
            value       REAL
        );

        CREATE TABLE IF NOT EXISTS summary (
            hour_bucket      TEXT PRIMARY KEY,
            avg_temperature  REAL,
            min_temperature  REAL,
            max_temperature  REAL,
            avg_light        REAL,
            motion_count     INTEGER,
            led_on_count     INTEGER,
            vent_open_count  INTEGER,
            away_alert_count INTEGER
        );
    """)
    conn.commit()


def log_event(cursor, event_type, severity, message, value=None):
    cursor.execute(
        "INSERT INTO events (ts, event_type, severity, message, value) "
        "VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"),
         event_type, severity, message, value),
    )


def update_summary(cursor):
    hour_bucket = datetime.now().strftime("%Y-%m-%d %H:00")
    cursor.execute("""
        SELECT
            AVG(temperature), MIN(temperature), MAX(temperature),
            AVG(light),
            SUM(motion),
            SUM(led),
            SUM(vent),
            SUM(CASE WHEN away = 1 AND motion = 1 THEN 1 ELSE 0 END)
        FROM raw_readings
        WHERE ts >= ?
    """, (hour_bucket,))
    stats = cursor.fetchone()

    cursor.execute("""
        INSERT INTO summary
        (hour_bucket, avg_temperature, min_temperature, max_temperature,
         avg_light, motion_count, led_on_count, vent_open_count, away_alert_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(hour_bucket) DO UPDATE SET
            avg_temperature  = excluded.avg_temperature,
            min_temperature  = excluded.min_temperature,
            max_temperature  = excluded.max_temperature,
            avg_light        = excluded.avg_light,
            motion_count     = excluded.motion_count,
            led_on_count     = excluded.led_on_count,
            vent_open_count  = excluded.vent_open_count,
            away_alert_count = excluded.away_alert_count
    """, (hour_bucket, *stats))


# ---------------- simulator ----------------
class FakeArduino:
    """Mimics the DHT11 Arduino's CSV output. Only used when SIMULATE = True."""
    def __init__(self):
        self.temp = 23.0
        self.light = 500
        self.away = 0
        self.motion_counter = 0
        self.tick = 0

    def readline(self):
        self.tick += 1
        self.temp += random.uniform(-0.15, 0.15)
        self.temp = max(18, min(38, self.temp))

        if random.random() < 0.05:
            self.light = random.randint(30, 850)
        if random.random() < 0.01:
            self.away = 1 - self.away

        motion = 0
        if random.random() < 0.03:
            self.motion_counter = 8
        if self.motion_counter > 0:
            motion = 1 if random.random() < 0.5 else 0
            self.motion_counter -= 1

        occupied = 1 if (self.motion_counter > 0 and not self.away) else 0
        led = 1 if (occupied and self.light < LIGHT_THRESHOLD and not self.away) else 0
        vent = 1 if self.temp > TEMP_HIGH else 0

        return f"{self.temp:.2f},{self.light},{motion},{occupied},{led},{vent},{self.away}"


# ---------------- main loop ----------------
def main():
    conn = sqlite3.connect(DB_FILE)
    init_db(conn)
    cursor = conn.cursor()

    if SIMULATE:
        print("[SIMULATE] generating fake Arduino data")
        source = FakeArduino()
    else:
        print(f"[REAL] opening {SERIAL_PORT} @ {BAUD}")
        ser = serial.Serial(SERIAL_PORT, BAUD, timeout=2)
        time.sleep(2)                 # let Arduino reset after serial connect
        ser.reset_input_buffer()
        source = ser

    prev = {"motion": 0, "led": 0, "vent": 0, "away": 0,
            "hot": 0, "alert": 0, "dark": 0}

    try:
        while True:
            if SIMULATE:
                line = source.readline()
                time.sleep(2.0)       # DHT11 pace
            else:
                line = source.readline().decode("utf-8", errors="ignore").strip()

            if not line or line.startswith("=") or line.startswith("temp,"):
                continue

            parts = line.split(",")
            if len(parts) != 7:
                continue

            try:
                temperature = float(parts[0])
                light       = int(parts[1])
                motion      = int(parts[2])
                occupied    = int(parts[3])
                led         = int(parts[4])
                vent        = int(parts[5])
                away        = int(parts[6])
            except ValueError:
                continue

            ts = datetime.now().isoformat(timespec="seconds")

            cursor.execute("""INSERT INTO raw_readings
                              (ts, temperature, light, motion, occupied, led, vent, away)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                           (ts, temperature, light, motion, occupied, led, vent, away))

            # ---- LED ----
            if led != prev["led"]:
                log_event(cursor, "led_on" if led else "led_off", "info",
                          "Desk lamp turned " + ("on" if led else "off"), temperature)

            # ---- Vent ----
            if vent != prev["vent"]:
                log_event(cursor, "vent_open" if vent else "vent_close",
                          "warning" if vent else "info",
                          "Vent " + ("opened — room hot" if vent else "closed"),
                          temperature)

            # ---- Away ----
            if away != prev["away"]:
                log_event(cursor, "away_on" if away else "away_off", "info",
                          "Away mode " + ("enabled" if away else "disabled"))

            # ---- Light level ----
            dark = 1 if light < LIGHT_THRESHOLD else 0
            if dark and not prev["dark"]:
                log_event(cursor, "light_low", "warning",
                          f"Light dropped below {LIGHT_THRESHOLD} (reading {light})",
                          light)
            if not dark and prev["dark"]:
                log_event(cursor, "light_ok", "info",
                          f"Light restored above {LIGHT_THRESHOLD} (reading {light})",
                          light)

            # ---- Intruder ----
            if away and motion and not prev["motion"]:
                log_event(cursor, "intruder_alert", "critical",
                          "Motion detected while away", temperature)
                print(f"🚨 [{ts}] INTRUDER ALERT — motion while away "
                      f"(T={temperature:.1f}°C)")

            # ---- Heat warning / cleared ----
            hot = 1 if temperature > TEMP_HIGH else 0
            if hot and not prev["hot"]:
                log_event(cursor, "heat_warning", "warning",
                          f"Temperature exceeded {TEMP_HIGH:.0f}°C", temperature)
            if not hot and prev["hot"]:
                log_event(cursor, "heat_cleared", "info",
                          "Temperature back to normal", temperature)

            # ---- Heat alert ----
            alert = 1 if temperature > TEMP_ALERT else 0
            if alert and not prev["alert"]:
                log_event(cursor, "heat_alert", "critical",
                          f"Temperature exceeded {TEMP_ALERT:.0f}°C", temperature)

            prev.update({"motion": motion, "led": led, "vent": vent,
                         "away": away, "hot": hot, "alert": alert, "dark": dark})

            update_summary(cursor)
            conn.commit()

            print(f"[{ts}] T={temperature:.1f}°C  light={light}  "
                  f"motion={motion}  occ={occupied}  led={led}  "
                  f"vent={vent}  away={away}")

    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        conn.close()
        if not SIMULATE:
            ser.close()


if __name__ == "__main__":
    main()