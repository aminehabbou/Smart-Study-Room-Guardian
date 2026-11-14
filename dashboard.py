"""
dashboard.py — Flask server for the Smart Study Room Guardian.
Serves two pages plus a small JSON API used by the frontend.
Auto-detects the sample interval from the database.
"""
from flask import Flask, render_template, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB = "guardian.db"

# Fallback if the DB is empty
DEFAULT_SAMPLE_INTERVAL = 2.0


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def detect_sample_interval(conn):
    """Return the median interval between recent rows (in seconds)."""
    rows = conn.execute("""
        SELECT ts FROM raw_readings ORDER BY id DESC LIMIT 100
    """).fetchall()
    if len(rows) < 2:
        return DEFAULT_SAMPLE_INTERVAL
    times = [datetime.fromisoformat(r["ts"]) for r in rows]
    diffs = sorted((times[i] - times[i+1]).total_seconds()
                   for i in range(len(times) - 1))
    median = diffs[len(diffs) // 2]
    return median if median > 0 else DEFAULT_SAMPLE_INTERVAL


@app.route("/")
def index():
    return render_template("index.html", page="live")


@app.route("/report")
def report():
    return render_template("report.html", page="report")


@app.route("/api/current")
def api_current():
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM raw_readings ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return jsonify(dict(row) if row else {})


@app.route("/api/live")
def api_live():
    conn = get_db()
    rows = conn.execute("""
        SELECT ts, temperature, light
        FROM raw_readings
        ORDER BY id DESC LIMIT 60
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in reversed(rows)])


@app.route("/api/events")
def api_events():
    conn = get_db()
    rows = conn.execute("""
        SELECT ts, event_type, severity, message, value
        FROM events
        ORDER BY id DESC LIMIT 30
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/stats")
def api_stats():
    conn = get_db()
    c = conn.cursor()
    interval = detect_sample_interval(conn)

    today = c.execute("""
        SELECT
            AVG(temperature) AS avg_temp,
            MIN(temperature) AS min_temp,
            MAX(temperature) AS max_temp,
            AVG(light) AS avg_light,
            COUNT(*) AS total_readings,
            SUM(led) AS led_samples,
            SUM(motion) AS motion_samples,
            SUM(vent) AS vent_samples,
            SUM(occupied) AS occupied_samples
        FROM raw_readings
        WHERE ts >= date('now')
    """).fetchone()
    today_d = dict(today) if today else {}

    led_hours      = (today_d.get("led_samples") or 0) * interval / 3600
    motion_hours   = (today_d.get("motion_samples") or 0) * interval / 3600
    vent_hours     = (today_d.get("vent_samples") or 0) * interval / 3600
    occupied_hours = (today_d.get("occupied_samples") or 0) * interval / 3600
    total_hours    = (today_d.get("total_readings") or 0) * interval / 3600

    alerts = c.execute("""
        SELECT COUNT(*) AS cnt FROM events
        WHERE event_type = 'intruder_alert'
        AND ts >= datetime('now', '-7 days')
    """).fetchone()

    motion_by_hour = c.execute("""
        SELECT strftime('%Y-%m-%d %H:00', ts) AS hour, COUNT(*) AS cnt
        FROM raw_readings
        WHERE motion = 1 AND ts >= datetime('now', '-1 day')
        GROUP BY hour
        ORDER BY hour
    """).fetchall()

    events_by_type = c.execute("""
        SELECT event_type, severity, COUNT(*) AS cnt
        FROM events
        WHERE ts >= date('now')
        GROUP BY event_type
        ORDER BY cnt DESC
    """).fetchall()

    temp_by_hour = c.execute("""
        SELECT strftime('%H:00', ts) AS hour, AVG(temperature) AS avg_t
        FROM raw_readings
        WHERE ts >= date('now')
        GROUP BY strftime('%H', ts)
        ORDER BY hour
    """).fetchall()

    conn.close()

    return jsonify({
        "sample_interval": interval,
        "today": {
            "avg_temp":       round(today_d.get("avg_temp") or 0, 1),
            "min_temp":       round(today_d.get("min_temp") or 0, 1),
            "max_temp":       round(today_d.get("max_temp") or 0, 1),
            "avg_light":      round(today_d.get("avg_light") or 0),
            "led_hours":      round(led_hours, 2),
            "motion_hours":   round(motion_hours, 2),
            "vent_hours":     round(vent_hours, 2),
            "occupied_hours": round(occupied_hours, 2),
            "total_hours":    round(total_hours, 2),
        },
        "week": {"alerts": alerts["cnt"] if alerts else 0},
        "motion_by_hour": [dict(r) for r in motion_by_hour],
        "events_by_type": [dict(r) for r in events_by_type],
        "temp_by_hour":   [dict(r) for r in temp_by_hour],
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)