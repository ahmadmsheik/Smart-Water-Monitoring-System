from datetime import datetime, timedelta, timezone
import sqlite3
import statistics
import json
import numpy as np
from sklearn.linear_model import LinearRegression
import pandas as pd
import os
import time
from flask import Response
from flask import Flask, request, jsonify, Response 
import threading
import firebase_admin # Add this
from firebase_admin import credentials, messaging # Add this

app = Flask(__name__)
DB_NAME = "water_usage.db"
last_zero_by_sensor = {}

latest_anomaly_hash = None


# --- Firebase Initialization --- ADD THIS BLOCK ---
# IMPORTANT: Keep 'serviceAccountKey.json' secure and out of version control.
if os.path.exists("shwms-b7382-firebase-adminsdk-fbsvc-34610d13b2.json"):
    cred = credentials.Certificate("shwms-b7382-firebase-adminsdk-fbsvc-34610d13b2.json")
    firebase_admin.initialize_app(cred)
else:
    print("⚠️ WARNING: serviceAccountKey.json not found. Push notifications will be disabled.")
# ----------------------------------------------------


# --- ADD THIS ENTIRE FUNCTION ---
@app.route('/register-device', methods=['POST'])
def register_device():
    data = request.get_json()
    token = data.get('token')

    if not token:
        return jsonify({"error": "Token is required"}), 400

    try:
        conn = sqlite3.connect(DB_NAME)
        # Use 'INSERT OR IGNORE' so duplicates don't cause an error
        conn.execute("INSERT OR IGNORE INTO device_tokens (token) VALUES (?)", (token,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Device registered successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ----------------------------------

# --- ADD THIS ENTIRE FUNCTION ---
def send_push_notification(title, body, data_payload=None):
    """Fetches all tokens and sends a push notification."""
    if not firebase_admin._apps:
        print("ℹ️ Firebase not initialized, skipping push notification.")
        return
        
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT token FROM device_tokens")
        tokens = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not tokens:
            print("📱 No device tokens found to send notification.")
            return

        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data_payload,
            tokens=tokens,
        )

        response = messaging.send_multicast(message)
        print(f'🚀 Successfully sent notification to {response.success_count} devices.')
        if response.failure_count > 0:
            print(f'💀 Failed to send to {response.failure_count} devices.')

    except Exception as e:
        print(f"🔴 Error sending push notification: {e}")
# ----------------------------------


# --- DATABASE SETUP ---
# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    c = conn.cursor()
    # Creates the flow_data table
    c.execute('''
        CREATE TABLE IF NOT EXISTS flow_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT,
            timestamp TEXT,
            flow_rate REAL,
            total REAL
        )
    ''')
    # Creates the device_tokens table
    c.execute("CREATE TABLE IF NOT EXISTS device_tokens (token TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()
    
# --- STORE DATA ---
def save_flow_data(sensor_id, flow_rate, total):
    global last_zero_by_sensor
    timestamp = datetime.now().isoformat()
    
    # Skip saving repeated 0 flow rates
    if flow_rate == 0.0:
        if last_zero_by_sensor.get(sensor_id) == 0.0:
            return  # Skip duplicate zero
        last_zero_by_sensor[sensor_id] = 0.0
    else:
        last_zero_by_sensor[sensor_id] = flow_rate
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO flow_data (sensor_id, timestamp, flow_rate, total) VALUES (?, ?, ?, ?)",
              (sensor_id, timestamp, flow_rate, total))
    conn.commit()
    conn.close()    
    
# --- HELPER ---
def load_daily_usage():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM flow_data", conn)
    conn.close()

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    sensor_1 = df[df['sensor_id'] == '1'].copy()
    daily = sensor_1.groupby('date')['total'].max().diff().fillna(0)
    daily[daily < 0] = 0

    return pd.DataFrame({
        'date': daily.index,
        'usage': daily.values
    })


    
# --- ANALYTICS & AI AGENT ---
def analyze_usage():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT timestamp, flow_rate FROM flow_data")
    rows = c.fetchall()
    conn.close()

    if not rows:
        return {"message": "No data yet."}

    hourly_usage = {}
    daily_total = {}
    session_durations = []

    session_start = None
    session_total = 0

    for row in rows:
        ts = datetime.fromisoformat(row[0])
        rate = row[1]
        hour = ts.hour
        date = ts.date()

        # Hourly stats
        hourly_usage.setdefault(hour, []).append(rate)
        # Daily stats
        daily_total[date] = daily_total.get(date, 0) + rate

        # Session analysis (e.g. shower run)
        if rate > 0:
            if session_start is None:
                session_start = ts
                session_total = 0
            session_total += 1
        else:
            if session_start:
                duration = (ts - session_start).total_seconds() / 60  # minutes
                session_durations.append(duration)
                session_start = None

    average_hourly = {h: round(statistics.mean(rates), 2) for h, rates in hourly_usage.items()}
    average_sessions = round(statistics.mean(session_durations), 2) if session_durations else 0

    return {
        "average_hourly_flow_rate": average_hourly,
        "total_daily_usage": {str(k): round(v, 2) for k, v in daily_total.items()},
        "avg_session_duration_minutes": average_sessions
    }
    

# ________ How data are being presented ________    
"""
{
  "average_hourly_flow_rate": {
    "7": 1.22,
    "8": 2.51
  },
  "total_daily_usage": {
    "2025-04-10": 122.5,
    "2025-04-11": 131.3
  },
  "avg_session_duration_minutes": 6.5
}

Data received by the flutter app.
    """


    
# --- API ROUTE FOR DATA ---
@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.get_json()
        sensor_id = data.get('sensor_id')
        flow_rate = data.get('flow_rate')
        total = data.get('total')

         # Strict validation
        if sensor_id not in ['1', '2', '3'] or not isinstance(flow_rate, (int, float)) or not isinstance(total, (int, float)):
            return jsonify({"error": "Invalid or missing data"}), 400

        save_flow_data(sensor_id, flow_rate, total)
        return jsonify({"status": "data saved"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
# @app.route('/analyze', methods=['GET'])
# def get_analysis():
#     return jsonify(analyze_usage())

# @app.route('/stream')
# def stream_flow_rate():
#     def event_stream():
#         last_id = None
#         while True:
#             conn = sqlite3.connect(DB_NAME)
#             c = conn.cursor()
#             c.execute("SELECT id, flow_rate FROM flow_data ORDER BY id DESC LIMIT 1")
#             row = c.fetchone()
#             conn.close()
#             if row and row[0] != last_id:
#                 last_id = row[0]
#                 yield f"data: {row[1]}\n\n"
#             time.sleep(1)  # adjust refresh rate as needed
#     return Response(event_stream(), mimetype="text/event-stream")

# @app.route('/stream/<int:sensor_id>')
# def stream_flow_rate(sensor_id):
#     def event_stream():
#         last_id = None
#         while True:
#             conn = sqlite3.connect(DB_NAME)
#             c = conn.cursor()
#             c.execute(
#                 "SELECT id, flow_rate FROM flow_data WHERE sensor_id = ? ORDER BY id DESC LIMIT 1",
#                 (str(sensor_id),)
#             )
#             row = c.fetchone()
#             conn.close()

#             if row is None:
#                 time.sleep(1)
#                 continue

#             # ✅ Always yield first value, then check for updates
#             if last_id is None or row[0] != last_id:
#                 last_id = row[0]
#                 yield f"data: {row[1]}\n\n"

#             time.sleep(1)
#     return Response(event_stream(), mimetype="text/event-stream")

@app.route('/stream/<int:sensor_id>')
def stream_flow_rate(sensor_id):
    def event_stream():
        print(f"[STREAM] Client connected to /stream/{sensor_id}")
        while True:
            try:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute(
                    "SELECT id, flow_rate FROM flow_data WHERE sensor_id = ? ORDER BY id DESC LIMIT 1",
                    (str(sensor_id),)
                )
                row = c.fetchone()
                conn.close()

                if row is not None:
                    print(f"[STREAM] Sensor {sensor_id}: flow_rate = {row[1]}")
                    yield f"data: {row[1]}\n\n"
                else:
                    print(f"[STREAM] No data for sensor {sensor_id}")

                time.sleep(1)
            except Exception as e:
                print(f"[STREAM ERROR] Sensor {sensor_id}: {e}")
                break

    return Response(event_stream(), mimetype="text/event-stream")




@app.route('/analyze', methods=['GET'])
def analyze_usage():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT timestamp, flow_rate FROM flow_data")
    rows = c.fetchall()
    conn.close()

    if not rows:
        return {"message": "No data yet."}

    # --- Preprocess
    df = pd.DataFrame(rows, columns=["timestamp", "flow_rate"])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour
    df['day'] = df['timestamp'].dt.to_period("D")
    df['week'] = df['timestamp'].dt.to_period("W")
    df['month'] = df['timestamp'].dt.to_period("M")

    today = datetime.now().date()
    current_week = datetime.now().date().isocalendar()[1]
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Calculate last month and year
    if current_month == 1:
        last_month = 12
        last_month_year = current_year - 1
    else:
        last_month = current_month - 1
        last_month_year = current_year

    # --- Usage Calculations
    today_usage = df[df['date'] == today]['flow_rate'].sum()
    this_week_usage = df[df['timestamp'].dt.isocalendar().week == current_week]['flow_rate'].sum()
    this_month_usage = df[df['timestamp'].dt.month == current_month]['flow_rate'].sum()
    last_month_usage = df[(df['timestamp'].dt.month == last_month) & (df['timestamp'].dt.year == last_month_year)]['flow_rate'].sum()

    # --- Hourly Average (today only)
    today_mask = df['date'] == today
    average_hourly_today = df[today_mask].groupby('hour')['flow_rate'].mean().round(2).to_dict()

    # --- Full Daily for Plot (only this week)
    week_mask = df['timestamp'].dt.isocalendar().week == current_week
    daily_this_week = df[week_mask].groupby('date')['flow_rate'].sum().round(2).to_dict()

    # --- Monthly Plot Data (only this month)
    month_mask = df['timestamp'].dt.month == current_month
    monthly_this_month = df[month_mask].groupby(df[month_mask]['timestamp'].dt.to_period("M"))['flow_rate'].sum().round(2)
    monthly_this_month = {str(k): float(v) for k, v in monthly_this_month.items()}

    return {
        "today_usage": round(today_usage, 2),
        "this_week_usage": round(this_week_usage, 2),
        "this_month_usage": round(this_month_usage, 2),
        "last_month_usage": round(last_month_usage, 2),
        "average_hourly_flow_rate": average_hourly_today,
        "daily_plot_data": {str(k): float(v) for k, v in daily_this_week.items()},
        "monthly_plot_data": monthly_this_month
    }



# --- CONSISTENCY CHECK ---
@app.route('/consistency', methods=['GET'])
def check_consistency():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT timestamp, sensor_id, flow_rate FROM flow_data ORDER BY timestamp", conn)
    conn.close()

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    grouped = df.groupby('timestamp')

    inconsistencies = []
    for ts, group in grouped:
        sensors = group.set_index('sensor_id')['flow_rate'].to_dict()
        f1 = sensors.get('1', None)
        f2 = sensors.get('2', 0)
        f3 = sensors.get('3', 0)
        if f1 is not None and abs(f1 - (f2 + f3)) > 0.5:
            inconsistencies.append({
                "timestamp": ts.isoformat(),
                "sensor_1": f1,
                "sensor_2": f2,
                "sensor_3": f3,
                "expected": round(f2 + f3, 2)
            })
    return jsonify({"inconsistencies": inconsistencies})
    
# --- C. Forecast Next 7 Days ---
# @app.route('/forecast', methods=['GET'])
# def predict_next_week():
#     df = load_daily_usage()
#     if len(df) < 7:
#         return jsonify({"message": "Not enough data for prediction"}), 200

#     df['date'] = pd.to_datetime(df['date'])
#     df['day_of_week'] = df['date'].dt.weekday  # 0 = Monday
#     df['prev_day'] = df['usage'].shift(1)
#     df['rolling_avg_3'] = df['usage'].rolling(window=3).mean()
#     df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

#     df.dropna(inplace=True)

#     # Feature matrix X and label y
#     X = df[['day_of_week', 'prev_day', 'rolling_avg_3', 'is_weekend']]
#     y = df['usage']

#     model = LinearRegression()
#     model.fit(X, y)

#     # Forecast next 7 days
#     last_row = df.iloc[-1]
#     future = []
#     for i in range(1, 8):
#         next_date = last_row['date'] + timedelta(days=1)
#         next_dow = next_date.weekday()
#         is_weekend = 1 if next_dow in [5, 6] else 0
#         prev = last_row['usage']
#         roll = df['usage'].tail(3).mean()

#         features = [[next_dow, prev, roll, is_weekend]]
#         pred = model.predict(features)[0]

#         future.append((str(next_date.date()), round(pred, 2)))

#         # Update for next loop
#         new_row = {
#             'date': next_date,
#             'usage': pred
#         }
#         df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
#         last_row = new_row

#     return jsonify({"forecast": dict(future)})

@app.route('/forecast', methods=['GET'])
def predict_next_week():
    df = load_daily_usage()
    
    df.dropna(inplace=True)
    if len(df) < 1:
        return jsonify({"message": "Not enough data after preprocessing"}), 200


    df['date'] = pd.to_datetime(df['date'])
    df['day_of_week'] = df['date'].dt.weekday  # 0 = Monday
    df['prev_day'] = df['usage'].shift(1)
    df['rolling_avg_3'] = df['usage'].rolling(window=3).mean()
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

    df.dropna(inplace=True)

    # Feature matrix X and label y
    X = df[['day_of_week', 'prev_day', 'rolling_avg_3', 'is_weekend']]
    y = df['usage']

    model = LinearRegression()
    model.fit(X, y)

    # Forecast next 3 days
    last_row = df.iloc[-1]
    future = []
    for i in range(1, 4):  # only next 3 days
        next_date = last_row['date'] + timedelta(days=1)
        next_dow = next_date.weekday()
        is_weekend = 1 if next_dow in [5, 6] else 0
        prev = last_row['usage']
        roll = df['usage'].tail(3).mean()

        features = [[next_dow, prev, roll, is_weekend]]
        pred = model.predict(features)[0]

        future.append((str(next_date.date()), round(pred, 2)))

        # Update for next loop
        new_row = {
            'date': next_date,
            'usage': pred
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        last_row = new_row

    return jsonify({"forecast": dict(future)})



# @app.route('/anomaly', methods=['GET'])
# def detect_anomalies():
#     data = load_daily_usage()
#     print(data)
#     if data.empty:
#         return jsonify({"message": "Not enough data"}), 200

#     mean = data.mean()
#     std = data.std()
#     threshold = 0.1
#     anomalies = data[(data - mean).abs() > threshold * std]

#     return jsonify({
#         "mean_usage": round(mean, 2),
#         "std_dev": round(std, 2),
#         "anomalies": {str(date): round(val, 2) for date, val in anomalies.items()},
#     })


#####  ######   Did any day look statistically strange compared with the past? ####### ########
# @app.route('/anomaly', methods=['GET'])
# def detect_anomalies():
#     conn = sqlite3.connect(DB_NAME)
#     df = pd.read_sql_query("SELECT timestamp,sensor_id,flow_rate FROM flow_data", conn)
#     conn.close()
#     if df.empty:
#         return jsonify({"message": "No data"}), 200

#     df['timestamp'] = pd.to_datetime(df['timestamp'])
#     wide = df.pivot(index='timestamp', columns='sensor_id', values='flow_rate').fillna(0)

#     wide['residual'] = wide['1'] - (wide['2'] + wide['3'])
#     resid_std = wide['residual'].rolling('24h').std().iloc[-1] or 0
#     k = 3
#     mb_mask = wide['residual'].abs() > k * resid_std


#     stuck_events = []
#     for sid in ['2', '3']:
#         above = wide[sid] > 0.1  
#         runs = (above != above.shift()).cumsum()
#         for run_id, grp in wide.groupby(runs):
#             if above.loc[grp.index[0]] and grp.shape[0] >= 15:  
#                 stuck_events.append({
#                     "sensor": sid,
#                     "start": grp.index[0].isoformat(),
#                     "end": grp.index[-1].isoformat(),
#                     "duration_minutes": len(grp)
#                 })

#     resp = {
#         "mass_balance": wide[mb_mask][['1','2','3','residual']].tail(20).to_dict(orient="index"),
#         "tap_stuck_on": stuck_events
#     }
#     return jsonify(resp)


# @app.route('/anomaly-stream')
# def live_anomaly_stream():
#     def generate():
#         global latest_anomaly_hash
#         while True:
#             time.sleep(30)

#             result = detect_latest_anomalies()
#             if result is None:
#                 continue

#             current_hash = json.dumps(result, sort_keys=True)

#             if current_hash != latest_anomaly_hash:
#                 latest_anomaly_hash = current_hash

#                 # Save to JSON file
#                 with open("anomalies_output.json", "w") as f:
#                     json.dump(result, f, indent=2)

#                 yield f"data: {current_hash}\n\n"

#     return Response(stream_with_context(generate()), mimetype='text/event-stream')


anomaly_history = []  # keep track of saved anomalies

def anomaly_detection_loop():
    global anomaly_history

    while True:
        time.sleep(5)
        print("⏳ Checking for anomalies...")

        result = detect_latest_anomalies()
        if result is None:
            continue

        # Load existing anomalies from file if any
        if os.path.exists("anomalies_output.json"):
            with open("anomalies_output.json", "r") as f:
                try:
                    existing = json.load(f)
                    anomaly_history = existing.get("anomalies", [])
                except json.JSONDecodeError:
                    anomaly_history = []
        else:
            anomaly_history = []

        # Helper to find last anomaly of a given type in history
        def find_last_anomaly_of_type(anomaly_type):
            # Return the most recent anomaly dict from history with this type non-empty
            filtered = [a for a in anomaly_history if anomaly_type in a and a[anomaly_type]]
            if not filtered:
                return None
            # Sort by saved_at descending
            filtered_sorted = sorted(filtered, key=lambda x: x.get("saved_at", ""), reverse=True)
            return filtered_sorted[0]

        # Flag to decide if we save this anomaly at all
        should_save = False

        # Check each anomaly type in the new result
        for anomaly_type in ["mass_balance", "tap_stuck_on", "inactive_pipe"]:
            new_data = result.get(anomaly_type, None)
            if new_data is None:
                continue  # no such anomaly type in new anomaly

            # Find last saved anomaly of this type with non-empty data
            last = find_last_anomaly_of_type(anomaly_type)

            if last is None:
                # No previous anomaly of this type - save new one if it's not empty
                if new_data:  # non-empty dict/list
                    should_save = True
                    break  # No need to check others, we save
            else:
                # Last anomaly exists and is non-empty
                if not new_data:
                    # New anomaly of this type is empty, treat as new (save)
                    should_save = True
                    break
                else:
                    # Compare saved times
                    try:
                        last_time_str = last.get("saved_at")
                        if last_time_str:
                            last_time_dt = datetime.fromisoformat(last_time_str)
                            current_time_utc = datetime.now(timezone.utc)
                            # Make sure last_time_dt is aware
                            if last_time_dt.tzinfo is None:
                                last_time_dt = last_time_dt.replace(tzinfo=timezone.utc)

                            delta = current_time_utc - last_time_dt
                            if delta >= timedelta(hours=1):
                                # More than 1 hour since last anomaly of this type, save
                                should_save = True
                                break
                            else:
                                # Less than 1 hour, do not save
                                print(f"⏳ Anomaly of type '{anomaly_type}' detected less than 1 hour ago; skipping save.")
                        else:
                            # No timestamp? Save anyway
                            should_save = True
                            break
                    except Exception as e:
                        print(f"⚠️ Error parsing saved_at: {e}")
                        # On error, save anyway
                        should_save = True
                        break

        if should_save:
            # Add current UTC timestamp
            result["saved_at"] = datetime.now(timezone.utc).isoformat()

            anomaly_history.append(result)

            with open("anomalies_output.json", "w") as f:
                json.dump({"anomalies": anomaly_history}, f, indent=2)

            print("✅ New anomaly saved.")
            

            title = "🚨 Anomaly Detected!"
            body = "A potential water leak or stuck tap has been detected."
            send_push_notification(title, body)

        else:
            print("ℹ️ No new anomaly to save after checking history.")


def detect_latest_anomalies():
    print("\n🔍 Running anomaly detection...")

    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT timestamp, sensor_id, flow_rate FROM flow_data", conn)
    conn.close()

    if df.empty:
        print("⚠️ No data in database.")
        return None

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    wide = df.pivot(index='timestamp', columns='sensor_id', values='flow_rate').fillna(0)

    if not all(s in wide.columns for s in ['1', '2', '3']):
        print("⚠️ Missing one or more sensors (1, 2, 3) in data.")
        return None

    # --- Mass Balance ---
    wide['residual'] = wide['1'] - (wide['2'] + wide['3'])

    now = wide.index.max()
    one_minute_ago = now - pd.Timedelta(minutes=1)
    recent = wide.loc[one_minute_ago:now]

    if recent.empty:
        print("⚠️ No recent data in the last 1 minute.")
        return None

    min_residual_threshold = 1.5  # or 2.0 depending on your expected usage
    std = recent['residual'].std() or 0
    tolerance = 0.05
    k = 1.5
    threshold = max(k * std + tolerance, min_residual_threshold)
    

    print(f"📊 STD: {std:.5f} | Tolerance: {tolerance} | Threshold: {threshold:.5f}")
    print("📈 Recent residuals:")
    print(recent['residual'].tail(10))

    mask = recent['residual'].abs() > threshold
    mass_anomalies = recent[mask].tail(1).to_dict(orient="index")

    if mass_anomalies:
        print("🚨 Mass balance anomaly detected:")
        print(json.dumps({k.isoformat(): v for k, v in mass_anomalies.items()}, indent=2))

    # --- Stuck Taps ---
    stuck = []
    for sid in ['2', '3']:
        flow = recent[sid] > 0.1
        runs = (flow != flow.shift()).cumsum()
        for _, grp in recent.groupby(runs):
            if flow.loc[grp.index[0]] and grp.shape[0] >= 5:  # ~5 seconds continuous
                stuck_event = {
                    "sensor": sid,
                    "start": grp.index[0].isoformat(),
                    "end": grp.index[-1].isoformat(),
                    "duration_seconds": len(grp)
                }
                stuck.append(stuck_event)
                print(f"🚰 Tap stuck ON detected: {json.dumps(stuck_event, indent=2)}")

    if not mass_anomalies and not stuck:
        print("🟢 No anomalies detected in this cycle.")
        return None

    return {
        "mass_balance": {
            k.isoformat(): v for k, v in mass_anomalies.items()
        },
        "tap_stuck_on": stuck
    }


@app.route('/latest-anomalies', methods=['GET'])
def get_latest_anomalies():
    try:
        with open("anomalies_output.json", "r") as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"message": "No anomalies detected yet"}), 200
    
if __name__ == '__main__':
    t = threading.Thread(target=anomaly_detection_loop, daemon=True)
    t.start()
    
    app.run(debug=True, host='0.0.0.0', port=5000)