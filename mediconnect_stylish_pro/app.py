
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, io, csv, datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'replace-with-a-secure-random-key'  # change for production
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'database.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
PROFILE_FOLDER = os.path.join(UPLOAD_FOLDER, 'profiles')
REPORT_FOLDER = os.path.join(UPLOAD_FOLDER, 'reports')
ALLOWED_EXT = {'png','jpg','jpeg','pdf'}

os.makedirs(PROFILE_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXT

def get_db():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        profile_pic TEXT
    );
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        specialization TEXT,
        city TEXT,
        experience INTEGER,
        rating REAL,
        fee REAL,
        mode TEXT
    );
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER,
        patient_id INTEGER,
        date TEXT,
        mode TEXT,
        disease TEXT,
        age INTEGER,
        status TEXT DEFAULT 'Booked',
        medicine TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(doctor_id) REFERENCES doctors(id),
        FOREIGN KEY(patient_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER,
        filename TEXT,
        uploaded_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(appointment_id) REFERENCES appointments(id)
    );
    ''')
    conn.commit()

    cur.execute("SELECT COUNT(*) as c FROM users")
    if cur.fetchone()["c"] == 0:
        cur.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                    ("Admin User","admin@example.com", generate_password_hash("password123"), "admin"))
        cur.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                    ("Test Patient","patient@example.com", generate_password_hash("password123"), "patient"))
        cur.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                    ("Dr. Alice","doctor@example.com", generate_password_hash("password123"), "doctor"))
    cur.execute("SELECT COUNT(*) as c FROM doctors")
    if cur.fetchone()["c"] == 0:
        doctors = [
            ("Sam Wallfolk","Clinical psychologist","New York",10,5.0,800,"Both"),
            ("Sarah Legend","Child psychologist","Chicago",8,4.8,1200,"Offline"),
            ("Ben Affleck","Military psychologist","Los Angeles",12,4.6,500,"Online")
        ]
        cur.executemany("INSERT INTO doctors (name,specialization,city,experience,rating,fee,mode) VALUES (?,?,?,?,?,?,?)", doctors)
    conn.commit()
    conn.close()

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash("You do not have access to that page.", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def inject_notifications():
    if 'user_id' in session:
        conn = get_db()
        notifs = conn.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 6", (session['user_id'],)).fetchall()
        unread = conn.execute("SELECT COUNT(*) as c FROM notifications WHERE user_id=? AND is_read=0", (session['user_id'],)).fetchone()['c']
        conn.close()
        return dict(__notifications=notifs, __unread_count=unread)
    return dict(__notifications=[], __unread_count=0)

@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        if role == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        if role == 'patient':
            return redirect(url_for('patient_dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role','patient')
        pic = request.files.get('profile_pic')
        pic_filename = None
        if pic and pic.filename!='' and allowed_file(pic.filename):
            pic_filename = secure_filename(f"{email}_profile_{pic.filename}")
            pic.save(os.path.join(PROFILE_FOLDER, pic_filename))
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (name,email,password,role,profile_pic) VALUES (?,?,?,?,?)",
                        (name, email, generate_password_hash(password), role, pic_filename))
            conn.commit()
            flash('Account created. Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Error creating account: ' + str(e), 'danger')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/admin')
@login_required(role='admin')
def admin_dashboard():
    conn = get_db()
    doctors = conn.execute("SELECT * FROM doctors").fetchall()
    users = conn.execute("SELECT * FROM users WHERE role != 'admin'").fetchall()
    appointments = conn.execute("SELECT a.*, d.name as doctor_name, u.name as patient_name FROM appointments a LEFT JOIN doctors d ON a.doctor_id=d.id LEFT JOIN users u ON a.patient_id=u.id ORDER BY a.created_at DESC LIMIT 30").fetchall()
    conn.close()
    return render_template('admin/dashboard.html', doctors=doctors, users=users, appointments=appointments)

@app.route('/admin/reports')
@login_required(role='admin')
def admin_reports():
    conn = get_db()
    by_month = conn.execute("SELECT strftime('%Y-%m', date) as month, COUNT(*) as cnt FROM appointments GROUP BY month ORDER BY month DESC").fetchall()
    per_doctor = conn.execute("SELECT d.name, COUNT(a.id) as cnt FROM doctors d LEFT JOIN appointments a ON a.doctor_id=d.id GROUP BY d.id ORDER BY cnt DESC").fetchall()
    revenue = conn.execute("SELECT SUM(d.fee) as total FROM appointments a JOIN doctors d ON a.doctor_id=d.id WHERE a.status='Completed'").fetchone()['total'] or 0
    conn.close()
    return render_template('admin/reports.html', by_month=by_month, per_doctor=per_doctor, revenue=revenue)

@app.route('/admin/reports/export_csv')
@login_required(role='admin')
def export_reports_csv():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT a.id, a.date, a.status, d.name as doctor_name, u.name as patient_name, d.fee FROM appointments a JOIN doctors d ON a.doctor_id=d.id JOIN users u ON a.patient_id=u.id")
    rows = cur.fetchall()
    conn.close()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['id','date','status','doctor','patient','fee'])
    for r in rows:
        cw.writerow([r['id'], r['date'], r['status'], r['doctor_name'], r['patient_name'], r['fee']])
    output = io.BytesIO()
    output.write(si.getvalue().encode())
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='appointments_report.csv')


@app.route('/doctor')
@login_required(role='doctor')
def doctor_dashboard():
    conn = get_db()
   
    active = conn.execute("""SELECT a.*, d.name as doctor_name, u.name as patient_name,
                           (SELECT GROUP_CONCAT(filename) FROM reports r WHERE r.appointment_id=a.id) as reports
                           FROM appointments a
                           LEFT JOIN doctors d ON a.doctor_id=d.id
                           LEFT JOIN users u ON a.patient_id=u.id
                           WHERE d.name LIKE ? AND a.status IN ('Booked','Confirmed')
                           ORDER BY a.date DESC""", ('%'+session.get('name')+'%',)).fetchall()

   
    history = conn.execute("""SELECT a.*, d.name as doctor_name, u.name as patient_name,
                           (SELECT GROUP_CONCAT(filename) FROM reports r WHERE r.appointment_id=a.id) as reports
                           FROM appointments a
                           LEFT JOIN doctors d ON a.doctor_id=d.id
                           LEFT JOIN users u ON a.patient_id=u.id
                           WHERE d.name LIKE ? AND a.status IN ('Completed','Cancelled')
                           ORDER BY a.date DESC""", ('%'+session.get('name')+'%',)).fetchall()

    conn.close()
    return render_template('doctor/dashboard.html', active=active, history=history)

@app.route('/doctor/profile', methods=['GET','POST'])
@login_required(role='doctor')
def doctor_profile():
    conn = get_db()
    doctor = conn.execute("SELECT * FROM doctors WHERE name LIKE ?", ('%'+session.get('name')+'%',)).fetchone()
    if request.method == 'POST':
        name = request.form.get('name')
        specialization = request.form.get('specialization')
        city = request.form.get('city')
        experience = int(request.form.get('experience') or 0)
        rating = float(request.form.get('rating') or 0.0)
        fee = float(request.form.get('fee') or 0.0)
        mode = request.form.get('mode')
        if doctor:
            conn.execute("UPDATE doctors SET name=?,specialization=?,city=?,experience=?,rating=?,fee=?,mode=? WHERE id=?",
                         (name,specialization,city,experience,rating,fee,mode,doctor['id']))
            conn.commit()
            flash('Profile updated.', 'success')
        else:
            conn.execute("INSERT INTO doctors (name,specialization,city,experience,rating,fee,mode) VALUES (?,?,?,?,?,?,?)",
                         (name,specialization,city,experience,rating,fee,mode))
            conn.commit()
            flash('Profile created (note: admins manage doctors).', 'success')
        conn.close()
        return redirect(url_for('doctor_profile'))
    conn.close()
    return render_template('doctor/profile.html', doctor=doctor)

@app.route('/doctor/confirm/<int:appid>')
@login_required(role='doctor')
def doctor_confirm(appid):
    conn = get_db()
    conn.execute("UPDATE appointments SET status='Confirmed' WHERE id=?", (appid,))
    appt = conn.execute("SELECT patient_id FROM appointments WHERE id=?", (appid,)).fetchone()
    if appt:
        conn.execute("INSERT INTO notifications (user_id,message) VALUES (?,?)", (appt['patient_id'], f"Your appointment #{appid} has been Confirmed by the doctor."))
    conn.commit()
    conn.close()
    flash('Appointment confirmed.', 'success')
    return redirect(url_for('doctor_dashboard'))

@app.route('/doctor/prescribe/<int:appid>', methods=['POST'])
@login_required(role='doctor')
def doctor_prescribe(appid):
    medicine = request.form.get('medicine')
    notes = request.form.get('notes')
    conn = get_db()
    conn.execute("UPDATE appointments SET medicine=?, notes=?, status='Completed' WHERE id=?", (medicine, notes, appid))
    appt = conn.execute("SELECT patient_id FROM appointments WHERE id=?", (appid,)).fetchone()
    if appt:
        conn.execute("INSERT INTO notifications (user_id,message) VALUES (?,?)", (appt['patient_id'], f"Your appointment #{appid} marked Completed and medicine prescribed."))
    conn.commit()
    conn.close()
    flash('Medicine saved and appointment marked completed.', 'success')
    return redirect(url_for('doctor_dashboard'))


@app.route('/patient')
@login_required(role='patient')
def patient_dashboard():
    uid = session.get('user_id')
    conn = get_db()
    appointments = conn.execute("""SELECT a.*, d.name as doctor_name,
                                (SELECT GROUP_CONCAT(filename) FROM reports r WHERE r.appointment_id=a.id) as reports
                                FROM appointments a
                                LEFT JOIN doctors d ON a.doctor_id=d.id
                                WHERE a.patient_id = ? ORDER BY a.date DESC""", (uid,)).fetchall()
    doctors = conn.execute("SELECT * FROM doctors").fetchall()
    conn.close()
    return render_template('patient/dashboard.html', appointments=appointments, doctors=doctors)

@app.route('/book/<int:doctor_id>', methods=['GET','POST'])
@login_required(role='patient')
def book(doctor_id):
    if request.method == 'POST':
        date = request.form.get('date')
        mode = request.form.get('mode')
        disease = request.form.get('disease')
        age = int(request.form.get('age') or 0)
        uid = session.get('user_id')
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO appointments (doctor_id, patient_id, date, mode, disease, age) VALUES (?,?,?,?,?,?)", (doctor_id, uid, date, mode, disease, age))
        appt_id = cur.lastrowid
        conn.execute("INSERT INTO notifications (user_id,message) VALUES (?,?)", (uid, f"Appointment #{appt_id} booked successfully."))
        conn.commit()
        conn.close()
        flash('Appointment booked.', 'success')
        return redirect(url_for('patient_dashboard'))
    conn = get_db()
    doctor = conn.execute("SELECT * FROM doctors WHERE id=?", (doctor_id,)).fetchone()
    conn.close()
    return render_template('patient/book.html', doctor=doctor)

@app.route('/patient/cancel/<int:appid>')
@login_required(role='patient')
def patient_cancel(appid):
    uid = session.get('user_id')
    conn = get_db()
    appt = conn.execute("SELECT * FROM appointments WHERE id=? AND patient_id=?", (appid, uid)).fetchone()
    if not appt:
        flash('Appointment not found or not yours.', 'danger')
        conn.close()
        return redirect(url_for('patient_dashboard'))
    if appt['status']=='Completed':
        flash('Cannot cancel a completed appointment.', 'warning')
        conn.close()
        return redirect(url_for('patient_dashboard'))
    conn.execute("UPDATE appointments SET status='Cancelled' WHERE id=?", (appid,))
    conn.execute("INSERT INTO notifications (user_id,message) VALUES ((SELECT id FROM users WHERE role='doctor' LIMIT 1), ?)", (f"Appointment #{appid} was cancelled by patient.",))
    conn.commit()
    conn.close()
    flash('Appointment cancelled.', 'info')
    return redirect(url_for('patient_dashboard'))

@app.route('/appointment/<int:appid>/upload_report', methods=['POST'])
@login_required(role='patient')
def upload_report(appid):
    file = request.files.get('report')
    if not file or file.filename=='':
        flash('No file selected.', 'warning')
        return redirect(url_for('patient_dashboard'))
    if not allowed_file(file.filename):
        flash('File type not allowed.', 'danger')
        return redirect(url_for('patient_dashboard'))
    filename = secure_filename(f"{appid}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
    path = os.path.join(REPORT_FOLDER, filename)
    file.save(path)
    conn = get_db()
    conn.execute("INSERT INTO reports (appointment_id, filename) VALUES (?,?)", (appid, filename))
    appt = conn.execute("SELECT doctor_id, patient_id FROM appointments WHERE id=?", (appid,)).fetchone()
    if appt:
       
        conn.execute("INSERT INTO notifications (user_id,message) VALUES ((SELECT id FROM users WHERE role='doctor' LIMIT 1), ?)", (f"New report uploaded for appointment #{appid}.",))
        conn.execute("INSERT INTO notifications (user_id,message) VALUES (?,?)", (appt['patient_id'], f"Report uploaded for appointment #{appid}."))
    conn.commit()
    conn.close()
    flash('Report uploaded.', 'success')
    return redirect(url_for('patient_dashboard'))

@app.route('/notifications/mark_read/<int:nid>')
@login_required()
def mark_read(nid):
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?", (nid, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('index'))

@app.route('/notifications/clear')
@login_required()
def clear_notifications():
    conn = get_db()
    conn.execute("DELETE FROM notifications WHERE user_id=?", (session['user_id'],))
    conn.commit()
    conn.close()
    flash('Notifications cleared.', 'info')
    return redirect(request.referrer or url_for('index'))

@app.route('/uploads/profiles/<path:filename>')
def uploaded_profile(filename):
    return send_file(os.path.join(PROFILE_FOLDER, filename))

@app.route('/uploads/reports/<path:filename>')
def uploaded_report(filename):
    return send_file(os.path.join(REPORT_FOLDER, filename))

@app.route('/api/notifications/unread_count')
def api_unread_count():
    if 'user_id' not in session:
        return jsonify({'count':0})
    conn = get_db()
    cnt = conn.execute("SELECT COUNT(*) as c FROM notifications WHERE user_id=? AND is_read=0", (session['user_id'],)).fetchone()['c']
    conn.close()
    return jsonify({'count':cnt})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
