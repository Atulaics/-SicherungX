# SicherungX - Enterprise Data Leak Prevention (DLP) System

![SicherungX Banner](https://img.shields.io/badge/SicherungX-Enterprise_DLP-0f172a?style=for-the-badge&logo=shield&logoColor=38bdf8)
![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-Waitress-white?style=for-the-badge&logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css)

**SicherungX** is a next-generation, AI-driven Data Leak Prevention (DLP) system engineered for complete enterprise endpoint security. It pairs an autonomous Windows monitoring agent with an intelligent backend dashboard to provide real-time visibility, AI-based anomaly detection, and rapid threat neutralization.

---

## 🛡️ Core Features

### 1. Active Threat Mitigation (Kill Switch)
- **Manual Endpoint Isolation:** Administrators can instantly lock an employee's screen and block agent operations directly from the dashboard if a severe breach is detected.
- **Persistent Blocking:** The agent remains locked behind an un-closeable warning screen until an administrator explicitly unblocks the device.

### 2. Autonomous Endpoint Agent
- **USB & Peripheral Monitoring:** Logs all USB insertions and removals.
- **File System Tracking:** Detects high-volume file transfers, copying, or access to sensitive directories.
- **Network Traffic Analysis:** Monitors massive data uploads and unusual network activity.
- **Offline Resilience:** The agent queues telemetry data locally when disconnected and bulk-flushes it to the server immediately upon network reconnection, guaranteeing zero data loss.
- **Constant Heartbeat:** 15-second heartbeat cycle ensures the dashboard always displays accurate `Active` or `Offline` device statuses.

### 3. AI-Driven Anomaly Detection
- **Isolation Forest Model:** Automatically establishes a baseline for "normal" user activity.
- **Risk Scoring:** Assigns a risk score (0-100) to every intercepted event. Events scoring >70 are flagged as critical anomalies.

### 4. Advanced Administrative Command Center
- **Real-Time Live Feed:** A glassmorphism-styled, non-refreshing live activity feed to monitor all enterprise endpoints simultaneously.
- **Deep-Dive User Profiles:** View granular device information, historical logs, and specific risk trends for every employee.
- **Comprehensive Audit Logs:** Every administrative action (blocking a device, promoting a user, creating an account) is permanently logged to an immutable ledger for compliance.
- **Threat Alerts:** Dynamic notification badges alert administrators the moment an endpoint generates a high-risk event.

---

## 🏗️ Architecture & Technology Stack

SicherungX is built on a highly modular architecture designed for stability and scalability:

- **Frontend:** HTML5, modern vanilla JavaScript, Tailwind CSS (via CDN), and Chart.js for beautiful, responsive data visualization.
- **Backend:** Python (Flask) utilizing `Flask-Login` for secure session management and `Waitress` as a production-ready WSGI server.
- **Database:** SQLite3 (`sicherungx.db`) with highly optimized schema tables (`users`, `devices`, `activity_logs`, `alerts`, `audit_logs`).
- **Agent:** Multi-threaded Python daemon utilizing `psutil`, `WMI`, and `requests`. Compiled to a standalone `.exe` via PyInstaller.
- **Machine Learning:** `scikit-learn` (Isolation Forest) for dynamic risk analysis and model training.

---

## 🚀 Installation & Setup

### Prerequisites
- Windows OS (for the Agent)
- Python 3.10+ (for backend and AI)
- `pip` package manager

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/yourusername/sicherungx.git
cd sicherungx
pip install -r requirements.txt
```

### 2. Initialize the Database
Before running the system for the first time, you must initialize the database and create the default admin account.
```bash
python database/db_init.py
```
*Note: This creates an admin user with the username `admin` and password `password`.*

### 3. Start the Backend Server
Run the production WSGI server. This will host the API and the Admin Dashboard.
```bash
python backend/app.py
```
*The dashboard will be available at `http://localhost:5000` or your server's IP address.*

### 4. Deploy the Endpoint Agent
On the target Windows machine you wish to monitor, execute the Python agent. In a true enterprise environment, this script is compiled using PyInstaller and deployed via Active Directory Group Policy.
```bash
python agent/main.py
```

---

## 📖 Usage Guide

### Logging In
1. Navigate to `http://localhost:5000/login`.
2. Sign in using the default credentials (`admin` / `password`).
3. You will be redirected to the **Live Dashboard**.

### Managing Users
1. Go to **Manage Users** in the sidebar.
2. Click **Add New User** to register employees manually.
3. You can click **Promote** or **Demote** to change their privileges between `admin` and `employee`. 

### Remote Device Isolation (Kill Switch)
1. Navigate to **Manage Users** and click **View Profile** on the target employee.
2. Scroll to the **Device Info** section.
3. Click the red **Isolate Endpoint** button. 
4. The target user's computer will lock instantly, and they will be blocked from accessing their workstation until you click **Unblock Device**.

### Monitoring Threats
- The **Alerts** tab will flag any activity with a risk score over 70.
- The **Audit Logs** tab securely tracks all internal system changes made by administrators, ensuring compliance and accountability.

---

## 🛠️ Project Structure
```text
SicherungX/
├── agent/                  # Autonomous Windows monitoring daemon
│   ├── main.py             # Agent entry point and heartbeat loop
│   ├── system_monitor.py   # Core telemetry collectors
│   └── file_monitor.py     # File IO tracking
├── ai_model/               # Machine Learning anomaly detection
│   ├── detector.py         # Real-time risk scoring engine
│   └── train.py            # Isolation Forest model training script
├── backend/                # Flask API and Waitress server
│   ├── app.py              # Application factory and WSGI entry
│   └── routes.py           # Core endpoints (Auth, API, Agent telemetry)
├── dashboard/              # Frontend UI components
│   └── templates/          # HTML pages with Tailwind styling
│       ├── base.html       # Master layout
│       ├── index.html      # Live dashboard metrics
│       └── user_detail.html# Deep-dive user profile and isolation UI
└── database/               # Data persistence
    ├── db_init.py          # Schema initialization
    └── sicherungx.db       # SQLite relational database
```

---

## 🔒 Security Notice
SicherungX is a powerful tool capable of deep system monitoring and remote device locking. It is designed **strictly for authorized enterprise use**. Always ensure you have explicit consent and legal authority to monitor targeted endpoints in your jurisdiction.

---

*Engineered with precision for modern enterprise security.*
