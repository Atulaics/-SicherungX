# SicherungX - Comprehensive Technical Documentation

This document serves as the complete technical blueprint for the **SicherungX** Data Leak Prevention (DLP) system. It outlines the architectural design, internal data flows, machine learning mechanisms, and provides direct instructions on how to access and modify the underlying database.

---

## 1. System Architecture

SicherungX operates on a classic **Client-Server Architecture** but is heavily augmented with asynchronous background processing and edge-level AI evaluation.

### Components
1. **The Edge Agent (`/agent`)**: A lightweight Python daemon running on target Windows machines. It uses multi-threading to simultaneously monitor system state (USB state, file I/O, network traffic). It caches data locally in RAM if the network goes down and bulk-transmits it via a REST API.
2. **The Intelligence Core (`/ai_model`)**: An Isolation Forest machine learning model. Instead of relying purely on static rules, this model evaluates event vectors (data size, file count, time of day) to detect statistical anomalies.
3. **The Central API (`/backend`)**: A Flask-based RESTful API served by Waitress. It ingests data from thousands of potential agents, routes it through the AI model, and stores it in the database.
4. **The Administrative Dashboard (`/dashboard`)**: A Jinja-rendered frontend utilizing Tailwind CSS and JavaScript. It polls the backend API asynchronously to provide a "live" non-refreshing view of the enterprise.

---

## 2. Telemetry Data Flow

1. **Collection**: The Agent detects a user copying 500MB of files to a USB drive.
2. **Transmission**: The Agent packages this into JSON: `{"activity_type": "USB_ACTIVITY", "details": "500MB copied", ...}` and POSTs it to `http://<server-ip>:5000/api/submit`.
3. **AI Evaluation**: The Flask backend receives the payload and passes the numerical parameters (size, counts) to `detector.py`. The AI returns an anomaly flag (`1` or `0`) and a Risk Score (`0-100`).
4. **Persistence**: The backend writes the enriched log to the `activity_logs` SQLite table. If the risk score > 70, it simultaneously writes a record to the `alerts` table.
5. **Visualization**: The Administrator's dashboard, which polls `/api/logs` every 5 seconds, instantly fetches the new row and updates the Live Feed UI, flashing a red warning if an anomaly is detected.

---

## 3. Database Architecture & Schema

SicherungX utilizes a local SQLite3 relational database (`sicherungx.db`) for zero-configuration deployment and lightning-fast read/write operations.

### Core Tables
- **`users`**: Stores employee and admin credentials (hashed passwords, roles).
- **`devices`**: Tracks registered endpoints, linking a `device_id` (MAC address hash) to a `user_id`. Also stores the `is_blocked` flag for the Kill Switch.
- **`activity_logs`**: The central ledger for all agent telemetry.
- **`alerts`**: High-risk events segregated for rapid administrative review.
- **`audit_logs`**: An immutable ledger tracking actions performed by administrators (e.g., blocking a device, creating a user).

---

## 4. How to Access the Database

Because the database is a standard SQLite file, you do not need heavy server software (like MySQL or PostgreSQL) to view or edit the raw data.

### Method A: Using a Graphical Interface (Recommended)
1. Download and install **[DB Browser for SQLite](https://sqlitebrowser.org/)**.
2. Open the application and click **"Open Database"**.
3. Navigate to your project folder and select: `SicherungX/database/sicherungx.db`.
4. Go to the **"Browse Data"** tab.
5. You can now select any table (e.g., `activity_logs` or `users`) from the dropdown and view, edit, or delete rows just like an Excel spreadsheet. 
6. *Click "Write Changes" at the top to save any edits.*

### Method B: Using the Command Line (CLI)
If you have SQLite installed in your terminal, you can query the database directly.

1. Open your terminal (PowerShell or Command Prompt).
2. Navigate to the project root:
   ```bash
   cd "c:\Users\your_name\Downloads\SicherungX"
   ```
3. Open the database:
   ```bash
   sqlite3 database/sicherungx.db
   ```
4. **Useful Queries to Run:**
   
   *See all registered users:*
   ```sql
   SELECT id, username, role FROM users;
   ```
   
   *Check the block status of all devices:*
   ```sql
   SELECT device_name, system_username, is_blocked FROM devices;
   ```

   *Find the 5 most recent high-risk alerts:*
   ```sql
   SELECT timestamp, username, activity_type, risk_score FROM activity_logs WHERE risk_score > 70 ORDER BY timestamp DESC LIMIT 5;
   ```

   *Manually reset a forgotten Admin password (sets it to 'password'):*
   ```sql
   UPDATE users SET password_hash = 'scrypt:32768:8:1$yXGzXGzX$...' WHERE username = 'admin';
   ```
   *(To exit the SQLite prompt, type `.quit` and hit Enter).*

---

## 5. Security & Threat Mitigation (The "Kill Switch")

When an administrator clicks **"Isolate Endpoint"** on the dashboard:
1. An AJAX request hits `/api/device/<id>/block`.
2. The SQLite `devices` table updates `is_blocked = 1`.
3. The Agent, which sends a heartbeat ping to `/api/submit` every 15 seconds, receives a JSON response: `{"command": "isolate"}`.
4. The Agent triggers the Windows API `ctypes.windll.user32.LockWorkStation()` to instantly lock the OS, and renders a full-screen Tkinter UI warning that cannot be bypassed by the user.

---

## 6. Extending the System (Future Roadmap)

To upgrade this system for a 10,000+ employee environment:
1. **Database Migration:** Replace SQLite with **PostgreSQL**. Simply update the `get_db_connection()` function in `backend/routes.py` to use `psycopg2` or `SQLAlchemy`.
2. **WebSocket Integration:** Replace the 5-second Javascript `setInterval` polling with `Flask-SocketIO` to push alerts to the dashboard with zero milliseconds of latency.
3. **Agent Obfuscation:** Use tools like `PyArmor` before compiling the Agent with `PyInstaller` to prevent users from reverse-engineering the monitoring logic.
