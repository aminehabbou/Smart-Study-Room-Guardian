"""
seed.py — populates guardian.db with 24 hours of realistic fake history.
Useful for demoing the report page without waiting for real data.

Run with:   python seed.py
Wipes nothing — but has no dedup, so delete guardian.db before re-running.
"""
import sqlite3
import random
from datetime import datetime, timedelta

DB = "guardian.db"

# Match thresholds used by ingest.py
TEMP_HIGH       = 23.0
TEMP_ALERT      = 25.0
LIGHT_THRESHOLD = 600
SAMPLE_INTERVAL = 2         # seconds per simulated row


def seed():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS raw_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, temperature REAL, light INTEGER,
            motion INTEGER, occupied INTEGER, led INTEGER,
            vent INTEGER, away INTEGER
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, event_type TEXT, severity TEXT,
            message TEXT, value REAL
        );
        CREATE TABLE IF NOT EXISTS summary (
            hour_bucket TEXT PRIMARY KEY,
            avg_temperature REAL, min_temperature REAL, max_temperature REAL,
            avg_light REAL, motion_count INTEGER, led_on_count INTEGER,
            vent_open_count INTEGER, away_alert_count INTEGER
        );
    """)

    now = datetime.now()
    start = now - timedelta(hours=24)

    temp = 22.0
    tick = start

    prev = {"led": 0, "vent": 0, "away": 0,
            "hot": 0, "alert": 0, "dark": 0}

    while tick < now:
        hour = tick.hour

        # temperature drifts with a day/night cycle
        temp += random.uniform(-0.15, 0.15)
        temp += 0.05 if 12 <= hour <= 18 else -0.03
        temp = max(18, min(34, temp))

        # light: bright during day, dark at night
        if 7 <= hour <= 20:
            light = random.randint(250, 900)
        else:
            light = random.randint(20, 200)

        # motion more likely during waking hours
        motion_p = 0.10 if 8 <= hour <= 22 else 0.015
        motion = 1 if random.random() < motion_p else 0
        
        away = 1 if (hour >= 23 or hour < 6) else 0
        occupied = 1 if (motion or random.random() < 0.3) and not away else 0
        led  = 1 if (occupied and light < LIGHT_THRESHOLD and not away) else 0
        vent = 1 if temp > TEMP_HIGH else 0

        ts = tick.isoformat(timespec="seconds")

        c.execute("""INSERT INTO raw_readings
                     (ts, temperature, light, motion, occupied, led, vent, away)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (ts, round(temp, 2), light, motion, occupied, led, vent, away))

        # ---- LED ----
        if led != prev["led"]:
            c.execute("""INSERT INTO events (ts, event_type, severity, message, value)
                         VALUES (?, ?, ?, ?, ?)""",
                      (ts, "led_on" if led else "led_off", "info",
                       "Desk lamp turned " + ("on" if led else "off"), temp))

        # ---- Vent ----
        if vent != prev["vent"]:
            c.execute("""INSERT INTO events (ts, event_type, severity, message, value)
                         VALUES (?, ?, ?, ?, ?)""",
                      (ts, "vent_open" if vent else "vent_close",
                       "warning" if vent else "info",
                       "Vent " + ("opened — room hot" if vent else "closed"), temp))

        # ---- Away mode ----
        if away != prev["away"]:
            c.execute("""INSERT INTO events (ts, event_type, severity, message, value)
                         VALUES (?, ?, 'info', ?, NULL)""",
                      (ts, "away_on" if away else "away_off",
                       "Away mode " + ("enabled" if away else "disabled")))

        # ---- Light level ----
        dark = 1 if light < LIGHT_THRESHOLD else 0
        if dark and not prev["dark"]:
            c.execute("""INSERT INTO events (ts, event_type, severity, message, value)
                         VALUES (?, 'light_low', 'warning', ?, ?)""",
                      (ts, f"Light dropped below {LIGHT_THRESHOLD} (reading {light})", light))
        if not dark and prev["dark"]:
            c.execute("""INSERT INTO events (ts, event_type, severity, message, value)
                         VALUES (?, 'light_ok', 'info', ?, ?)""",
                      (ts, f"Light restored above {LIGHT_THRESHOLD} (reading {light})", light))

        # ---- Intruder ----
        if away and motion and random.random() < 0.4:
            c.execute("""INSERT INTO events (ts, event_type, severity, message, value)
                         VALUES (?, 'intruder_alert', 'critical',
                                 'Motion detected while away', ?)""",
                      (ts, temp))

        # ---- Heat warning / cleared ----
        hot = 1 if temp > TEMP_HIGH else 0
        if hot and not prev["hot"]:
            c.execute("""INSERT INTO events (ts, event_type, severity, message, value)
                         VALUES (?, 'heat_warning', 'warning', ?, ?)""",
                      (ts, f"Temperature exceeded {TEMP_HIGH:.0f}°C", temp))
        if not hot and prev["hot"]:
            c.execute("""INSERT INTO events (ts, event_type, severity, message, value)
                         VALUES (?, 'heat_cleared', 'info',
                                 'Temperature back to normal', ?)""",
                      (ts, temp))

        # ---- Heat alert ----
        alert = 1 if temp > TEMP_ALERT else 0
        if alert and not prev["alert"]:
            c.execute("""INSERT INTO events (ts, event_type, severity, message, value)
                         VALUES (?, 'heat_alert', 'critical', ?, ?)""",
                      (ts, f"Temperature exceeded {TEMP_ALERT:.0f}°C", temp))

        prev.update({"led": led, "vent": vent, "away": away,
                     "hot": hot, "alert": alert, "dark": dark})

        tick += timedelta(seconds=SAMPLE_INTERVAL)

    # ---- rebuild summary ----
    c.execute("""
        INSERT INTO summary
        (hour_bucket, avg_temperature, min_temperature, max_temperature,
         avg_light, motion_count, led_on_count, vent_open_count, away_alert_count)
        SELECT
            strftime('%Y-%m-%d %H:00', ts),
            AVG(temperature), MIN(temperature), MAX(temperature),
            AVG(light), SUM(motion), SUM(led), SUM(vent),
            SUM(CASE WHEN away = 1 AND motion = 1 THEN 1 ELSE 0 END)
        FROM raw_readings
        GROUP BY strftime('%Y-%m-%d %H:00', ts)
        ON CONFLICT(hour_bucket) DO UPDATE SET
            avg_temperature  = excluded.avg_temperature,
            min_temperature  = excluded.min_temperature,
            max_temperature  = excluded.max_temperature,
            avg_light        = excluded.avg_light,
            motion_count     = excluded.motion_count,
            led_on_count     = excluded.led_on_count,
            vent_open_count  = excluded.vent_open_count,
            away_alert_count = excluded.away_alert_count
    """)

    conn.commit()
    conn.close()
    print("Seeded 24 hours of data into guardian.db")


if __name__ == "__main__":
    seed()