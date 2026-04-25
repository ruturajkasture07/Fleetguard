# 🛡️ FleetGuard – Smart Transport Management System

A full-stack fleet management web application built with **Flask**, **Bootstrap 5**, and **MongoDB**.

---

## 📦 Tech Stack

| Layer      | Technology              |
|------------|-------------------------|
| Backend    | Python / Flask          |
| Frontend   | HTML + CSS + Bootstrap 5 |
| Database   | MongoDB (PyMongo)       |
| Payments   | Razorpay                |
| Icons      | Font Awesome 6          |
| Fonts      | Rajdhani + Inter (Google Fonts) |

---

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.8+
- MongoDB running locally (`mongod`) or a MongoDB Atlas URI
- (Optional) Razorpay account for payment integration

### 2. Clone / Extract the project

```bash
cd fleetguard
```

### 3. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Edit the `.env` file:

```env
SECRET_KEY=your_secret_key_here
MONGO_URI=mongodb://localhost:27017/
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret
```

> For MongoDB Atlas: `MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/`

### 6. Run the application

```bash
python app.py
```

Open your browser at: **http://127.0.0.1:5000**

---

## 🔐 Default Login Credentials

| Role  | Username | Password  |
|-------|----------|-----------|
| Admin | `admin`  | `admin123` |
| Driver | *(Create via Admin → Drivers → Add Driver)* | *(set during creation)* |

---

## 📋 Module Overview

### Admin Modules
| Module | URL | Description |
|--------|-----|-------------|
| Dashboard | `/dashboard` | Overview stats + recent alerts |
| Trucks | `/trucks` | Add, edit, change status |
| Drivers | `/drivers` | Add, assign trucks, manage |
| Shipments | `/shipments` | Create, assign, track status |
| Live Locations | `/admin/locations` | Monitor driver positions |
| Fuel Requests | `/admin/fuel-requests` | Approve/Reject + Razorpay payment |
| Accidents | `/admin/accidents` | View & resolve reports |
| Breakdowns | `/admin/breakdowns` | View & resolve reports |
| Call Requests | `/admin/call-requests` | View & mark done |

### Driver Modules
| Module | URL | Description |
|--------|-----|-------------|
| Dashboard | `/dashboard` | Quick actions + shipments |
| My Shipments | `/shipments` | View assigned shipments |
| Update Location | `/location` | Share current GPS position |
| Fuel Request | `/fuel-request` | Emergency fuel request |
| Accident Report | `/accident` | Report accidents |
| Breakdown Report | `/breakdown` | Report mechanical issues |
| Call Admin | `/call-request` | Request urgent callback |

---

## 💳 Razorpay Integration

1. Create an account at [razorpay.com](https://razorpay.com)
2. Go to **Settings → API Keys** and generate test keys
3. Add keys to `.env`:
   ```
   RAZORPAY_KEY_ID=rzp_test_xxxxxx
   RAZORPAY_KEY_SECRET=xxxxxxxx
   ```
4. When an admin **approves** a fuel request, the **Pay** button appears
5. Clicking it opens the Razorpay checkout popup
6. On success, payment status updates to **Paid** in the system

---

## 🗂️ Project Structure

```
fleetguard/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables
├── README.md                 # This file
└── templates/
    ├── base.html             # Shared layout (sidebar + topbar)
    ├── login.html            # Login page
    ├── admin_dashboard.html  # Admin overview
    ├── driver_dashboard.html # Driver portal
    ├── trucks.html           # Truck list
    ├── truck_form.html       # Add/Edit truck
    ├── drivers.html          # Driver list
    ├── driver_form.html      # Add/Edit driver
    ├── shipments.html        # Shipment list
    ├── shipment_form.html    # Create shipment
    ├── location_update.html  # Driver location update
    ├── admin_locations.html  # Admin location monitor
    ├── fuel_request.html     # Driver fuel request form
    ├── admin_fuel_requests.html # Admin fuel management + Razorpay
    ├── accident_report.html  # Driver accident form
    ├── admin_accidents.html  # Admin accident management
    ├── breakdown_report.html # Driver breakdown form
    ├── admin_breakdowns.html # Admin breakdown management
    ├── call_request.html     # Driver call request
    └── admin_call_requests.html # Admin call management
```

---

## 🔧 Troubleshooting

**MongoDB not connecting?**
- Make sure MongoDB is running: `mongod --dbpath /data/db`
- Or use MongoDB Atlas and update `MONGO_URI` in `.env`

**Razorpay payment not working?**
- Ensure you're using TEST keys (prefixed with `rzp_test_`)
- The `razorpay` package must be installed: `pip install razorpay`

**Port already in use?**
```bash
python app.py  # runs on port 5000
# or change port:
flask run --port 8080
```

---

## 📄 License
MIT License – Free to use and modify.
