from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, timedelta
from functools import wraps
import json
import os
import random
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fleetguard_secret_2024')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

SQLITE_PATH = os.environ.get('SQLITE_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fleetguard.db'))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    name TEXT,
    surname TEXT,
    phone TEXT,
    email_verified INTEGER DEFAULT 0,
    phone_verified INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS trucks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    truck_number TEXT UNIQUE NOT NULL,
    truck_type TEXT,
    capacity TEXT,
    status TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS drivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    driver_name TEXT,
    surname TEXT,
    phone TEXT,
    license_number TEXT,
    experience TEXT,
    assigned_truck TEXT,
    username TEXT,
    paused_until TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id TEXT UNIQUE NOT NULL,
    item_type TEXT,
    weight TEXT,
    pickup_location TEXT,
    delivery_location TEXT,
    dimensions TEXT,
    assigned_truck TEXT,
    driver_id INTEGER,
    customer_id INTEGER,
    status TEXT,
    payment_status TEXT,
    payment_amount REAL,
    is_frozen INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT,
    delivery_otp TEXT,
    delivery_otp_generated_at TEXT,
    delivered_at TEXT
);
CREATE TABLE IF NOT EXISTS locations (
    driver_id INTEGER PRIMARY KEY,
    driver_name TEXT,
    truck_number TEXT,
    current_location TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS location_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER NOT NULL,
    driver_name TEXT,
    truck_number TEXT,
    current_location TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    source TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fuel_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER,
    driver_name TEXT,
    truck_number TEXT,
    current_location TEXT,
    fuel_required TEXT,
    amount REAL,
    status TEXT,
    payment_status TEXT,
    razorpay_order_id TEXT,
    payment_id TEXT,
    paid_at TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS accidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER,
    driver_name TEXT,
    truck_number TEXT,
    location TEXT,
    description TEXT,
    accident_type TEXT,
    latitude REAL,
    longitude REAL,
    status TEXT,
    created_at TEXT,
    resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS accident_fund_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    accident_id INTEGER NOT NULL,
    driver_id INTEGER,
    driver_name TEXT,
    accident_type TEXT,
    requested_amount REAL,
    purpose TEXT,
    status TEXT,
    created_at TEXT,
    resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS user_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    email_otp TEXT,
    phone_otp TEXT,
    expires_at TEXT NOT NULL,
    verified_at TEXT
);
CREATE TABLE IF NOT EXISTS app_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    role_target TEXT,
    message TEXT NOT NULL,
    category TEXT,
    link TEXT,
    created_at TEXT NOT NULL,
    read_at TEXT
);
CREATE TABLE IF NOT EXISTS breakdowns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER,
    driver_name TEXT,
    truck_number TEXT,
    location TEXT,
    problem_description TEXT,
    status TEXT,
    created_at TEXT,
    resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS call_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER,
    driver_name TEXT,
    truck_number TEXT,
    message TEXT,
    status TEXT,
    created_at TEXT,
    resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS fuel_payment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fuel_request_id INTEGER NOT NULL,
    event TEXT NOT NULL,
    razorpay_order_id TEXT,
    razorpay_payment_id TEXT,
    amount_paise INTEGER,
    detail TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS driver_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    category TEXT,
    fuel_request_id INTEGER,
    created_at TEXT NOT NULL,
    read_at TEXT
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id TEXT NOT NULL,
    sender_id INTEGER NOT NULL,
    sender_role TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS maintenance_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    truck_id INTEGER NOT NULL REFERENCES trucks(id),
    amount REAL NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS driver_payroll (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER NOT NULL REFERENCES drivers(id),
    amount REAL NOT NULL,
    period_start TEXT,
    period_end TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shipment_routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id TEXT NOT NULL,
    planned_route_json TEXT, -- List of [lat, lng]
    actual_path_json TEXT, -- List of [lat, lng]
    eta TEXT,
    distance REAL,
    last_optimized_at TEXT
);
CREATE TABLE IF NOT EXISTS route_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id TEXT NOT NULL,
    alert_type TEXT NOT NULL, -- 'Deviation', 'Delay', 'HOS_Violation'
    message TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dispatch_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dispatch_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id TEXT NOT NULL,
    decision_type TEXT NOT NULL, -- 'Automated' or 'Manual'
    algo_version TEXT,
    parameters_json TEXT,
    compatibility_score REAL,
    assigned_driver_id INTEGER,
    override_reason TEXT,
    admin_id INTEGER,
    created_at TEXT NOT NULL
);
"""

conn = None


def get_conn():
    global conn
    if conn is None:
        conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
    return conn

app.jinja_env.filters['from_json'] = json.loads

def row_to_dict(row):
    if row is None:
        return None
    d = {k: row[k] for k in row.keys()}
    for key, value in list(d.items()):
        if key.endswith('_at') and isinstance(value, str):
            try:
                d[key] = datetime.fromisoformat(value)
            except ValueError:
                # Keep raw value if it is not an ISO timestamp
                pass
    # Keep template compatibility: expose a generic _id key.
    if 'id' in d:
        d['_id'] = d['id']
    elif 'driver_id' in d:
        d['_id'] = d['driver_id']
    return d


def rows_to_dicts(rows):
    return [row_to_dict(r) for r in rows]


def init_db():
    c = get_conn()
    c.executescript(SCHEMA)
    cur = c.cursor()
    # Backward-compatible migration for existing SQLite files.
    cur.execute("PRAGMA table_info(shipments)")
    shipment_columns = {row[1] for row in cur.fetchall()}
    if 'customer_id' not in shipment_columns:
        cur.execute("ALTER TABLE shipments ADD COLUMN customer_id INTEGER")
    if 'payment_status' not in shipment_columns:
        cur.execute("ALTER TABLE shipments ADD COLUMN payment_status TEXT")
    if 'payment_amount' not in shipment_columns:
        cur.execute("ALTER TABLE shipments ADD COLUMN payment_amount REAL")
    cur.execute("PRAGMA table_info(users)")
    user_columns = {row[1] for row in cur.fetchall()}
    if 'email' not in user_columns:
        cur.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if 'phone' not in user_columns:
        cur.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    if 'surname' not in user_columns:
        cur.execute("ALTER TABLE users ADD COLUMN surname TEXT")
    if 'email_verified' not in user_columns:
        cur.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0")
    if 'phone_verified' not in user_columns:
        cur.execute("ALTER TABLE users ADD COLUMN phone_verified INTEGER DEFAULT 0")
    if 'is_active' not in user_columns:
        cur.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 0")
    cur.execute("PRAGMA table_info(fuel_requests)")
    fuel_cols = {row[1] for row in cur.fetchall()}
    if 'payment_failure_reason' not in fuel_cols:
        cur.execute("ALTER TABLE fuel_requests ADD COLUMN payment_failure_reason TEXT")
    cur.execute("PRAGMA table_info(location_updates)")
    location_update_cols = {row[1] for row in cur.fetchall()}
    if location_update_cols and 'source' not in location_update_cols:
        cur.execute("ALTER TABLE location_updates ADD COLUMN source TEXT")
    cur.execute("PRAGMA table_info(shipments)")
    shipment_cols = {row[1] for row in cur.fetchall()}
    if 'delivery_otp' not in shipment_cols:
        cur.execute("ALTER TABLE shipments ADD COLUMN delivery_otp TEXT")
    if 'delivery_otp_generated_at' not in shipment_cols:
        cur.execute("ALTER TABLE shipments ADD COLUMN delivery_otp_generated_at TEXT")
    if 'delivered_at' not in shipment_cols:
        cur.execute("ALTER TABLE shipments ADD COLUMN delivered_at TEXT")
    if 'is_frozen' not in shipment_cols:
        cur.execute("ALTER TABLE shipments ADD COLUMN is_frozen INTEGER DEFAULT 0")
    if 'dimensions' not in shipment_cols:
        cur.execute("ALTER TABLE shipments ADD COLUMN dimensions TEXT")
    cur.execute("PRAGMA table_info(accidents)")
    acc_cols = {row[1] for row in cur.fetchall()}
    if 'accident_type' not in acc_cols:
        cur.execute("ALTER TABLE accidents ADD COLUMN accident_type TEXT")
    if 'latitude' not in acc_cols:
        cur.execute("ALTER TABLE accidents ADD COLUMN latitude REAL")
    if 'longitude' not in acc_cols:
        cur.execute("ALTER TABLE accidents ADD COLUMN longitude REAL")
    cur.execute("PRAGMA table_info(drivers)")
    driver_cols = {row[1] for row in cur.fetchall()}
    if 'surname' not in driver_cols:
        cur.execute("ALTER TABLE drivers ADD COLUMN surname TEXT")
    if 'experience' not in driver_cols:
        cur.execute("ALTER TABLE drivers ADD COLUMN experience TEXT")
    if 'paused_until' not in driver_cols:
        cur.execute("ALTER TABLE drivers ADD COLUMN paused_until TEXT")
    cur.execute("PRAGMA table_info(accident_fund_requests)")
    fund_cols = {row[1] for row in cur.fetchall()}
    if 'purpose' not in fund_cols:
        cur.execute("ALTER TABLE accident_fund_requests ADD COLUMN purpose TEXT")
    
    # FR-412: Initialize Dispatch Settings
    cur.execute("INSERT OR IGNORE INTO dispatch_settings (key, value) VALUES ('optimization_goal', 'MINIMIZE_DEADHEAD')")
    cur.execute("INSERT OR IGNORE INTO dispatch_settings (key, value) VALUES ('confidence_threshold', '0.85')")
    cur.execute("INSERT OR IGNORE INTO dispatch_settings (key, value) VALUES ('driver_acceptance_window', '5')")

    # Dispatch Engine Columns
    if 'hos_remaining' not in driver_cols: cur.execute("ALTER TABLE drivers ADD COLUMN hos_remaining REAL DEFAULT 14.0")
    if 'performance_rating' not in driver_cols: cur.execute("ALTER TABLE drivers ADD COLUMN performance_rating REAL DEFAULT 5.0")
    if 'certifications' not in driver_cols: cur.execute("ALTER TABLE drivers ADD COLUMN certifications TEXT DEFAULT ''")
    
    cur.execute("PRAGMA table_info(trucks)")
    truck_cols = {row[1] for row in cur.fetchall()}
    if 'equipment_tags' not in truck_cols: cur.execute("ALTER TABLE trucks ADD COLUMN equipment_tags TEXT DEFAULT ''")
    if 'fuel_efficiency' not in truck_cols: cur.execute("ALTER TABLE trucks ADD COLUMN fuel_efficiency REAL DEFAULT 6.5")

    if 'assignment_deadline' not in shipment_cols: cur.execute("ALTER TABLE shipments ADD COLUMN assignment_deadline TEXT")
    if 'dispatch_metadata' not in shipment_cols: cur.execute("ALTER TABLE shipments ADD COLUMN dispatch_metadata TEXT")
    
    # FR-510: Add ETA to shipments
    if 'eta' not in shipment_cols: cur.execute("ALTER TABLE shipments ADD COLUMN eta TEXT")

    c.commit()


def seed_admin():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = ?", ('admin',))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, email, password, role, name, is_active) VALUES (?, ?, ?, ?, ?, 1)",
            ('admin', 'admin@fleetguard.local', 'admin123', 'admin', 'Fleet Administrator'),
        )
        c.commit()


def seed_customer():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", ('customer',))
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO users (username, email, password, role, name, is_active) VALUES (?, ?, ?, ?, ?, 1)",
            ('customer', 'customer@example.com', 'customer123', 'customer', 'Default Customer'),
        )
    else:
        cur.execute(
            "UPDATE users SET email = ?, password = ?, role = ?, name = ? WHERE username = ?",
            ('customer@example.com', 'customer123', 'customer', 'Default Customer', 'customer'),
        )
    c.commit()


init_db()
seed_admin()
seed_customer()

# Razorpay config (use .env — never commit real keys to source control)
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_yourkeyhere')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'yoursecrethere')


# SMTP Configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', SMTP_USERNAME)

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')


def send_email_otp(to_email, otp):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"Skipping email to {to_email}: SMTP not configured. OTP: {otp}")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email
        msg['Subject'] = "FleetGuard Registration OTP"
        
        body = f"Your FleetGuard registration OTP is: {otp}\nIt will expire in 10 minutes."
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email to {to_email}: {e}")
        return False


def send_sms_otp(to_phone, otp):
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
        print(f"Skipping SMS to {to_phone}: Twilio not configured. OTP: {otp}")
        return False
    
    # Simple normalization for Twilio (ensure starts with +)
    clean_phone = to_phone.strip().replace(" ", "").replace("-", "")
    if not clean_phone.startswith('+'):
        # Default to +91 if no country code provided (common for this app)
        clean_phone = '+91' + clean_phone if len(clean_phone) == 10 else '+' + clean_phone
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your FleetGuard OTP is: {otp}. Valid for 10 mins.",
            from_=TWILIO_PHONE_NUMBER,
            to=clean_phone
        )
        return True
    except Exception as e:
        print(f"Error sending SMS to {clean_phone}: {e}")
        return False


def razorpay_credentials_configured():
    kid = (RAZORPAY_KEY_ID or '').strip()
    sec = (RAZORPAY_KEY_SECRET or '').strip()
    if not kid or not sec:
        return False
    if 'yourkey' in kid.lower() or 'yoursecret' in sec.lower():
        return False
    return True


def log_fuel_payment_event(cur, fuel_request_id, event, order_id=None, payment_id=None, amount_paise=None, detail=None):
    cur.execute(
        """INSERT INTO fuel_payment_events
           (fuel_request_id, event, razorpay_order_id, razorpay_payment_id, amount_paise, detail, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            int(fuel_request_id),
            event,
            order_id,
            payment_id,
            amount_paise,
            detail if detail is None or isinstance(detail, str) else json.dumps(detail),
            datetime.now().isoformat(),
        ),
    )


def notify_driver_fuel_paid(c, cur, fuel_req, payment_id):
    driver_id = fuel_req.get('driver_id')
    if not driver_id:
        return
    amt = fuel_req.get('amount')
    truck = fuel_req.get('truck_number') or ''
    msg = (
        f"Fuel payment received: ₹{amt} for truck {truck}. "
        f"Transaction ID: {payment_id}. Your request is marked Paid."
    )
    cur.execute(
        """INSERT INTO driver_notifications (driver_id, message, category, fuel_request_id, created_at)
           VALUES (?, ?, 'fuel_payment', ?, ?)""",
        (int(driver_id), msg, int(fuel_req['id']), datetime.now().isoformat()),
    )


def create_notification(cur, message, category='info', user_id=None, role_target=None, link=None):
    cur.execute(
        """INSERT INTO app_notifications (user_id, role_target, message, category, link, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, role_target, message, category, link, datetime.now().isoformat()),
    )


def generate_otp():
    return f"{random.randint(100000, 999999)}"


def create_user_verification(cur, user_id):
    email_otp = generate_otp()
    phone_otp = generate_otp()
    expires_at = (datetime.now() + timedelta(minutes=10)).isoformat()
    cur.execute("DELETE FROM user_verifications WHERE user_id = ?", (int(user_id),))
    cur.execute(
        """INSERT INTO user_verifications (user_id, email_otp, phone_otp, expires_at)
           VALUES (?, ?, ?, ?)""",
        (int(user_id), email_otp, phone_otp, expires_at),
    )
    return email_otp, phone_otp


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def driver_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'driver':
            flash('Driver access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def customer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'customer':
            flash('Customer access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_header_notifications():
    if 'user_id' not in session:
        return {'header_notifications': [], 'header_notification_unread': 0}
    c = get_conn()
    cur = c.cursor()
    cur.execute(
        """SELECT * FROM app_notifications
           WHERE (user_id = ? OR (user_id IS NULL AND role_target = ?))
           ORDER BY (read_at IS NULL) DESC, created_at DESC
           LIMIT 8""",
        (int(session['user_id']), session.get('role', '')),
    )
    items = rows_to_dicts(cur.fetchall())
    cur.execute(
        """SELECT COUNT(*) FROM app_notifications
           WHERE (user_id = ? OR (user_id IS NULL AND role_target = ?))
             AND read_at IS NULL""",
        (int(session['user_id']), session.get('role', '')),
    )
    unread = cur.fetchone()[0]
    return {'header_notifications': items, 'header_notification_unread': unread}


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        c = get_conn()
        cur = c.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        )
        row = cur.fetchone()
        user = row_to_dict(row)
        if user:
            if not int(user.get('is_active') or 0):
                # Check if it's a verification issue
                cur.execute("SELECT id, verified_at FROM user_verifications WHERE user_id = ? ORDER BY id DESC LIMIT 1", (int(user['id']),))
                verification = row_to_dict(cur.fetchone())
                if verification and not verification.get('verified_at'):
                    flash('Account pending email/phone verification. Complete verification first.', 'warning')
                    return redirect(url_for('verify_registration', user_id=int(user['id'])))
                else:
                    flash('Account is inactive. Please contact administrator.', 'danger')
                    return redirect(url_for('login'))
            
            session.permanent = True
            session['user_id'] = str(user['id'])
            session['username'] = user['username']
            session['role'] = user['role']
            session['name'] = user.get('name') or username
            flash(f"Welcome back, {session['name']}!", 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        name = request.form.get('name', '').strip()
        surname = request.form.get('surname', '').strip()
        role = request.form.get('role', 'customer').strip()
        license_number = request.form.get('license_number', '').strip()
        experience = request.form.get('experience', '').strip()
        
        if not username or not email or not password or not name or not surname or not phone:
            flash('All core fields are required.', 'danger')
            return render_template('register.html')
            
        if role == 'driver' and (not license_number or not experience):
            flash('License Number and Experience are required for drivers.', 'danger')
            return render_template('register.html')

        c = get_conn()
        cur = c.cursor()
        cur.execute("SELECT 1 FROM users WHERE username = ? OR email = ? OR phone = ?", (username, email, phone))
        if cur.fetchone():
            flash('Username, email, or phone already exists. Please use unique details.', 'danger')
            return render_template('register.html')
            
        cur.execute(
            """INSERT INTO users (username, email, surname, phone, password, role, name, email_verified, phone_verified, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0)""",
            (username, email, surname, phone, password, role, name),
        )
        user_id = cur.lastrowid
        
        if role == 'driver':
            cur.execute(
                """INSERT INTO drivers (user_id, driver_name, surname, phone, license_number, experience, username, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, name, surname, phone, license_number, experience, username, datetime.now().isoformat()),
            )

        email_otp, phone_otp = create_user_verification(cur, user_id)
        create_notification(
            cur,
            f"New {role} registration pending verification: {name} ({username}).",
            category='warning',
            role_target='admin',
        )
        email_sent = send_email_otp(email, email_otp)
        sms_sent = send_sms_otp(phone, phone_otp)
        
        c.commit()
        
        flash_msg = 'Account created. '
        if email_sent and sms_sent:
            flash_msg += 'OTPs have been sent to your email and phone.'
        elif email_sent:
            flash_msg += 'OTP sent to email. SMS failed (check logs).'
        elif sms_sent:
            flash_msg += 'OTP sent to phone. Email failed (check logs).'
        else:
            flash_msg += f'Demo Mode: Verify with Email OTP {email_otp} and Phone OTP {phone_otp}.'
            
        flash(flash_msg, 'info')
        return redirect(url_for('verify_registration', user_id=user_id))
    return render_template('register.html')


@app.route('/verify-registration/<int:user_id>', methods=['GET', 'POST'])
def verify_registration(user_id):
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT id, role, name FROM users WHERE id = ?", (user_id,))
    user = row_to_dict(cur.fetchone())
    if not user:
        flash('User not found for verification.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        email_otp = request.form.get('email_otp', '').strip()
        phone_otp = request.form.get('phone_otp', '').strip()
        cur.execute(
            """SELECT * FROM user_verifications
               WHERE user_id = ? AND verified_at IS NULL
               ORDER BY id DESC LIMIT 1""",
            (user_id,),
        )
        vr = row_to_dict(cur.fetchone())
        if not vr:
            flash('No active verification found.', 'danger')
            return redirect(url_for('verify_registration', user_id=user_id))
        
        expires_at = vr.get('expires_at')
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except (ValueError, TypeError):
                pass

        if isinstance(expires_at, datetime) and expires_at < datetime.now():
            flash('Verification OTP has expired. Please contact admin to resend.', 'warning')
            return redirect(url_for('verify_registration', user_id=user_id))
        
        if email_otp != (vr.get('email_otp') or '') or phone_otp != (vr.get('phone_otp') or ''):
            flash('Invalid OTP. Please try again.', 'danger')
            return redirect(url_for('verify_registration', user_id=user_id))
        now = datetime.now().isoformat()
        cur.execute(
            "UPDATE users SET email_verified = 1, phone_verified = 1, is_active = 1 WHERE id = ?",
            (user_id,),
        )
        cur.execute("UPDATE user_verifications SET verified_at = ? WHERE id = ?", (now, vr['id']))
        create_notification(
            cur,
            f"Verification complete for {user.get('name') or 'user'} ({user.get('role')}).",
            category='success',
            role_target='admin',
        )
        c.commit()
        flash('Verification successful. You can now login.', 'success')
        return redirect(url_for('login'))
    return render_template('verify_registration.html', user=user)


@app.route('/resend-otp/<int:user_id>')
def resend_otp(user_id):
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT id, email, phone FROM users WHERE id = ?", (user_id,))
    user = row_to_dict(cur.fetchone())
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))
    
    email_otp, phone_otp = create_user_verification(cur, user_id)
    email_sent = send_email_otp(user['email'], email_otp)
    sms_sent = send_sms_otp(user['phone'], phone_otp)
    c.commit()
    
    if email_sent and sms_sent:
        flash('New OTPs sent to your email and phone.', 'success')
    else:
        flash('Failed to resend some OTPs. Please try again.', 'warning')
    return redirect(url_for('verify_registration', user_id=user_id))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        username = request.form.get('username', '').strip()
        new_password = request.form['new_password'].strip()
        c = get_conn()
        cur = c.cursor()
        if username:
            cur.execute("SELECT * FROM users WHERE email = ? AND username = ?", (email, username))
        else:
            cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        if not user:
            flash('No account found with the provided details.', 'danger')
            return render_template('forgot_password.html')
        cur.execute("UPDATE users SET password = ? WHERE id = ?", (new_password, user['id']))
        c.commit()
        flash('Password reset successful. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    c = get_conn()
    cur = c.cursor()
    if session['role'] == 'admin':
        stats = {}
        for key, sql in [
            ('total_trucks', "SELECT COUNT(*) FROM trucks"),
            ('available_trucks', "SELECT COUNT(*) FROM trucks WHERE status = 'Available'"),
            ('on_route_trucks', "SELECT COUNT(*) FROM trucks WHERE status = 'On Route'"),
            ('maintenance_trucks', "SELECT COUNT(*) FROM trucks WHERE status = 'Maintenance'"),
            ('total_drivers', "SELECT COUNT(*) FROM drivers"),
            ('active_shipments', "SELECT COUNT(*) FROM shipments WHERE status = 'In Transit'"),
            ('pending_shipments', "SELECT COUNT(*) FROM shipments WHERE status = 'Pending'"),
            ('delivered_shipments', "SELECT COUNT(*) FROM shipments WHERE status = 'Delivered'"),
            ('pending_fuel', "SELECT COUNT(*) FROM fuel_requests WHERE status = 'Pending'"),
            ('recent_accidents', "SELECT COUNT(*) FROM accidents WHERE status = 'Reported'"),
            ('open_breakdowns', "SELECT COUNT(*) FROM breakdowns WHERE status = 'Open'"),
            ('pending_calls', "SELECT COUNT(*) FROM call_requests WHERE status = 'Pending'"),
            ('pending_accident_funds', "SELECT COUNT(*) FROM accident_fund_requests WHERE status = 'Pending'"),
            ('frozen_shipments', "SELECT COUNT(*) FROM shipments WHERE is_frozen = 1"),
        ]:
            cur.execute(sql)
            stats[key] = cur.fetchone()[0]

        cur.execute(
            "SELECT * FROM fuel_requests WHERE status = 'Pending' ORDER BY created_at DESC LIMIT 5"
        )
        recent_fuel = rows_to_dicts(cur.fetchall())
        cur.execute(
            "SELECT * FROM accident_fund_requests WHERE status = 'Pending' ORDER BY created_at DESC LIMIT 5"
        )
        pending_funds = rows_to_dicts(cur.fetchall())
        cur.execute(
            "SELECT * FROM accidents WHERE status = 'Reported' ORDER BY created_at DESC LIMIT 5"
        )
        recent_accidents = rows_to_dicts(cur.fetchall())
        cur.execute(
            "SELECT * FROM breakdowns WHERE status = 'Open' ORDER BY created_at DESC LIMIT 5"
        )
        recent_breakdowns = rows_to_dicts(cur.fetchall())
        cur.execute(
            "SELECT * FROM call_requests WHERE status = 'Pending' ORDER BY created_at DESC LIMIT 5"
        )
        recent_calls = rows_to_dicts(cur.fetchall())
        
        cur.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'")
        stats['total_customers'] = cur.fetchone()[0]

        # FR-414: Shipments requiring manual assignment
        cur.execute("SELECT * FROM shipments WHERE status = 'Requires Manual Assignment' ORDER BY created_at DESC")
        manual_assignment_required = rows_to_dicts(cur.fetchall())

        # FR-907: Predicted Delay Alert Feed (Mock logic for demo)
        # We flag shipments that are "In Transit" but haven't updated in 30 mins as "High Risk"
        thirty_mins_ago = (datetime.now() - timedelta(minutes=30)).isoformat()
        cur.execute(
            """SELECT s.shipment_id, d.driver_name, s.updated_at 
               FROM shipments s 
               JOIN drivers d ON s.driver_id = d.id 
               WHERE s.status = 'In Transit' AND s.updated_at < ?""",
            (thirty_mins_ago,)
        )
        high_risk_delays = rows_to_dicts(cur.fetchall())
        for delay in high_risk_delays:
            delay['estimated_delay'] = "45 mins" # Mock delay time

        # FR-908: Cost Per Mile (CPM) Analytics
        # Formula: (Fuel + Maintenance + Payroll) / Total Miles
        cur.execute("SELECT SUM(amount) FROM fuel_requests WHERE payment_status = 'Paid'")
        fuel_sum = cur.fetchone()[0] or 0
        cur.execute("SELECT SUM(amount) FROM maintenance_costs")
        maint_sum = cur.fetchone()[0] or 0
        cur.execute("SELECT SUM(amount) FROM driver_payroll")
        payroll_sum = cur.fetchone()[0] or 0
        
        # Estimate miles from location updates (very rough)
        cur.execute("SELECT COUNT(*) FROM location_updates")
        miles_est = (cur.fetchone()[0] or 1) * 0.5 # 0.5 miles per update for demo
        
        cpm = (fuel_sum + maint_sum + payroll_sum) / max(miles_est, 1)
        stats['cpm'] = round(cpm, 2)
        stats['cpm_change'] = "+2.4%" # Mock change

        # FR-904: Active shipments with location update frequency status
        cur.execute(
            """SELECT s.shipment_id, s.status, l.updated_at as last_loc_update 
               FROM shipments s 
               LEFT JOIN locations l ON s.driver_id = l.driver_id 
               WHERE s.status = 'In Transit'"""
        )
        active_shipments_loc = rows_to_dicts(cur.fetchall())

        # FR-902: Fetch active shipment locations for map
        cur.execute(
            """SELECT l.*, s.shipment_id FROM locations l 
               JOIN shipments s ON s.driver_id = l.driver_id 
               WHERE s.status = 'In Transit'"""
        )
        active_locations = rows_to_dicts(cur.fetchall())
        for loc in active_locations:
            cur.execute(
                """SELECT latitude, longitude FROM location_updates 
                   WHERE driver_id = ? AND latitude IS NOT NULL AND longitude IS NOT NULL 
                   ORDER BY updated_at DESC LIMIT 1""",
                (loc['driver_id'],)
            )
            coords = cur.fetchone()
            if coords:
                loc['latitude'] = coords[0]
                loc['longitude'] = coords[1]

        # FR-905: Alerts for paused location sharing
        cur.execute("SELECT * FROM drivers WHERE paused_until IS NOT NULL")
        paused_drivers = rows_to_dicts(cur.fetchall())
        
        # FR-506: Alert if no update for 60 minutes
        sixty_mins_ago = (datetime.now() - timedelta(minutes=60)).isoformat()
        cur.execute(
            """SELECT d.driver_name, d.assigned_truck, l.updated_at 
               FROM drivers d 
               JOIN locations l ON d.id = l.driver_id 
               WHERE l.updated_at < ? AND d.assigned_truck IS NOT NULL""",
            (sixty_mins_ago,)
        )
        missing_updates = rows_to_dicts(cur.fetchall())

        return render_template(
            'admin_dashboard.html',
            stats=stats,
            recent_fuel=recent_fuel,
            pending_funds=pending_funds,
            recent_accidents=recent_accidents,
            recent_breakdowns=recent_breakdowns,
            recent_calls=recent_calls,
            active_locations=active_locations,
            paused_drivers=paused_drivers,
            missing_updates=missing_updates,
            high_risk_delays=high_risk_delays,
            active_shipments_loc=active_shipments_loc,
            manual_assignment_required=manual_assignment_required
        )
    elif session['role'] == 'driver':
        cur.execute("SELECT * FROM drivers WHERE user_id = ?", (int(session['user_id']),))
        driver = row_to_dict(cur.fetchone())
        my_shipments = []
        my_fuel_requests = []
        driver_notifications = []
        transit_shipment = None
        if driver:
            cur.execute("SELECT * FROM shipments WHERE driver_id = ? AND status = 'In Transit' LIMIT 1", (driver['id'],))
            transit_shipment = row_to_dict(cur.fetchone())
            
            cur.execute("SELECT * FROM shipments WHERE driver_id = ? ORDER BY created_at DESC LIMIT 5", (driver['id'],))
            my_shipments = rows_to_dicts(cur.fetchall())
            cur.execute("SELECT * FROM fuel_requests WHERE driver_id = ? ORDER BY created_at DESC LIMIT 3", (driver['id'],))
            my_fuel_requests = rows_to_dicts(cur.fetchall())
            cur.execute(
                """SELECT * FROM driver_notifications WHERE driver_id = ?
                   ORDER BY (read_at IS NULL) DESC, created_at DESC LIMIT 8""",
                (driver['id'],),
            )
            driver_notifications = rows_to_dicts(cur.fetchall())
            
        return render_template(
            'driver_dashboard.html',
            driver=driver,
            my_shipments=my_shipments,
            my_fuel_requests=my_fuel_requests,
            driver_notifications=driver_notifications,
            transit_shipment=transit_shipment,
            now_str=datetime.now().isoformat()
        )
    else:
        cur.execute(
            "SELECT * FROM shipments WHERE customer_id = ? ORDER BY created_at DESC LIMIT 8",
            (int(session['user_id']),),
        )
        my_shipments = rows_to_dicts(cur.fetchall())
        for s in my_shipments:
            if s.get('driver_id'):
                cur.execute(
                    "SELECT current_location, updated_at FROM locations WHERE driver_id = ?",
                    (s['driver_id'],),
                )
                loc = row_to_dict(cur.fetchone())
                s['live_location'] = loc.get('current_location') if loc else ''
                s['live_updated_at'] = loc.get('updated_at') if loc else None
                cur.execute(
                    """SELECT latitude, longitude FROM location_updates
                       WHERE driver_id = ? AND latitude IS NOT NULL AND longitude IS NOT NULL
                       ORDER BY updated_at DESC LIMIT 1""",
                    (s['driver_id'],),
                )
                coords = row_to_dict(cur.fetchone())
                s['live_latitude'] = coords.get('latitude') if coords else None
                s['live_longitude'] = coords.get('longitude') if coords else None
            else:
                s['live_location'] = ''
                s['live_updated_at'] = None
                s['live_latitude'] = None
                s['live_longitude'] = None
        cur.execute(
            "SELECT COUNT(*) FROM shipments WHERE customer_id = ?",
            (int(session['user_id']),),
        )
        total_shipments = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM shipments WHERE customer_id = ? AND status = 'In Transit'",
            (int(session['user_id']),),
        )
        in_transit = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM shipments WHERE customer_id = ? AND payment_status = 'Paid'",
            (int(session['user_id']),),
        )
        paid_shipments = cur.fetchone()[0]
        return render_template(
            'customer_dashboard.html',
            my_shipments=my_shipments,
            total_shipments=total_shipments,
            in_transit=in_transit,
            paid_shipments=paid_shipments,
        )


# ─── TRUCKS ───────────────────────────────────────────────────────────────────
@app.route('/trucks')
@login_required
@admin_required
def trucks():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM trucks ORDER BY created_at DESC")
    all_trucks = rows_to_dicts(cur.fetchall())
    return render_template('trucks.html', trucks=all_trucks)


@app.route('/trucks/delete/<truck_id>', methods=['POST'])
@login_required
@admin_required
def delete_truck(truck_id):
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT truck_number FROM trucks WHERE id = ?", (int(truck_id),))
    truck = cur.fetchone()
    if not truck:
        flash('Truck not found.', 'danger')
        return redirect(url_for('trucks'))
    cur.execute("SELECT COUNT(*) FROM shipments WHERE assigned_truck = ? AND status != 'Delivered'", (truck['truck_number'],))
    active_shipments = cur.fetchone()[0]
    if active_shipments > 0:
        flash('Cannot delete truck with active shipments.', 'danger')
        return redirect(url_for('trucks'))
    cur.execute("DELETE FROM trucks WHERE id = ?", (int(truck_id),))
    c.commit()
    flash('Truck deleted successfully.', 'success')
    return redirect(url_for('trucks'))


@app.route('/trucks/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_truck():
    if request.method == 'POST':
        truck_number = request.form['truck_number'].strip().upper()
        c = get_conn()
        cur = c.cursor()
        cur.execute("SELECT 1 FROM trucks WHERE truck_number = ?", (truck_number,))
        if cur.fetchone():
            flash('Truck number already exists!', 'danger')
        else:
            cur.execute(
                """INSERT INTO trucks (truck_number, truck_type, capacity, status, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    truck_number,
                    request.form['truck_type'],
                    request.form['capacity'],
                    request.form['status'],
                    datetime.now().isoformat(),
                ),
            )
            c.commit()
            flash('Truck added successfully!', 'success')
            return redirect(url_for('trucks'))
    return render_template('truck_form.html', truck=None, action='Add')


@app.route('/trucks/edit/<truck_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_truck(truck_id):
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM trucks WHERE id = ?", (int(truck_id),))
    truck = row_to_dict(cur.fetchone())
    if not truck:
        flash('Truck not found.', 'danger')
        return redirect(url_for('trucks'))
    if request.method == 'POST':
        cur.execute(
            """UPDATE trucks SET truck_number = ?, truck_type = ?, capacity = ?, status = ?, updated_at = ?
               WHERE id = ?""",
            (
                request.form['truck_number'].strip().upper(),
                request.form['truck_type'],
                request.form['capacity'],
                request.form['status'],
                datetime.now().isoformat(),
                int(truck_id),
            ),
        )
        c.commit()
        flash('Truck updated!', 'success')
        return redirect(url_for('trucks'))
    return render_template('truck_form.html', truck=truck, action='Edit')


@app.route('/trucks/status/<truck_id>', methods=['POST'])
@login_required
@admin_required
def change_truck_status(truck_id):
    c = get_conn()
    c.cursor().execute(
        "UPDATE trucks SET status = ? WHERE id = ?",
        (request.form['status'], int(truck_id)),
    )
    c.commit()
    flash('Status updated!', 'success')
    return redirect(url_for('trucks'))


@app.route('/trucks/profitability')
@login_required
@admin_required
def truck_profitability():
    """FR-1105: Detailed profitability report for each truck asset."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM trucks")
    trucks = rows_to_dicts(cur.fetchall())
    
    reports = []
    for t in trucks:
        # Total Revenue
        revenue_sql = "SELECT SUM(payment_amount) FROM shipments WHERE assigned_truck = ? AND payment_status = 'Paid'"
        params = [t['truck_number']]
        if start_date:
            revenue_sql += " AND created_at >= ?"
            params.append(start_date)
        if end_date:
            revenue_sql += " AND created_at <= ?"
            params.append(end_date)
        cur.execute(revenue_sql, params)
        revenue = cur.fetchone()[0] or 0
        
        # Fuel Costs
        fuel_sql = "SELECT SUM(amount) FROM fuel_requests WHERE truck_number = ? AND payment_status = 'Paid'"
        fparams = [t['truck_number']]
        if start_date:
            fuel_sql += " AND created_at >= ?"
            fparams.append(start_date)
        if end_date:
            fuel_sql += " AND created_at <= ?"
            fparams.append(end_date)
        cur.execute(fuel_sql, fparams)
        fuel_costs = cur.fetchone()[0] or 0
        
        # Maintenance Costs
        maint_sql = "SELECT SUM(amount) FROM maintenance_costs WHERE truck_id = ?"
        mparams = [t['id']]
        if start_date:
            maint_sql += " AND created_at >= ?"
            mparams.append(start_date)
        if end_date:
            maint_sql += " AND created_at <= ?"
            mparams.append(end_date)
        cur.execute(maint_sql, mparams)
        maint_costs = cur.fetchone()[0] or 0
        
        profit = revenue - (fuel_costs + maint_costs)
        
        reports.append({
            'truck_number': t['truck_number'],
            'truck_type': t['truck_type'],
            'revenue': revenue,
            'fuel_costs': fuel_costs,
            'maint_costs': maint_costs,
            'profit': profit
        })
        
    return render_template('truck_profitability.html', reports=reports, start_date=start_date, end_date=end_date)


# ─── DRIVERS ──────────────────────────────────────────────────────────────────
@app.route('/drivers')
@login_required
@admin_required
def drivers():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers ORDER BY created_at DESC")
    all_drivers = rows_to_dicts(cur.fetchall())
    for d in all_drivers:
        cur.execute("SELECT email FROM users WHERE id = ?", (d['user_id'],))
        user_row = cur.fetchone()
        d['email'] = user_row['email'] if user_row else ''
    return render_template('drivers.html', drivers=all_drivers)


@app.route('/drivers/details/<int:driver_id>')
@login_required
@admin_required
def driver_details(driver_id):
    """FR-1001, FR-1003: View driver details and historical records."""
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,))
    driver = row_to_dict(cur.fetchone())
    if not driver:
        flash('Driver not found.', 'danger')
        return redirect(url_for('drivers'))
    
    cur.execute("SELECT is_active, username, email FROM users WHERE id = ?", (driver['user_id'],))
    user_row = cur.fetchone()
    driver['is_active'] = user_row['is_active']
    driver['email'] = user_row['email']
    
    # FR-1003: Historical shipment and emergency records
    cur.execute("SELECT * FROM shipments WHERE driver_id = ? ORDER BY created_at DESC", (driver_id,))
    shipments = rows_to_dicts(cur.fetchall())
    
    cur.execute("SELECT * FROM accidents WHERE driver_id = ? ORDER BY created_at DESC", (driver_id,))
    accidents = rows_to_dicts(cur.fetchall())
    
    cur.execute("SELECT * FROM breakdowns WHERE driver_id = ? ORDER BY created_at DESC", (driver_id,))
    breakdowns = rows_to_dicts(cur.fetchall())
    
    return render_template('driver_details.html', driver=driver, shipments=shipments, accidents=accidents, breakdowns=breakdowns)


@app.route('/users/toggle-status/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """FR-1004: Suspend or activate a driver's (or any user's) account."""
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT is_active FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        flash('User not found.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))
    
    new_status = 0 if row['is_active'] else 1
    cur.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
    c.commit()
    flash('User status updated!', 'success')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/drivers/reset-password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_reset_password(user_id):
    """FR-1002: Reset driver password."""
    new_pass = request.form.get('new_password', '').strip()
    if not new_pass:
        flash('New password cannot be empty.', 'danger')
        return redirect(request.referrer or url_for('drivers'))
    
    c = get_conn()
    cur = c.cursor()
    cur.execute("UPDATE users SET password = ? WHERE id = ?", (new_pass, user_id))
    c.commit()
    flash('Password reset successful.', 'success')
    return redirect(request.referrer or url_for('drivers'))


@app.route('/drivers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_driver():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM trucks WHERE status = 'Available'")
    all_trucks = rows_to_dicts(cur.fetchall())
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        name = request.form.get('driver_name', '').strip()
        surname = request.form.get('surname', '').strip()
        password = request.form.get('password', '').strip()
        license_number = request.form.get('license_number', '').strip()
        experience = request.form.get('experience', '').strip()
        if not username or not email or not phone or not name or not surname or not password or not license_number or not experience:
            flash('All driver registration fields are required.', 'danger')
            return render_template('driver_form.html', driver=None, trucks=all_trucks, action='Add')
        cur.execute("SELECT 1 FROM users WHERE username = ? OR email = ?", (username, email))
        if cur.fetchone():
            flash('Username or email already exists!', 'danger')
            return render_template('driver_form.html', driver=None, trucks=all_trucks, action='Add')
        cur.execute(
            """INSERT INTO users (username, email, surname, phone, password, role, name, email_verified, phone_verified)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)""",
            (
                username,
                email,
                surname,
                phone,
                password,
                'driver',
                name,
            ),
        )
        user_id = cur.lastrowid
        email_otp, phone_otp = create_user_verification(cur, user_id)
        assigned_truck = request.form.get('assigned_truck', '')
        cur.execute(
            """INSERT INTO drivers
               (user_id, driver_name, surname, phone, license_number, experience, assigned_truck, username, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                f"{name} {surname}",
                surname,
                phone,
                license_number,
                experience,
                assigned_truck,
                username,
                datetime.now().isoformat(),
            ),
        )
        if assigned_truck:
            cur.execute(
                "UPDATE trucks SET status = 'On Route' WHERE truck_number = ?",
                (assigned_truck,),
            )
        create_notification(
            cur,
            f"Driver {name} {surname} added. Verification pending (email OTP: {email_otp}, phone OTP: {phone_otp}).",
            category='warning',
            role_target='admin',
        )
        c.commit()
        flash('Driver added. Share OTP with driver and complete verification.', 'success')
        flash(f"Driver verification link: /verify-registration/{user_id}", 'info')
        return redirect(url_for('drivers'))
    return render_template('driver_form.html', driver=None, trucks=all_trucks, action='Add')


@app.route('/drivers/edit/<driver_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_driver(driver_id):
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers WHERE id = ?", (int(driver_id),))
    driver = row_to_dict(cur.fetchone())
    if driver:
        cur.execute("SELECT email FROM users WHERE id = ?", (driver['user_id'],))
        urow = cur.fetchone()
        driver['email'] = urow['email'] if urow else ''
    cur.execute("SELECT * FROM trucks")
    all_trucks = rows_to_dicts(cur.fetchall())
    if not driver:
        flash('Driver not found.', 'danger')
        return redirect(url_for('drivers'))
    if request.method == 'POST':
        driver_name = request.form.get('driver_name', '').strip()
        surname = request.form.get('surname', '').strip()
        phone = request.form.get('phone', '').strip()
        license_number = request.form.get('license_number', '').strip()
        experience = request.form.get('experience', '').strip()
        if not driver_name or not surname or not phone or not license_number or not experience:
            flash('All driver fields are required.', 'danger')
            return render_template('driver_form.html', driver=driver, trucks=all_trucks, action='Edit')
        cur.execute(
            """UPDATE drivers SET driver_name = ?, surname = ?, phone = ?, license_number = ?, experience = ?, assigned_truck = ?, updated_at = ?
               WHERE id = ?""",
            (
                f"{driver_name} {surname}",
                surname,
                phone,
                license_number,
                experience,
                request.form.get('assigned_truck', ''),
                datetime.now().isoformat(),
                int(driver_id),
            ),
        )
        cur.execute(
            "UPDATE users SET name = ?, surname = ?, email = ? WHERE id = ?",
            (driver_name, surname, request.form['email'].strip().lower(), driver['user_id']),
        )
        c.commit()
        flash('Driver updated!', 'success')
        return redirect(url_for('drivers'))
    return render_template('driver_form.html', driver=driver, trucks=all_trucks, action='Edit')


@app.route('/drivers/delete/<driver_id>', methods=['POST'])
@login_required
@admin_required
def delete_driver(driver_id):
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers WHERE id = ?", (int(driver_id),))
    driver = row_to_dict(cur.fetchone())
    if not driver:
        flash('Driver not found.', 'danger')
        return redirect(url_for('drivers'))
    cur.execute("DELETE FROM drivers WHERE id = ?", (int(driver_id),))
    cur.execute("DELETE FROM users WHERE id = ?", (driver['user_id'],))
    c.commit()
    flash('Driver deleted successfully.', 'success')
    return redirect(url_for('drivers'))


# ─── SHIPMENTS ────────────────────────────────────────────────────────────────
@app.route('/shipments')
@login_required
def shipments():
    c = get_conn()
    cur = c.cursor()
    customers = []
    available_drivers = []
    if session['role'] == 'admin':
        cur.execute("SELECT * FROM shipments ORDER BY created_at DESC")
        all_shipments = rows_to_dicts(cur.fetchall())
        cur.execute("SELECT id, name, username FROM users WHERE role = 'customer' ORDER BY name")
        customers = rows_to_dicts(cur.fetchall())
        cur.execute("SELECT id, driver_name, assigned_truck FROM drivers WHERE assigned_truck IS NOT NULL")
        available_drivers = rows_to_dicts(cur.fetchall())
    elif session['role'] == 'driver':
        cur.execute("SELECT * FROM drivers WHERE user_id = ?", (int(session['user_id']),))
        driver = row_to_dict(cur.fetchone())
        did = driver['id'] if driver else -1
        cur.execute(
            """SELECT * FROM shipments 
               WHERE driver_id = ? OR status = 'Pending Assignment' 
               ORDER BY (status = 'Pending Assignment') DESC, created_at DESC""",
            (did,),
        )
        all_shipments = rows_to_dicts(cur.fetchall())
    else:
        cur.execute(
            "SELECT * FROM shipments WHERE customer_id = ? ORDER BY created_at DESC",
            (int(session['user_id']),),
        )
        all_shipments = rows_to_dicts(cur.fetchall())
    for s in all_shipments:
        if s.get('driver_id'):
            cur.execute(
                """SELECT current_location, updated_at FROM locations WHERE driver_id = ?""",
                (s['driver_id'],),
            )
            loc = row_to_dict(cur.fetchone())
            s['live_location'] = loc.get('current_location') if loc else ''
            s['live_updated_at'] = loc.get('updated_at') if loc else None
            cur.execute(
                """SELECT latitude, longitude FROM location_updates
                   WHERE driver_id = ? AND latitude IS NOT NULL AND longitude IS NOT NULL
                   ORDER BY updated_at DESC LIMIT 1""",
                (s['driver_id'],),
            )
            coords = row_to_dict(cur.fetchone())
            s['live_latitude'] = coords.get('latitude') if coords else None
            s['live_longitude'] = coords.get('longitude') if coords else None
        else:
            s['live_location'] = ''
            s['live_updated_at'] = None
            s['live_latitude'] = None
            s['live_longitude'] = None
    return render_template('shipments.html', shipments=all_shipments, customers=customers, available_drivers=available_drivers)


@app.route('/shipments/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_shipment():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM trucks")
    all_trucks = rows_to_dicts(cur.fetchall())
    cur.execute("SELECT * FROM drivers")
    all_drivers = rows_to_dicts(cur.fetchall())
    cur.execute("SELECT id, name, username FROM users WHERE role = 'customer' ORDER BY name")
    all_customers = rows_to_dicts(cur.fetchall())
    if request.method == 'POST':
        shipment_id = 'SHP' + datetime.now().strftime('%Y%m%d%H%M%S')
        assigned_truck = request.form['assigned_truck']
        driver_pk = int(request.form['driver_id'])
        customer_id = request.form.get('customer_id')
        if not customer_id:
            flash('Please assign a customer for this shipment.', 'danger')
            return render_template(
                'shipment_form.html',
                trucks=all_trucks,
                drivers=all_drivers,
                customers=all_customers,
            )
        customer_pk = int(customer_id)
        cur.execute(
            """INSERT INTO shipments (shipment_id, item_type, weight, pickup_location, delivery_location, dimensions,
               assigned_truck, driver_id, customer_id, status, payment_status, payment_amount, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Assigned', 'Unpaid', 0, ?)""",
            (
                shipment_id,
                request.form['item_type'],
                request.form['weight'],
                request.form['pickup_location'],
                request.form['delivery_location'],
                request.form.get('dimensions', ''),
                assigned_truck,
                driver_pk,
                customer_pk,
                datetime.now().isoformat(),
            ),
        )
        # Notify Customer
        create_notification(
            cur,
            f"Your shipment {shipment_id} has been created and assigned.",
            category='success',
            user_id=customer_pk,
            link='/shipments'
        )
        # Notify Driver
        cur.execute("SELECT user_id FROM drivers WHERE id = ?", (driver_pk,))
        driver_user = cur.fetchone()
        if driver_user:
            create_notification(
                cur,
                f"New shipment {shipment_id} assigned to you.",
                category='info',
                user_id=driver_user[0],
                link='/shipments'
            )

        if assigned_truck:
            cur.execute(
                "UPDATE trucks SET status = 'On Route' WHERE truck_number = ?",
                (assigned_truck,),
            )
        c.commit()
        flash(f'Shipment {shipment_id} created!', 'success')
        return redirect(url_for('shipments'))
    return render_template('shipment_form.html', trucks=all_trucks, drivers=all_drivers, customers=all_customers)


@app.route('/shipments/status/<shipment_id>', methods=['POST'])
@login_required
@admin_required
def update_shipment_status(shipment_id):
    new_status = request.form['status']
    if new_status == 'Delivered':
        flash('Use driver OTP delivery completion flow to mark Delivered.', 'warning')
        return redirect(url_for('shipments'))
    c = get_conn()
    cur = c.cursor()
    cur.execute(
        "UPDATE shipments SET status = ?, updated_at = ? WHERE id = ?",
        (new_status, datetime.now().isoformat(), int(shipment_id)),
    )
    
    # FR-415, FR-417: Log manual assignment and capture reason
    if new_status == 'Assigned':
        reason = request.form.get('override_reason', 'Manual Assignment')
        cur.execute("SELECT shipment_id FROM shipments WHERE id = ?", (int(shipment_id),))
        s_text_id = cur.fetchone()[0]
        cur.execute(
            """INSERT INTO dispatch_audit_logs 
               (shipment_id, decision_type, override_reason, admin_id, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (s_text_id, 'Manual', reason, session['user_id'], datetime.now().isoformat())
        )

    if new_status == 'In Transit':
        optimize_shipment_route(cur, int(shipment_id))

    if new_status == 'Delivered':
        cur.execute("SELECT * FROM shipments WHERE id = ?", (int(shipment_id),))
        shipment = row_to_dict(cur.fetchone())
        if shipment and shipment.get('assigned_truck'):
            cur.execute(
                "UPDATE trucks SET status = 'Available' WHERE truck_number = ?",
                (shipment['assigned_truck'],),
            )
    c.commit()
    flash('Shipment status updated!', 'success')
    return redirect(url_for('shipments'))


@app.route('/driver/shipments/self-assign/<shipment_id>', methods=['POST'])
@login_required
@driver_required
def driver_self_assign(shipment_id):
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers WHERE user_id = ?", (int(session['user_id']),))
    driver = row_to_dict(cur.fetchone())
    if not driver:
        flash('Driver profile not found.', 'danger')
        return redirect(url_for('shipments'))
    if not driver.get('assigned_truck'):
        flash('You must have a truck assigned to your profile to self-assign shipments.', 'warning')
        return redirect(url_for('shipments'))
    
    cur.execute("SELECT * FROM shipments WHERE id = ?", (int(shipment_id),))
    shipment = row_to_dict(cur.fetchone())
    if not shipment:
        flash('Shipment not found.', 'danger')
        return redirect(url_for('shipments'))
    if shipment.get('status') != 'Pending Assignment':
        flash('Only shipments pending assignment can be self-assigned.', 'warning')
        return redirect(url_for('shipments'))
    
    now = datetime.now().isoformat()
    cur.execute(
        """UPDATE shipments 
           SET driver_id = ?, assigned_truck = ?, status = 'Assigned', updated_at = ? 
           WHERE id = ?""",
        (driver['id'], driver['assigned_truck'], now, int(shipment_id)),
    )
    # Notify customer
    if shipment.get('customer_id'):
        create_notification(
            cur,
            f"Your shipment {shipment['shipment_id']} has been assigned to driver {driver['driver_name']}.",
            category='info',
            user_id=int(shipment['customer_id']),
            link='/shipments'
        )
    c.commit()
    flash(f"Shipment {shipment['shipment_id']} self-assigned successfully!", 'success')
    return redirect(url_for('shipments'))


@app.route('/driver/shipments/unassign/<shipment_id>', methods=['POST'])
@login_required
@driver_required
def driver_unassign(shipment_id):
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT id FROM drivers WHERE user_id = ?", (int(session['user_id']),))
    driver = cur.fetchone()
    if not driver:
        flash('Driver not found.', 'danger')
        return redirect(url_for('shipments'))
    
    cur.execute("SELECT * FROM shipments WHERE id = ? AND driver_id = ?", (int(shipment_id), driver[0]))
    shipment = row_to_dict(cur.fetchone())
    if not shipment:
        flash('Shipment not found or not assigned to you.', 'danger')
        return redirect(url_for('shipments'))
    
    if shipment.get('status') != 'Assigned':
        flash('Cannot unassign shipment that is already in transit or completed.', 'warning')
        return redirect(url_for('shipments'))
    
    now = datetime.now().isoformat()
    cur.execute(
        """UPDATE shipments 
           SET driver_id = NULL, assigned_truck = '', status = 'Pending Assignment', updated_at = ? 
           WHERE id = ?""",
        (now, int(shipment_id)),
    )
    # Notify Admin
    create_notification(
        cur,
        f"Driver {session['name']} has unassigned themselves from shipment {shipment['shipment_id']}.",
        category='warning',
        role_target='admin',
        link='/shipments'
    )
    c.commit()
    flash(f"You have unassigned yourself from shipment {shipment['shipment_id']}.", 'info')
    return redirect(url_for('shipments'))



@app.route('/customer/shipments/<shipment_id>/generate-delivery-otp', methods=['POST'])
@login_required
@customer_required
def generate_delivery_otp(shipment_id):
    c = get_conn()
    cur = c.cursor()
    cur.execute(
        "SELECT * FROM shipments WHERE id = ? AND customer_id = ?",
        (int(shipment_id), int(session['user_id'])),
    )
    shipment = row_to_dict(cur.fetchone())
    if not shipment:
        flash('Shipment not found.', 'danger')
        return redirect(url_for('shipments'))
    if shipment.get('status') != 'In Transit':
        flash('Delivery OTP can only be generated for in-transit shipments.', 'warning')
        return redirect(url_for('shipments'))
    otp = generate_otp()
    now = datetime.now().isoformat()
    cur.execute(
        "UPDATE shipments SET delivery_otp = ?, delivery_otp_generated_at = ?, updated_at = ? WHERE id = ?",
        (otp, now, now, int(shipment_id)),
    )
    if shipment.get('driver_id'):
        create_notification(
            cur,
            f"Delivery OTP generated for shipment {shipment.get('shipment_id')}.",
            category='info',
            role_target='driver',
            link='/shipments',
        )
    c.commit()
    flash(f"Delivery OTP for {shipment.get('shipment_id')}: {otp}", 'info')
    return redirect(url_for('shipments'))


@app.route('/driver/shipments/<shipment_id>/complete-delivery', methods=['POST'])
@login_required
@driver_required
def driver_complete_delivery(shipment_id):
    otp = request.form.get('delivery_otp', '').strip()
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers WHERE user_id = ?", (int(session['user_id']),))
    driver = row_to_dict(cur.fetchone())
    if not driver:
        flash('Driver profile not found.', 'danger')
        return redirect(url_for('shipments'))
    cur.execute(
        "SELECT * FROM shipments WHERE id = ? AND driver_id = ?",
        (int(shipment_id), int(driver['id'])),
    )
    shipment = row_to_dict(cur.fetchone())
    if not shipment:
        flash('Shipment not found.', 'danger')
        return redirect(url_for('shipments'))
    if shipment.get('status') == 'Delivered':
        flash('Shipment is already delivered.', 'info')
        return redirect(url_for('shipments'))
    if not shipment.get('delivery_otp'):
        flash('Customer has not generated delivery OTP yet.', 'warning')
        return redirect(url_for('shipments'))
    if otp != shipment.get('delivery_otp'):
        flash('Invalid delivery OTP.', 'danger')
        return redirect(url_for('shipments'))
    now = datetime.now().isoformat()
    cur.execute(
        """UPDATE shipments
           SET status = 'Delivered', delivered_at = ?, updated_at = ?, delivery_otp = NULL
           WHERE id = ?""",
        (now, now, int(shipment_id)),
    )
    if shipment.get('assigned_truck'):
        cur.execute(
            "UPDATE trucks SET status = 'Available' WHERE truck_number = ?",
            (shipment['assigned_truck'],),
        )
    if shipment.get('customer_id'):
        create_notification(
            cur,
            f"Shipment {shipment.get('shipment_id')} delivered successfully.",
            category='success',
            user_id=int(shipment['customer_id']),
            link='/shipments',
        )
    c.commit()
    flash('Delivery completed with OTP verification.', 'success')
    return redirect(url_for('shipments'))


@app.route('/customer/shipments/create', methods=['GET', 'POST'])
@login_required
@customer_required
def customer_create_shipment():
    if request.method == 'POST':
        shipment_id = 'SHP' + datetime.now().strftime('%Y%m%d%H%M%S')
        c = get_conn()
        cur = c.cursor()
        cur.execute(
            """INSERT INTO shipments (shipment_id, item_type, weight, pickup_location, delivery_location, dimensions,
               assigned_truck, driver_id, customer_id, status, payment_status, payment_amount, created_at)
               VALUES (?, ?, ?, ?, ?, ?, '', NULL, ?, 'Pending Assignment', 'Unpaid', ?, ?)""",
            (
                shipment_id,
                request.form['item_type'],
                request.form['weight'],
                request.form['pickup_location'],
                request.form['delivery_location'],
                request.form.get('dimensions', ''),
                int(session['user_id']),
                float(request.form['payment_amount']),
                datetime.now().isoformat(),
            ),
        )
        # Notify Admin
        create_notification(
            cur,
            f"New shipment request {shipment_id} from customer {session['name']}.",
            category='warning',
            role_target='admin',
            link='/shipments'
        )
        # Notify Drivers
        create_notification(
            cur,
            f"New shipment {shipment_id} available for assignment.",
            category='info',
            role_target='driver',
            link='/shipments'
        )
        c.commit()
        
        # FR-410: Trigger Dispatch Engine
        trigger_dispatch_engine(shipment_id)
        
        flash(f'Shipment request {shipment_id} created!', 'success')
        return redirect(url_for('shipments'))
    return render_template('customer_shipment_form.html')


@app.route('/admin/shipments/payment/<shipment_id>', methods=['POST'])
@login_required
@admin_required
def update_shipment_payment(shipment_id):
    payment_status = request.form['payment_status']
    c = get_conn()
    c.cursor().execute(
        "UPDATE shipments SET payment_status = ?, updated_at = ? WHERE id = ?",
        (payment_status, datetime.now().isoformat(), int(shipment_id)),
    )
    c.commit()
    flash('Shipment payment status updated.', 'success')
    return redirect(url_for('shipments'))


@app.route('/admin/shipments/customer/<shipment_id>', methods=['POST'])
@login_required
@admin_required
def assign_shipment_customer(shipment_id):
    customer_id = request.form.get('customer_id')
    c = get_conn()
    c.cursor().execute(
        "UPDATE shipments SET customer_id = ?, updated_at = ? WHERE id = ?",
        (int(customer_id) if customer_id else None, datetime.now().isoformat(), int(shipment_id)),
    )
    c.commit()
    flash('Shipment customer updated.', 'success')
    return redirect(url_for('shipments'))


@app.route('/users')
@login_required
@admin_required
def users():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT id, username, email, role, name FROM users ORDER BY id DESC")
    all_users = rows_to_dicts(cur.fetchall())
    return render_template('users.html', users=all_users)


@app.route('/users/delete/<user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if int(user_id) == int(session['user_id']):
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('users'))
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (int(user_id),))
    user = row_to_dict(cur.fetchone())
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('users'))
    if user['role'] == 'admin':
        flash('Admin account cannot be deleted.', 'danger')
        return redirect(url_for('users'))
    if user['role'] == 'driver':
        cur.execute("DELETE FROM drivers WHERE user_id = ?", (int(user_id),))
    cur.execute("UPDATE shipments SET customer_id = NULL WHERE customer_id = ?", (int(user_id),))
    cur.execute("DELETE FROM users WHERE id = ?", (int(user_id),))
    c.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('users'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT id, username, email, role, name FROM users WHERE id = ?", (int(session['user_id']),))
    user = row_to_dict(cur.fetchone())
    driver = None
    if user and user['role'] == 'driver':
        cur.execute("SELECT * FROM drivers WHERE user_id = ?", (user['id'],))
        driver = row_to_dict(cur.fetchone())
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form.get('password', '').strip()
        cur.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, user['id']))
        if cur.fetchone():
            flash('Email already in use by another account.', 'danger')
            return render_template('profile.html', user=user, driver=driver)
        if password:
            cur.execute("UPDATE users SET name = ?, email = ?, password = ? WHERE id = ?", (name, email, password, user['id']))
        else:
            cur.execute("UPDATE users SET name = ?, email = ? WHERE id = ?", (name, email, user['id']))
        if user['role'] == 'driver' and driver:
            cur.execute(
                """UPDATE drivers SET driver_name = ?, phone = ?, license_number = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    name,
                    request.form.get('phone', driver.get('phone', '')),
                    request.form.get('license_number', driver.get('license_number', '')),
                    datetime.now().isoformat(),
                    driver['id'],
                ),
            )
        c.commit()
        session['name'] = name
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=user, driver=driver)


# ─── LOCATION ─────────────────────────────────────────────────────────────────
@app.route('/location', methods=['GET', 'POST'])
@login_required
@driver_required
def location_update():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers WHERE user_id = ?", (int(session['user_id']),))
    driver = row_to_dict(cur.fetchone())
    if request.method == 'POST':
        did = driver['id'] if driver else None
        if did is None:
            flash('Driver profile not found.', 'danger')
            return redirect(url_for('location_update'))
        truck_number = (driver.get('assigned_truck') or '').strip()
        if not truck_number:
            flash('No truck is assigned to your profile. Contact admin before updating location.', 'danger')
            return redirect(url_for('location_update'))
        location_text = request.form.get('current_location', '').strip()
        if not location_text:
            flash('Current location is required.', 'danger')
            return redirect(url_for('location_update'))
        lat_raw = request.form.get('latitude', '').strip()
        lon_raw = request.form.get('longitude', '').strip()
        source = request.form.get('source', 'manual').strip() or 'manual'
        latitude = None
        longitude = None
        try:
            if lat_raw and lon_raw:
                latitude = float(lat_raw)
                longitude = float(lon_raw)
        except ValueError:
            latitude = None
            longitude = None
            source = 'manual'
        now = datetime.now().isoformat()
        cur.execute(
            """INSERT INTO locations (driver_id, driver_name, truck_number, current_location, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(driver_id) DO UPDATE SET
                 driver_name = excluded.driver_name,
                 truck_number = excluded.truck_number,
                 current_location = excluded.current_location,
                 updated_at = excluded.updated_at""",
            (
                did,
                session['name'],
                truck_number,
                location_text,
                now,
            ),
        )
        cur.execute(
            """INSERT INTO location_updates
               (driver_id, driver_name, truck_number, current_location, latitude, longitude, source, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (did, session['name'], truck_number, location_text, latitude, longitude, source, now),
        )
        create_notification(
            cur,
            f"Location update from {session['name']}: {location_text}",
            category='info',
            role_target='admin',
            link='/admin/locations',
        )
        c.commit()
        flash('Location updated!', 'success')
        return redirect(url_for('location_update'))
    latest = None
    latest_coords = None
    recent_updates = []
    if driver:
        cur.execute("SELECT * FROM locations WHERE driver_id = ?", (driver['id'],))
        latest = row_to_dict(cur.fetchone())
        cur.execute(
            """SELECT latitude, longitude, updated_at FROM location_updates
               WHERE driver_id = ? AND latitude IS NOT NULL AND longitude IS NOT NULL
               ORDER BY updated_at DESC LIMIT 1""",
            (driver['id'],),
        )
        latest_coords = row_to_dict(cur.fetchone())
        cur.execute(
            """SELECT * FROM location_updates
               WHERE driver_id = ?
               ORDER BY updated_at DESC
               LIMIT 5""",
            (driver['id'],),
        )
        recent_updates = rows_to_dicts(cur.fetchall())
    return render_template(
        'location_update.html',
        driver=driver,
        latest=latest,
        latest_coords=latest_coords,
        recent_updates=recent_updates,
    )


@app.route('/location/auto', methods=['POST'])
@login_required
@driver_required
def location_auto_update():
    data = request.get_json(silent=True) or {}
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers WHERE user_id = ?", (int(session['user_id']),))
    driver = row_to_dict(cur.fetchone())
    if not driver:
        return jsonify({'ok': False, 'error': 'Driver profile not found'}), 404
    
    # FR-505: Check if paused
    if driver.get('paused_until'):
        try:
            p_until = driver['paused_until']
            if isinstance(p_until, str):
                p_until = datetime.fromisoformat(p_until)
            
            if p_until > datetime.now():
                return jsonify({'ok': False, 'error': 'Location sharing is paused', 'paused_until': driver['paused_until']}), 403
            else:
                # Pause expired, clear it
                cur.execute("UPDATE drivers SET paused_until = NULL WHERE id = ?", (driver['id'],))
        except (ValueError, TypeError):
            pass

    truck_number = (driver.get('assigned_truck') or '').strip()
    if not truck_number:
        return jsonify({'ok': False, 'error': 'No truck assigned'}), 400
    location_text = (data.get('current_location') or '').strip()
    if not location_text:
        return jsonify({'ok': False, 'error': 'current_location required'}), 400
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    now = datetime.now().isoformat()
    cur.execute(
        """INSERT INTO locations (driver_id, driver_name, truck_number, current_location, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(driver_id) DO UPDATE SET
             driver_name = excluded.driver_name,
             truck_number = excluded.truck_number,
             current_location = excluded.current_location,
             updated_at = excluded.updated_at""",
        (driver['id'], session['name'], truck_number, location_text, now),
    )
    cur.execute(
        """INSERT INTO location_updates
           (driver_id, driver_name, truck_number, current_location, latitude, longitude, source, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 'auto_30m', ?)""",
        (driver['id'], session['name'], truck_number, location_text, latitude, longitude, now),
    )
    create_notification(
        cur,
        f"Auto location update from {session['name']}: {location_text}",
        category='info',
        role_target='admin',
        link='/admin/locations',
    )
    c.commit()
    return jsonify({'ok': True, 'updated_at': now})


@app.route('/location/pause', methods=['POST'])
@login_required
@driver_required
def location_pause():
    minutes = min(int(request.form.get('minutes', 60)), 60)
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT id FROM drivers WHERE user_id = ?", (int(session['user_id']),))
    driver = cur.fetchone()
    if not driver:
        flash('Driver not found.', 'danger')
        return redirect(url_for('location_update'))
    
    paused_until = (datetime.now() + timedelta(minutes=minutes)).isoformat()
    cur.execute("UPDATE drivers SET paused_until = ? WHERE id = ?", (paused_until, driver[0]))
    create_notification(
        cur,
        f"Driver {session['name']} has paused location sharing for {minutes} minutes.",
        category='warning',
        role_target='admin',
        link='/admin/locations'
    )
    c.commit()
    flash(f'Location sharing paused for {minutes} minutes.', 'warning')
    return redirect(url_for('location_update'))


@app.route('/location/resume', methods=['POST'])
@login_required
@driver_required
def location_resume():
    c = get_conn()
    cur = c.cursor()
    cur.execute("UPDATE drivers SET paused_until = NULL WHERE user_id = ?", (int(session['user_id']),))
    c.commit()
    flash('Location sharing resumed.', 'success')
    return redirect(url_for('location_update'))


@app.route('/admin/locations')
@login_required
@admin_required
def admin_locations():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM locations ORDER BY updated_at DESC")
    all_locations = rows_to_dicts(cur.fetchall())
    cur.execute("SELECT * FROM location_updates ORDER BY updated_at DESC LIMIT 50")
    recent_updates = rows_to_dicts(cur.fetchall())
    
    # FR-515: Fetch route data for map overlays
    cur.execute("SELECT * FROM shipment_routes")
    route_data = rows_to_dicts(cur.fetchall())
    
    # FR-512: Fetch alerts
    cur.execute("SELECT * FROM route_alerts ORDER BY created_at DESC LIMIT 10")
    route_alerts = rows_to_dicts(cur.fetchall())

    return render_template(
        'admin_locations.html',
        locations=all_locations,
        recent_updates=recent_updates,
        route_data=route_data,
        route_alerts=route_alerts
    )


# ─── FUEL REQUESTS ────────────────────────────────────────────────────────────
@app.route('/fuel-request', methods=['GET', 'POST'])
@login_required
@driver_required
def fuel_request():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers WHERE user_id = ?", (int(session['user_id']),))
    driver = row_to_dict(cur.fetchone())
    if request.method == 'POST':
        did = driver['id'] if driver else None
        cur.execute(
            """INSERT INTO fuel_requests (driver_id, driver_name, truck_number, current_location,
               fuel_required, amount, status, payment_status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'Pending', 'Unpaid', ?)""",
            (
                did,
                session['name'],
                request.form['truck_number'],
                request.form['current_location'],
                request.form['fuel_required'],
                float(request.form['amount']),
                datetime.now().isoformat(),
            ),
        )
        c.commit()
        flash('Fuel request submitted!', 'success')
        return redirect(url_for('fuel_request'))
    my_requests = []
    driver_notifications = []
    if driver:
        cur.execute(
            "SELECT * FROM fuel_requests WHERE driver_id = ? ORDER BY created_at DESC",
            (driver['id'],),
        )
        my_requests = rows_to_dicts(cur.fetchall())
        cur.execute(
            """SELECT * FROM driver_notifications WHERE driver_id = ? AND read_at IS NULL
               ORDER BY created_at DESC LIMIT 5""",
            (driver['id'],),
        )
        driver_notifications = rows_to_dicts(cur.fetchall())
    return render_template(
        'fuel_request.html',
        driver=driver,
        my_requests=my_requests,
        driver_notifications=driver_notifications,
    )


@app.route('/admin/fuel-requests')
@login_required
@admin_required
def admin_fuel_requests():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM fuel_requests ORDER BY created_at DESC")
    all_requests = rows_to_dicts(cur.fetchall())
    for req in all_requests:
        if not req.get('payment_status'):
            req['payment_status'] = 'Unpaid'
    return render_template(
        'admin_fuel_requests.html',
        requests=all_requests,
        razorpay_key=RAZORPAY_KEY_ID,
        razorpay_ready=razorpay_credentials_configured(),
    )


@app.route('/admin/fuel-requests/action/<req_id>', methods=['POST'])
@login_required
@admin_required
def fuel_request_action(req_id):
    action = request.form['action']
    c = get_conn()
    c.cursor().execute(
        "UPDATE fuel_requests SET status = ?, updated_at = ? WHERE id = ?",
        (action, datetime.now().isoformat(), int(req_id)),
    )
    c.commit()
    flash(f'Request {action}!', 'success' if action == 'Approved' else 'warning')
    return redirect(url_for('admin_fuel_requests'))


@app.route('/admin/fuel-requests/pay/<req_id>', methods=['POST'])
@login_required
@admin_required
def pay_fuel_request(req_id):
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM fuel_requests WHERE id = ?", (int(req_id),))
    fuel_req = row_to_dict(cur.fetchone())
    if not fuel_req:
        return jsonify({'error': 'Not found'}), 404
    if fuel_req.get('status') != 'Approved':
        return jsonify({'error': 'Request must be approved before payment.'}), 400
    if fuel_req.get('payment_status') == 'Paid':
        return jsonify({'error': 'Request already paid.'}), 400

    try:
        amount_val = float(fuel_req['amount'])
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid amount on fuel request.'}), 400
    if amount_val <= 0:
        return jsonify({'error': 'Amount must be greater than zero.'}), 400
    amount_paise = int(round(amount_val * 100))

    # FR-701/702: Demo/offline path when Razorpay is not configured (no live gateway).
    if not razorpay_credentials_configured():
        offline_pid = f"offline_{req_id}_{int(datetime.now().timestamp())}"
        now = datetime.now().isoformat()
        cur.execute(
            """UPDATE fuel_requests
               SET payment_status = 'Paid', payment_id = ?, paid_at = ?, updated_at = ?
               WHERE id = ?""",
            (offline_pid, now, now, int(req_id)),
        )
        log_fuel_payment_event(
            cur,
            req_id,
            'payment_succeeded_offline',
            order_id=None,
            payment_id=offline_pid,
            amount_paise=amount_paise,
            detail='offline_demo',
        )
        notify_driver_fuel_paid(c, cur, fuel_req, offline_pid)
        c.commit()
        return jsonify({'success': True, 'mode': 'offline'})

    try:
        import razorpay

        rzp = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order = rzp.order.create(
            {
                'amount': amount_paise,
                'currency': 'INR',
                'receipt': f'fuel_{req_id}',
                'payment_capture': 1,
                'notes': {'fuel_request_id': str(req_id), 'driver': fuel_req.get('driver_name') or ''},
            }
        )
        now = datetime.now().isoformat()
        cur.execute(
            """UPDATE fuel_requests
               SET razorpay_order_id = ?, payment_failure_reason = NULL, updated_at = ?
               WHERE id = ?""",
            (order['id'], now, int(req_id)),
        )
        log_fuel_payment_event(
            cur,
            req_id,
            'order_created',
            order_id=order['id'],
            payment_id=None,
            amount_paise=amount_paise,
            detail=json.dumps({'receipt': order.get('receipt')}),
        )
        c.commit()
        return jsonify({'order_id': order['id'], 'amount': amount_paise, 'key': RAZORPAY_KEY_ID})
    except Exception as e:
        err_msg = str(e)
        try:
            log_fuel_payment_event(
                cur,
                req_id,
                'gateway_error',
                detail=err_msg[:2000],
            )
            cur.execute(
                "UPDATE fuel_requests SET payment_failure_reason = ?, updated_at = ? WHERE id = ?",
                (err_msg[:500], datetime.now().isoformat(), int(req_id)),
            )
            c.commit()
        except Exception:
            c.rollback()
        return jsonify({'error': f'Could not create Razorpay order: {err_msg}'}), 500


@app.route('/admin/fuel-requests/payment-failed', methods=['POST'])
@login_required
@admin_required
def payment_failed():
    """FR-705: Record Razorpay checkout failures and surface them to admin."""
    data = request.get_json(silent=True) or {}
    req_id = data.get('req_id')
    err = data.get('error') or {}
    if not req_id:
        return jsonify({'ok': False, 'error': 'req_id required'}), 400
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM fuel_requests WHERE id = ?", (int(req_id),))
    fuel_req = row_to_dict(cur.fetchone())
    if not fuel_req:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    detail = err if isinstance(err, dict) else {'message': str(err)}
    summary = detail.get('description') or detail.get('reason') or json.dumps(detail)[:400]
    log_fuel_payment_event(
        cur,
        req_id,
        'payment_failed',
        order_id=fuel_req.get('razorpay_order_id'),
        payment_id=None,
        amount_paise=None,
        detail=detail,
    )
    cur.execute(
        "UPDATE fuel_requests SET payment_failure_reason = ?, updated_at = ? WHERE id = ?",
        (summary[:500], datetime.now().isoformat(), int(req_id)),
    )
    c.commit()
    return jsonify({'ok': True})


@app.route('/admin/fuel-requests/payment-success', methods=['POST'])
@login_required
@admin_required
def payment_success():
    """FR-703/704: Verify Razorpay response, then mark Paid and notify driver (FR-707)."""
    req_id = request.form.get('req_id')
    payment_id = (request.form.get('payment_id') or '').strip()
    order_id = (request.form.get('razorpay_order_id') or '').strip()
    signature = (request.form.get('razorpay_signature') or '').strip()
    if not req_id:
        flash('Invalid payment callback (missing request).', 'danger')
        return redirect(url_for('admin_fuel_requests'))

    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM fuel_requests WHERE id = ?", (int(req_id),))
    fuel_req = row_to_dict(cur.fetchone())
    if not fuel_req:
        flash('Fuel request not found.', 'danger')
        return redirect(url_for('admin_fuel_requests'))
    if fuel_req.get('status') != 'Approved':
        flash('Only approved requests can be marked paid.', 'danger')
        return redirect(url_for('admin_fuel_requests'))
    if fuel_req.get('payment_status') == 'Paid':
        flash('This request is already marked as Paid.', 'info')
        return redirect(url_for('admin_fuel_requests'))

    if not razorpay_credentials_configured():
        flash(
            'This callback is only used with Razorpay checkout. '
            'With demo keys, use Pay on the row for instant offline settlement.',
            'warning',
        )
        return redirect(url_for('admin_fuel_requests'))

    now = datetime.now().isoformat()
    amount_paise = int(round(float(fuel_req['amount']) * 100))

    if not payment_id or not order_id or not signature:
        log_fuel_payment_event(
            cur,
            req_id,
            'callback_incomplete',
            order_id=order_id or None,
            payment_id=payment_id or None,
            detail='missing payment_id, order_id, or signature',
        )
        c.commit()
        flash('Payment could not be verified (incomplete response from gateway).', 'danger')
        return redirect(url_for('admin_fuel_requests'))
    stored_order = (fuel_req.get('razorpay_order_id') or '').strip()
    if not stored_order or stored_order != order_id:
        log_fuel_payment_event(
            cur,
            req_id,
            'order_mismatch',
            order_id=order_id,
            payment_id=payment_id,
            detail=f"expected_order={stored_order}",
        )
        c.commit()
        flash('Payment verification failed: order does not match this fuel request.', 'danger')
        return redirect(url_for('admin_fuel_requests'))
    try:
        import razorpay
        from razorpay.errors import SignatureVerificationError

        rzp = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        rzp.utility.verify_payment_signature(
            {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature,
            }
        )
    except SignatureVerificationError:
        log_fuel_payment_event(
            cur,
            req_id,
            'signature_invalid',
            order_id=order_id,
            payment_id=payment_id,
            detail='SignatureVerificationError',
        )
        c.commit()
        flash('Payment signature verification failed. The payment was not recorded.', 'danger')
        return redirect(url_for('admin_fuel_requests'))
    except Exception as e:
        log_fuel_payment_event(
            cur,
            req_id,
            'verification_error',
            order_id=order_id,
            payment_id=payment_id,
            detail=str(e)[:2000],
        )
        c.commit()
        flash(f'Payment verification error: {e}', 'danger')
        return redirect(url_for('admin_fuel_requests'))

    cur.execute(
        """UPDATE fuel_requests
           SET payment_status = 'Paid', payment_id = ?, paid_at = ?, updated_at = ?,
               payment_failure_reason = NULL
           WHERE id = ?""",
        (payment_id or f"unverified_{req_id}", now, now, int(req_id)),
    )
    log_fuel_payment_event(
        cur,
        req_id,
        'payment_succeeded',
        order_id=order_id or fuel_req.get('razorpay_order_id'),
        payment_id=payment_id,
        amount_paise=amount_paise,
        detail=None,
    )
    notify_driver_fuel_paid(c, cur, fuel_req, payment_id or 'N/A')
    c.commit()
    flash('Payment successful. Driver has been notified.', 'success')
    return redirect(url_for('admin_fuel_requests'))


@app.route('/admin/fuel-payment-history')
@login_required
@admin_required
def admin_fuel_payment_history():
    """FR-706: Audit trail of Razorpay-related fuel payment events."""
    c = get_conn()
    cur = c.cursor()
    cur.execute(
        """SELECT e.*, f.driver_name, f.truck_number, f.amount AS request_amount, f.status AS request_status
           FROM fuel_payment_events e
           LEFT JOIN fuel_requests f ON f.id = e.fuel_request_id
           ORDER BY e.id DESC LIMIT 250"""
    )
    events = rows_to_dicts(cur.fetchall())
    return render_template('admin_fuel_payment_history.html', events=events)


@app.route('/driver/notification/<int:nid>/read', methods=['POST'])
@login_required
@driver_required
def driver_notification_read(nid):
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers WHERE user_id = ?", (int(session['user_id']),))
    driver = row_to_dict(cur.fetchone())
    if not driver:
        return redirect(url_for('dashboard'))
    cur.execute(
        "UPDATE driver_notifications SET read_at = ? WHERE id = ? AND driver_id = ?",
        (datetime.now().isoformat(), nid, driver['id']),
    )
    c.commit()
    flash('Notification dismissed.', 'info')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/notifications/read/<int:nid>', methods=['POST'])
@login_required
def mark_header_notification_read(nid):
    c = get_conn()
    cur = c.cursor()
    cur.execute(
        """UPDATE app_notifications
           SET read_at = ?
           WHERE id = ?
             AND (user_id = ? OR (user_id IS NULL AND role_target = ?))""",
        (datetime.now().isoformat(), nid, int(session['user_id']), session.get('role', '')),
    )
    c.commit()
    return redirect(request.referrer or url_for('dashboard'))


# ─── ACCIDENTS ────────────────────────────────────────────────────────────────
@app.route('/accident', methods=['GET', 'POST'])
@login_required
@driver_required
def accident_report():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers WHERE user_id = ?", (int(session['user_id']),))
    driver = row_to_dict(cur.fetchone())
    if request.method == 'POST':
        did = driver['id'] if driver else None
        fund_levels = ['Small', 'Major', 'Critical']
        accident_type = request.form.get('accident_type', 'Small')
        if accident_type not in fund_levels:
            accident_type = 'Small'

        lat_raw = request.form.get('latitude', '').strip()
        lon_raw = request.form.get('longitude', '').strip()
        latitude = None
        longitude = None
        try:
            if lat_raw and lon_raw:
                latitude = float(lat_raw)
                longitude = float(lon_raw)
        except ValueError:
            latitude = None
            longitude = None
        
        # FR-703: Request emergency funds (Amount, Purpose)
        try:
            requested_amount = float(request.form.get('requested_amount', 0))
        except ValueError:
            requested_amount = 0.0
        purpose = request.form.get('purpose', 'Emergency funds for accident')
        now = datetime.now().isoformat()
        cur.execute(
            """INSERT INTO accidents
               (driver_id, driver_name, truck_number, location, description, accident_type, latitude, longitude, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Reported', ?)""",
            (
                did,
                session['name'],
                request.form['truck_number'],
                request.form['location'],
                request.form['description'],
                accident_type,
                latitude,
                longitude,
                now,
            ),
        )
        accident_id = cur.lastrowid
        
        if requested_amount > 0:
            cur.execute(
                """INSERT INTO accident_fund_requests
                   (accident_id, driver_id, driver_name, accident_type, requested_amount, purpose, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?)""",
                (accident_id, did, session['name'], accident_type, requested_amount, purpose, now),
            )
        if latitude is not None and longitude is not None:
            cur.execute(
                """INSERT INTO locations (driver_id, driver_name, truck_number, current_location, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(driver_id) DO UPDATE SET
                     driver_name = excluded.driver_name,
                     truck_number = excluded.truck_number,
                     current_location = excluded.current_location,
                     updated_at = excluded.updated_at""",
                (did, session['name'], request.form['truck_number'], request.form['location'], now),
            )
            cur.execute(
                """INSERT INTO location_updates
                   (driver_id, driver_name, truck_number, current_location, latitude, longitude, source, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'accident', ?)""",
                (did, session['name'], request.form['truck_number'], request.form['location'], latitude, longitude, now),
            )
        create_notification(
            cur,
            f"Accident reported by {session['name']} ({accident_type}). Fund request ₹{requested_amount:.0f} created.",
            category='danger',
            role_target='admin',
            link='/admin/accidents',
        )
        
        # FR-702: Freeze shipment for Major/Critical
        if accident_type in ('Major', 'Critical'):
            # Find active shipment for this driver
            cur.execute("SELECT id, shipment_id, customer_id FROM shipments WHERE driver_id = ? AND status IN ('Assigned', 'In Transit') LIMIT 1", (did,))
            active_shipment = row_to_dict(cur.fetchone())
            if active_shipment:
                cur.execute("UPDATE shipments SET is_frozen = 1, updated_at = ? WHERE id = ?", (now, active_shipment['id']))
                # FR-706: Notify customer
                if active_shipment.get('customer_id'):
                    create_notification(
                        cur,
                        f"Shipment {active_shipment['shipment_id']} is delayed due to a {accident_type} accident involving the driver. We are working on it.",
                        category='warning',
                        user_id=active_shipment['customer_id'],
                        link='/shipments'
                    )
        
        c.commit()
        flash('Accident reported. Admin notified and fund request created.', 'success')
        return redirect(url_for('accident_report'))
    my_reports = []
    if driver:
        cur.execute(
            "SELECT * FROM accidents WHERE driver_id = ? ORDER BY created_at DESC",
            (driver['id'],),
        )
        my_reports = rows_to_dicts(cur.fetchall())
    return render_template('accident_report.html', driver=driver, my_reports=my_reports)


@app.route('/admin/accidents')
@login_required
@admin_required
def admin_accidents():
    c = get_conn()
    cur = c.cursor()
    cur.execute(
        """SELECT a.*,
                  f.requested_amount AS fund_amount,
                  f.status AS fund_status
           FROM accidents a
           LEFT JOIN accident_fund_requests f ON f.accident_id = a.id
           ORDER BY a.created_at DESC"""
    )
    all_accidents = rows_to_dicts(cur.fetchall())
    return render_template('admin_accidents.html', accidents=all_accidents)


@app.route('/admin/accidents/resolve/<acc_id>', methods=['POST'])
@login_required
@admin_required
def resolve_accident(acc_id):
    c = get_conn()
    c.cursor().execute(
        "UPDATE accidents SET status = 'Resolved', resolved_at = ? WHERE id = ?",
        (datetime.now().isoformat(), int(acc_id)),
    )
    c.commit()
    flash('Accident resolved.', 'success')
    return redirect(url_for('admin_accidents'))


@app.route('/admin/accidents/fund-action/<int:fund_id>', methods=['POST'])
@login_required
@admin_required
def fund_request_action(fund_id):
    action = request.form.get('action') # Approved / Rejected
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM accident_fund_requests WHERE id = ?", (fund_id,))
    fund_req = row_to_dict(cur.fetchone())
    if not fund_req:
        flash('Fund request not found.', 'danger')
        return redirect(url_for('admin_accidents'))
        
    now = datetime.now().isoformat()
    cur.execute(
        "UPDATE accident_fund_requests SET status = ?, resolved_at = ? WHERE id = ?",
        (action, now, fund_id)
    )
    
    # Notify driver
    if fund_req.get('driver_id'):
        cur.execute(
            """INSERT INTO driver_notifications (driver_id, message, category, created_at)
               VALUES (?, ?, 'accident_fund', ?)""",
            (int(fund_req['driver_id']), f"Your emergency fund request for ₹{fund_req['requested_amount']} has been {action}.", now)
        )
    
    c.commit()
    flash(f'Fund request {action}!', 'success' if action == 'Approved' else 'warning')
    return redirect(url_for('admin_accidents'))


# ─── BREAKDOWNS ───────────────────────────────────────────────────────────────
@app.route('/breakdown', methods=['GET', 'POST'])
@login_required
@driver_required
def breakdown_report():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers WHERE user_id = ?", (int(session['user_id']),))
    driver = row_to_dict(cur.fetchone())
    if request.method == 'POST':
        did = driver['id'] if driver else None
        cur.execute(
            """INSERT INTO breakdowns (driver_id, driver_name, truck_number, location, problem_description, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'Open', ?)""",
            (
                did,
                session['name'],
                request.form['truck_number'],
                request.form['location'],
                request.form['problem_description'],
                datetime.now().isoformat(),
            ),
        )
        c.commit()
        flash('Breakdown reported!', 'success')
        return redirect(url_for('breakdown_report'))
    my_reports = []
    if driver:
        cur.execute(
            "SELECT * FROM breakdowns WHERE driver_id = ? ORDER BY created_at DESC",
            (driver['id'],),
        )
        my_reports = rows_to_dicts(cur.fetchall())
    return render_template('breakdown_report.html', driver=driver, my_reports=my_reports)


@app.route('/admin/breakdowns')
@login_required
@admin_required
def admin_breakdowns():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM breakdowns ORDER BY created_at DESC")
    all_breakdowns = rows_to_dicts(cur.fetchall())
    return render_template('admin_breakdowns.html', breakdowns=all_breakdowns)


@app.route('/admin/breakdowns/resolve/<bd_id>', methods=['POST'])
@login_required
@admin_required
def resolve_breakdown(bd_id):
    c = get_conn()
    c.cursor().execute(
        "UPDATE breakdowns SET status = 'Resolved', resolved_at = ? WHERE id = ?",
        (datetime.now().isoformat(), int(bd_id)),
    )
    c.commit()
    flash('Breakdown resolved.', 'success')
    return redirect(url_for('admin_breakdowns'))


# ─── CALL REQUESTS ────────────────────────────────────────────────────────────
@app.route('/call-request', methods=['GET', 'POST'])
@login_required
@driver_required
def call_request():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers WHERE user_id = ?", (int(session['user_id']),))
    driver = row_to_dict(cur.fetchone())
    if request.method == 'POST':
        did = driver['id'] if driver else None
        cur.execute(
            """INSERT INTO call_requests (driver_id, driver_name, truck_number, message, status, created_at)
               VALUES (?, ?, ?, ?, 'Pending', ?)""",
            (
                did,
                session['name'],
                request.form.get('truck_number', ''),
                request.form.get('message', 'Urgent: Please call back.'),
                datetime.now().isoformat(),
            ),
        )
        c.commit()
        flash('Call request sent!', 'success')
        return redirect(url_for('call_request'))
    my_requests = []
    if driver:
        cur.execute(
            "SELECT * FROM call_requests WHERE driver_id = ? ORDER BY created_at DESC",
            (driver['id'],),
        )
        my_requests = rows_to_dicts(cur.fetchall())
    return render_template('call_request.html', driver=driver, my_requests=my_requests)


@app.route('/admin/call-requests')
@login_required
@admin_required
def admin_call_requests():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM call_requests ORDER BY created_at DESC")
    all_requests = rows_to_dicts(cur.fetchall())
    return render_template('admin_call_requests.html', requests=all_requests)


@app.route('/admin/call-requests/done/<req_id>', methods=['POST'])
@login_required
@admin_required
def resolve_call(req_id):
    c = get_conn()
    c.cursor().execute(
        "UPDATE call_requests SET status = 'Resolved', resolved_at = ? WHERE id = ?",
        (datetime.now().isoformat(), int(req_id)),
    )
    c.commit()
    flash('Call resolved.', 'success')
    return redirect(url_for('admin_call_requests'))


# ─── CHAT ─────────────────────────────────────────────────────────────────────
@app.route('/chat/<shipment_id>')
@login_required
def chat(shipment_id):
    c = get_conn()
    cur = c.cursor()
    # Verify access: only admin, the assigned driver, or the customer can see this chat
    cur.execute("SELECT * FROM shipments WHERE shipment_id = ?", (shipment_id,))
    shipment = row_to_dict(cur.fetchone())
    if not shipment:
        flash('Shipment not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    can_access = False
    if session['role'] == 'admin':
        can_access = True
    elif session['role'] == 'driver':
        cur.execute("SELECT id FROM drivers WHERE user_id = ?", (int(session['user_id']),))
        driver = cur.fetchone()
        if driver and shipment.get('driver_id') == driver[0]:
            can_access = True
    elif session['role'] == 'customer' and shipment.get('customer_id') == int(session['user_id']):
        can_access = True
        
    if not can_access:
        flash('Access denied to this chat.', 'danger')
        return redirect(url_for('dashboard'))
        
    cur.execute("SELECT * FROM chat_messages WHERE shipment_id = ? ORDER BY created_at ASC", (shipment_id,))
    messages = rows_to_dicts(cur.fetchall())
    return render_template('chat.html', shipment=shipment, messages=messages)


@app.route('/chat/send', methods=['POST'])
@login_required
def chat_send():
    shipment_id = request.form['shipment_id']
    message = request.form['message'].strip()
    if not message:
        return redirect(url_for('chat', shipment_id=shipment_id))
    
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM shipments WHERE shipment_id = ?", (shipment_id,))
    shipment = row_to_dict(cur.fetchone())
    if not shipment:
        flash('Shipment not found.', 'danger')
        return redirect(url_for('dashboard'))

    # Stakeholder check
    can_access = False
    if session['role'] == 'admin':
        can_access = True
    elif session['role'] == 'driver':
        if shipment.get('driver_id') == int(session['user_id']):
            can_access = True
    elif session['role'] == 'customer':
        if shipment.get('customer_id') == int(session['user_id']):
            can_access = True
            
    if not can_access:
        flash('Unauthorized to send message.', 'danger')
        return redirect(url_for('dashboard'))

    cur.execute(
        """INSERT INTO chat_messages (shipment_id, sender_id, sender_role, message, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (shipment_id, int(session['user_id']), session['role'], message, datetime.now().isoformat())
    )
    c.commit()
    return redirect(url_for('chat', shipment_id=shipment_id))


@app.route('/driver/phone/<shipment_id>')
@login_required
def get_driver_phone(shipment_id):
    """FR-804: Display driver phone only when 'In Transit'."""
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM shipments WHERE shipment_id = ?", (shipment_id,))
    shipment = row_to_dict(cur.fetchone())
    if not shipment:
        return jsonify({'error': 'Shipment not found'}), 404
    
    if shipment.get('status') != 'In Transit' and session['role'] != 'admin':
        return jsonify({'error': 'Phone number visible only during transit'}), 403

    # Authorization check
    if session['role'] == 'customer' and shipment.get('customer_id') != int(session['user_id']):
        return jsonify({'error': 'Unauthorized to view this driver phone'}), 403
    
    if not shipment.get('driver_id'):
        return jsonify({'error': 'No driver assigned'}), 404
        
    cur.execute("SELECT phone FROM drivers WHERE id = ?", (shipment['driver_id'],))
    driver = cur.fetchone()
    if not driver:
        return jsonify({'error': 'Driver not found'}), 404
        
    return jsonify({'phone': driver[0]})


# ─── WEBRTC SIGNALING ────────────────────────────────────────────────────────
# We use a simple signaling approach: one party posts a signal, the other gets it.
# In a real app, you'd use WebSockets (Socket.IO). For this demo, we'll poll or use a simple GET/POST.
signals = {} # Dictionary to hold signals for shipment_ids

@app.route('/chat/signal/<shipment_id>', methods=['GET', 'POST'])
@login_required
def webrtc_signal(shipment_id):
    if request.method == 'POST':
        data = request.json
        signals[shipment_id] = {
            'sender_id': session['user_id'],
            'data': data,
            'timestamp': datetime.now()
        }
        return jsonify({'status': 'ok'})
    
    # GET: fetch signal if it's not from us
    signal = signals.get(shipment_id)
    if signal and signal['sender_id'] != session['user_id']:
        # Clear after reading to simulate one-time exchange
        # del signals[shipment_id] 
        return jsonify(signal['data'])
    return jsonify({})

@app.route('/admin/chat-logs')
@login_required
@admin_required
def admin_chat_logs():
    """FR-805: All chat messages retrievable by Admin for auditing."""
    c = get_conn()
    cur = c.cursor()
    cur.execute("""
        SELECT cm.*, s.item_type, u.name as sender_name
        FROM chat_messages cm
        JOIN shipments s ON cm.shipment_id = s.shipment_id
        JOIN users u ON cm.sender_id = u.id
        ORDER BY cm.created_at DESC
    """)
    logs = rows_to_dicts(cur.fetchall())
    return render_template('admin_chat_logs.html', logs=logs)


def trigger_dispatch_engine(shipment_id):
    """FR-410 to FR-414: Automated Intelligent Dispatch Engine."""
    c = get_conn()
    cur = c.cursor()
    
    # Get shipment details
    cur.execute("SELECT * FROM shipments WHERE shipment_id = ?", (shipment_id,))
    shipment = row_to_dict(cur.fetchone())
    if not shipment: return
    
    # Get settings
    cur.execute("SELECT key, value FROM dispatch_settings")
    settings = {r[0]: r[1] for r in cur.fetchall()}
    threshold = float(settings.get('confidence_threshold', 0.85))
    goal = settings.get('optimization_goal', 'MINIMIZE_DEADHEAD')
    
    # Find eligible drivers
    cur.execute("SELECT * FROM drivers WHERE assigned_truck IS NOT NULL")
    drivers = rows_to_dicts(cur.fetchall())
    
    candidates = []
    for d in drivers:
        cur.execute("SELECT * FROM trucks WHERE truck_number = ?", (d['assigned_truck'],))
        truck = row_to_dict(cur.fetchone())
        if not truck or truck['status'] != 'Available': continue
        
        # Score calculation
        score = 0.5
        try:
            if truck['capacity'] and shipment['weight']:
                if float(truck['capacity']) >= float(shipment['weight']):
                    score += 0.2
        except: pass
        if d.get('performance_rating'): score += (float(d['performance_rating']) / 5.0) * 0.1
        if d.get('hos_remaining') and float(d['hos_remaining']) > 4: score += 0.1
        
        final_score = min(score, 1.0)
        candidates.append({'driver_id': d['id'], 'user_id': d['user_id'], 'driver_name': d['driver_name'], 'truck_number': d['assigned_truck'], 'score': final_score})
    
    candidates.sort(key=lambda x: x['score'], reverse=True)
    best_candidate = candidates[0] if candidates else None
    
    if best_candidate and best_candidate['score'] >= threshold:
        window = int(settings.get('driver_acceptance_window', 5))
        deadline = (datetime.now() + timedelta(minutes=window)).isoformat()
        cur.execute(
            """UPDATE shipments SET status = 'Pending Acceptance', driver_id = ?, assigned_truck = ?, assignment_deadline = ?, dispatch_metadata = ? WHERE shipment_id = ?""",
            (best_candidate['driver_id'], best_candidate['truck_number'], deadline, json.dumps(best_candidate), shipment_id)
        )
        create_notification(cur, f"Automated assignment for shipment {shipment_id}. Accept within {window}m.", category='info', user_id=best_candidate['user_id'], link='/shipments')
        cur.execute(
            """INSERT INTO dispatch_audit_logs (shipment_id, decision_type, algo_version, parameters_json, compatibility_score, assigned_driver_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (shipment_id, 'Automated', '1.0', json.dumps(settings), best_candidate['score'], best_candidate['driver_id'], datetime.now().isoformat())
        )
    else:
        top_three = json.dumps(candidates[:3])
        cur.execute("UPDATE shipments SET status = 'Requires Manual Assignment', dispatch_metadata = ? WHERE shipment_id = ?", (top_three, shipment_id))
        create_notification(cur, f"Manual assignment required for {shipment_id}.", category='warning', role_target='admin', link='/shipments')
    c.commit()


@app.route('/driver/shipment-action/<int:shipment_id>/<action>', methods=['POST'])
@login_required
@driver_required
def driver_shipment_action(shipment_id, action):
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
    shipment = row_to_dict(cur.fetchone())
    if not shipment or shipment['status'] != 'Pending Acceptance':
        flash('Invalid shipment or action.', 'danger')
        return redirect(url_for('shipments'))
    
    if shipment.get('assignment_deadline') and datetime.now().isoformat() > shipment['assignment_deadline']:
        cur.execute("UPDATE shipments SET status = 'Pending Assignment', driver_id = NULL, assigned_truck = '' WHERE id = ?", (shipment_id,))
        c.commit()
        flash('Assignment window expired.', 'warning')
        trigger_dispatch_engine(shipment['shipment_id'])
        return redirect(url_for('shipments'))
    if action == 'Accept':
        cur.execute("UPDATE shipments SET status = 'Assigned', updated_at = ? WHERE id = ?", (datetime.now().isoformat(), shipment_id))
        cur.execute("UPDATE trucks SET status = 'On Route' WHERE truck_number = ?", (shipment['assigned_truck'],))
        flash('Accepted!', 'success')
    else:
        cur.execute("UPDATE shipments SET status = 'Pending Assignment', driver_id = NULL, assigned_truck = '', updated_at = ? WHERE id = ?", (datetime.now().isoformat(), shipment_id))
        trigger_dispatch_engine(shipment['shipment_id'])
    c.commit()
    return redirect(url_for('shipments'))


@app.route('/admin/dispatch-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_dispatch_settings():
    c = get_conn()
    cur = c.cursor()
    if request.method == 'POST':
        for k in ['optimization_goal', 'confidence_threshold', 'driver_acceptance_window']:
            if k in request.form: cur.execute("INSERT OR REPLACE INTO dispatch_settings (key, value) VALUES (?, ?)", (k, request.form[k]))
        c.commit()
        flash('Updated!', 'success')
        return redirect(url_for('admin_dispatch_settings'))
    cur.execute("SELECT key, value FROM dispatch_settings")
    settings = {r[0]: r[1] for r in cur.fetchall()}
    return render_template('admin_dispatch_settings.html', settings=settings)


@app.route('/admin/dispatch-audit-logs')
@login_required
@admin_required
def admin_dispatch_audit_logs():
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM dispatch_audit_logs ORDER BY created_at DESC")
    logs = rows_to_dicts(cur.fetchall())
    return render_template('admin_dispatch_audit_logs.html', logs=logs)


@app.route('/admin/shipments/assign-driver/<int:shipment_id>', methods=['POST'])
@login_required
@admin_required
def admin_assign_driver(shipment_id):
    """FR-407, FR-417: Admin manual driver assignment with reason capture."""
    driver_id = request.form.get('driver_id')
    override_reason = request.form.get('override_reason', 'None')
    c = get_conn()
    cur = c.cursor()
    cur.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,))
    driver = row_to_dict(cur.fetchone())
    if not driver:
        flash('Driver not found.', 'danger')
        return redirect(url_for('shipments'))
    cur.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
    shipment = row_to_dict(cur.fetchone())
    now = datetime.now().isoformat()
    cur.execute("UPDATE shipments SET driver_id = ?, assigned_truck = ?, status = 'Assigned', updated_at = ? WHERE id = ?", (driver['id'], driver['assigned_truck'], now, shipment_id))
    cur.execute("UPDATE trucks SET status = 'On Route' WHERE truck_number = ?", (driver['assigned_truck'],))
    cur.execute("INSERT INTO dispatch_audit_logs (shipment_id, decision_type, override_reason, admin_id, compatibility_score, created_at) VALUES (?, ?, ?, ?, ?, ?)", (shipment['shipment_id'], 'Manual', override_reason, session['user_id'], 0.0, now))
    if shipment.get('customer_id'): create_notification(cur, f"Shipment {shipment['shipment_id']} assigned to {driver['driver_name']}.", category='info', user_id=int(shipment['customer_id']), link='/shipments')
    create_notification(cur, f"Manually assigned to {shipment['shipment_id']}.", category='info', user_id=driver['user_id'], link='/shipments')
    c.commit()
    flash('Driver assigned!', 'success')
    return redirect(url_for('shipments'))


@app.route('/driver/update-location', methods=['POST'])
@login_required
@driver_required
def driver_update_location():
    """FR-501, FR-504, FR-512: Automated location push and deviation check."""
    lat = request.form.get('latitude')
    lng = request.form.get('longitude')
    loc_text = request.form.get('location_text', 'GPS Update')
    
    if not lat or not lng:
        return jsonify({'status': 'error', 'message': 'Missing coordinates'}), 400
        
    c = get_conn()
    cur = c.cursor()
    
    # Get driver/truck
    cur.execute("SELECT id, driver_name, assigned_truck FROM drivers WHERE user_id = ?", (session['user_id'],))
    driver = row_to_dict(cur.fetchone())
    if not driver: return jsonify({'status': 'error'}), 404
    
    # Check if paused (FR-505)
    cur.execute("SELECT paused_until FROM drivers WHERE id = ?", (driver['id'],))
    p_row = cur.fetchone()
    if p_row and p_row[0] and datetime.fromisoformat(p_row[0]) > datetime.now():
        return jsonify({'status': 'paused', 'until': p_row[0]})

    now = datetime.now().isoformat()
    
    # FR-504: Store timestamped data
    cur.execute(
        """INSERT INTO location_updates (driver_id, driver_name, truck_number, current_location, latitude, longitude, source, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 'Device', ?)""",
        (driver['id'], driver['driver_name'], driver['assigned_truck'], loc_text, lat, lng, now)
    )
    
    cur.execute(
        "INSERT OR REPLACE INTO locations (driver_id, driver_name, truck_number, current_location, updated_at) VALUES (?, ?, ?, ?, ?)",
        (driver['id'], driver['driver_name'], driver['assigned_truck'], loc_text, now)
    )
    
    # FR-512: Route Deviation Detection
    cur.execute("SELECT id, shipment_id FROM shipments WHERE driver_id = ? AND status = 'In Transit'", (driver['id'],))
    active_shipment = cur.fetchone()
    if active_shipment:
        check_route_deviation(cur, active_shipment[0], float(lat), float(lng))

    c.commit()
    return jsonify({'status': 'ok'})


@app.route('/driver/pause-location', methods=['POST'])
@login_required
@driver_required
def driver_pause_location():
    """FR-505: Temporarily pause location sharing for max 1 hour."""
    c = get_conn()
    cur = c.cursor()
    paused_until = (datetime.now() + timedelta(hours=1)).isoformat()
    cur.execute("UPDATE drivers SET paused_until = ? WHERE user_id = ?", (paused_until, session['user_id']))
    create_notification(cur, f"Driver {session['name']} paused location until {paused_until[:16]}", category='warning', role_target='admin')
    c.commit()
    flash('Paused for 1 hour.', 'info')
    return redirect(url_for('dashboard'))


def optimize_shipment_route(cur, shipment_pk):
    """FR-507, FR-511: AI-Driven Route Optimization."""
    cur.execute("SELECT * FROM shipments WHERE id = ?", (shipment_pk,))
    shipment = row_to_dict(cur.fetchone())
    if not shipment: return
    
    # Get driver HOS
    cur.execute("SELECT hos_remaining FROM drivers WHERE id = ?", (shipment['driver_id'],))
    hos = cur.fetchone()[0] or 11.0
    
    # Mock Route Generation (A-B path)
    # In real app, call Google Maps/OpenRouteService API
    route_points = [[19.076, 72.877], [18.520, 73.856]] # Mumbai to Pune
    
    # FR-511: HOS Aware (Suggest rest stop if route > HOS)
    if float(hos) < 2:
        # Add a rest stop point
        route_points.insert(1, [18.75, 73.4]) 
    
    cur.execute(
        """INSERT INTO shipment_routes (shipment_id, planned_route_json, eta, last_optimized_at)
           VALUES (?, ?, ?, ?)""",
        (shipment['shipment_id'], json.dumps(route_points), (datetime.now() + timedelta(hours=4)).isoformat(), datetime.now().isoformat())
    )
    
    cur.execute("UPDATE shipments SET eta = ? WHERE id = ?", ((datetime.now() + timedelta(hours=4)).isoformat(), shipment_pk))


def check_route_deviation(cur, shipment_pk, current_lat, current_lng):
    """FR-512: Flag deviations > 3km."""
    cur.execute("SELECT * FROM shipments WHERE id = ?", (shipment_pk,))
    shipment = row_to_dict(cur.fetchone())
    cur.execute("SELECT planned_route_json FROM shipment_routes WHERE shipment_id = ? ORDER BY id DESC LIMIT 1", (shipment['shipment_id'],))
    row = cur.fetchone()
    if not row: return
    
    planned = json.loads(row[0])
    # Very simple check: distance to nearest planned point
    min_dist = 999
    for p in planned:
        dist = abs(p[0] - current_lat) + abs(p[1] - current_lng) # Rough degrees
        if dist < min_dist: min_dist = dist
        
    if min_dist > 0.03: # Approx 3km in degrees
        cur.execute(
            "INSERT INTO route_alerts (shipment_id, alert_type, message, created_at) VALUES (?, ?, ?, ?)",
            (shipment['shipment_id'], 'Deviation', f'Route deviation detected: {min_dist*100:.1f}km off path', datetime.now().isoformat())
        )
        create_notification(cur, f"Deviation Alert for {shipment['shipment_id']}!", category='danger', role_target='admin')


@app.route('/driver/reroute-action/<int:shipment_id>/<action>', methods=['POST'])
@login_required
@driver_required
def driver_reroute_action(shipment_id, action):
    """FR-509, FR-510: Driver re-route response and ETA update."""
    c = get_conn()
    cur = c.cursor()
    if action == 'Accept':
        # Mock logic: update route and ETA
        new_eta = (datetime.now() + timedelta(hours=3)).isoformat()
        cur.execute("UPDATE shipments SET eta = ? WHERE id = ?", (new_eta, shipment_id))
        cur.execute("SELECT shipment_id, customer_id FROM shipments WHERE id = ?", (shipment_id,))
        shipment = cur.fetchone()
        
        # Notify customer (FR-510)
        create_notification(cur, f"New ETA for {shipment[0]}: {new_eta[:16]}. Driver accepted optimized route.", category='success', user_id=int(shipment[1]), link='/shipments')
        flash('Re-route accepted! ETA updated.', 'success')
    else:
        flash('Re-route ignored.', 'info')
    
    c.commit()
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    # FR-Deployment: Optional ngrok support
    if os.environ.get('USE_NGROK') == 'True' and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        from pyngrok import ngrok
        
        # Set auth token if provided
        ngrok_token = os.environ.get('NGROK_AUTH_TOKEN')
        if ngrok_token:
            ngrok.set_auth_token(ngrok_token)
            
        try:
            # Check for existing tunnels first
            tunnels = ngrok.get_tunnels()
            if tunnels:
                public_url = tunnels[0].public_url
            else:
                # Open a tunnel on the default Flask port
                public_url = ngrok.connect(5000).public_url
            print(f" * ngrok tunnel available at: {public_url}")
        except Exception as e:
            print(f" * Could not start ngrok: {e}")
        
    app.run(debug=True, port=5000)
