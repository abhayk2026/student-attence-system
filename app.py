"""
Student Attendance Management System - Main Flask Application (app.py)
Handles routing, session authentication, student/subject CRUD, attendance marking,
percentage calculation logic, low attendance warnings, and dashboard statistics.
"""

import sqlite3
from datetime import date
from functools import wraps

from flask import (
    Flask, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash

import database

app = Flask(__name__)
# Secret key for session management
app.secret_key = 'student_attendance_management_secret_key_viva_project'


# Initialize database schema and default data on app context startup
@app.before_request
def initialize_app_database():
    """Ensure database tables and initial seed data exist before processing requests."""
    if not hasattr(g, 'db_initialized'):
        database.init_db()
        g.db_initialized = True


def login_required(f):
    """Decorator to restrict access to authenticated admin users only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first to access the dashboard.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin Login Route"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Username and password are required!', 'danger')
            return render_template('login.html')

        conn = database.get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Log out admin user and clear session."""
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))


# ==========================================
# DASHBOARD ROUTE
# ==========================================

@app.route('/')
@login_required
def dashboard():
    """
    Dashboard Overview:
    Computes total students, total subjects, overall attendance percentage,
    low attendance count (<75%), and lists low attendance students.
    """
    conn = database.get_db_connection()

    # Total counts
    total_students = conn.execute(
        "SELECT COUNT(*) FROM students").fetchone()[0]
    total_subjects = conn.execute(
        "SELECT COUNT(*) FROM subjects").fetchone()[0]
    total_attendance_logs = conn.execute(
        "SELECT COUNT(*) FROM attendance").fetchone()[0]

    # Overall System Attendance Rate (%)
    total_records = conn.execute(
        "SELECT COUNT(*) FROM attendance").fetchone()[0]
    present_records = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE status IN ('Present', 'Late')"
    ).fetchone()[0]

    overall_percentage = round(
        (present_records / total_records * 100),
        1) if total_records > 0 else 0.0

    # Calculate individual student attendance percentages to find low
    # attendance students (< 75%)
    student_stats_query = """
        SELECT
            s.id,
            s.roll_number,
            s.name,
            s.department,
            s.semester,
            COUNT(a.id) AS total_classes,
            SUM(CASE WHEN a.status IN ('Present', 'Late') THEN 1 ELSE 0 END) AS attended_classes
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id
        GROUP BY s.id
    """
    all_students_stats = conn.execute(student_stats_query).fetchall()

    low_attendance_list = []
    for stat in all_students_stats:
        t_classes = stat['total_classes']
        a_classes = stat['attended_classes']
        pct = round(
            (a_classes / t_classes * 100),
            1) if t_classes > 0 else 100.0

        if pct < 75.0 and t_classes > 0:
            low_attendance_list.append({
                'id': stat['id'],
                'roll_number': stat['roll_number'],
                'name': stat['name'],
                'department': stat['department'],
                'semester': stat['semester'],
                'total_classes': t_classes,
                'attended_classes': a_classes,
                'percentage': pct
            })

    # Recent attendance entries for dashboard activity widget
    recent_activities = conn.execute("""
        SELECT a.attendance_date, s.name AS student_name, sub.subject_code, sub.subject_name, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN subjects sub ON a.subject_id = sub.id
        ORDER BY a.id DESC
        LIMIT 6
    """).fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        total_students=total_students,
        total_subjects=total_subjects,
        total_attendance_logs=total_attendance_logs,
        overall_percentage=overall_percentage,
        low_attendance_count=len(low_attendance_list),
        low_attendance_list=low_attendance_list,
        recent_activities=recent_activities
    )


# ==========================================
# STUDENT MANAGEMENT ROUTES
# ==========================================

@app.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    """
    Student Management:
    GET: List all students with search and filter capabilities.
    POST: Add a new student record.
    """
    conn = database.get_db_connection()

    if request.method == 'POST':
        roll_number = request.form.get('roll_number', '').strip()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        department = request.form.get('department', '').strip()
        semester = request.form.get('semester', '').strip()

        # Backend Validation
        if not (roll_number and name and email and department and semester):
            flash('All student fields are required!', 'danger')
        else:
            try:
                conn.execute(
                    "INSERT INTO students (roll_number, name, email, department, semester) VALUES (?, ?, ?, ?, ?)",
                    (roll_number, name, email, department, int(semester))
                )
                conn.commit()
                flash(
                    f'Student "{name}" ({roll_number}) added successfully!',
                    'success')
                return redirect(url_for('students'))
            except sqlite3.IntegrityError:
                flash(f'Roll Number "{roll_number}" already exists!', 'danger')
            except Exception as e:
                flash(f'Error adding student: {str(e)}', 'danger')

    # GET Request: Fetch students list with optional search query
    search_query = request.args.get('search', '').strip()
    dept_filter = request.args.get('department', '').strip()

    sql = "SELECT * FROM students WHERE 1=1"
    params = []

    if search_query:
        sql += " AND (roll_number LIKE ? OR name LIKE ? OR email LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term])

    if dept_filter:
        sql += " AND department = ?"
        params.append(dept_filter)

    sql += " ORDER BY roll_number ASC"
    student_records = conn.execute(sql, params).fetchall()

    # Get unique departments for filter dropdown
    departments = conn.execute(
        "SELECT DISTINCT department FROM students ORDER BY department").fetchall()
    conn.close()

    return render_template('students.html', students=student_records,
                           departments=departments, search_query=search_query, selected_dept=dept_filter)


@app.route('/students/edit/<int:student_id>', methods=['POST'])
@login_required
def edit_student(student_id):
    """Edit an existing student details."""
    roll_number = request.form.get('roll_number', '').strip()
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    department = request.form.get('department', '').strip()
    semester = request.form.get('semester', '').strip()

    if not (roll_number and name and email and department and semester):
        flash('All fields are required to update student.', 'danger')
        return redirect(url_for('students'))

    conn = database.get_db_connection()
    try:
        conn.execute(
            "UPDATE students SET roll_number = ?, name = ?, email = ?, department = ?, semester = ? WHERE id = ?",
            (roll_number, name, email, department, int(semester), student_id)
        )
        conn.commit()
        flash(f'Student details for "{name}" updated successfully.', 'success')
    except sqlite3.IntegrityError:
        flash(
            f'Roll Number "{roll_number}" is already used by another student!',
            'danger')
    except Exception as e:
        flash(f'Error updating student: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('students'))


@app.route('/students/delete/<int:student_id>', methods=['POST'])
@login_required
def delete_student(student_id):
    """Delete a student record."""
    conn = database.get_db_connection()
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    flash('Student record deleted successfully.', 'success')
    return redirect(url_for('students'))


# ==========================================
# SUBJECT MANAGEMENT ROUTES
# ==========================================

@app.route('/subjects', methods=['GET', 'POST'])
@login_required
def subjects():
    """
    Subject Management:
    GET: List all subjects.
    POST: Add a new subject.
    """
    conn = database.get_db_connection()

    if request.method == 'POST':
        subject_code = request.form.get('subject_code', '').strip().upper()
        subject_name = request.form.get('subject_name', '').strip()
        department = request.form.get('department', '').strip()
        semester = request.form.get('semester', '').strip()

        if not (subject_code and subject_name and department and semester):
            flash('All subject fields are required!', 'danger')
        else:
            try:
                conn.execute(
                    "INSERT INTO subjects (subject_code, subject_name, department, semester) VALUES (?, ?, ?, ?)",
                    (subject_code, subject_name, department, int(semester))
                )
                conn.commit()
                flash(
                    f'Subject "{subject_name}" ({subject_code}) added successfully!',
                    'success')
                return redirect(url_for('subjects'))
            except sqlite3.IntegrityError:
                flash(
                    f'Subject code "{subject_code}" already exists!',
                    'danger')
            except Exception as e:
                flash(f'Error adding subject: {str(e)}', 'danger')

    subject_list = conn.execute(
        "SELECT * FROM subjects ORDER BY department, semester, subject_code").fetchall()
    conn.close()
    return render_template('subjects.html', subjects=subject_list)


@app.route('/subjects/delete/<int:subject_id>', methods=['POST'])
@login_required
def delete_subject(subject_id):
    """Delete a subject record."""
    conn = database.get_db_connection()
    conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    conn.commit()
    conn.close()
    flash('Subject deleted successfully.', 'success')
    return redirect(url_for('subjects'))


# ==========================================
# ATTENDANCE MARKING ROUTES
# ==========================================

@app.route('/attendance/mark', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    """
    Mark Attendance Route:
    GET: Allows admin to choose subject and date, then fetches eligible students.
    POST: Processes batch attendance marking (upsert into attendance table).
    """
    conn = database.get_db_connection()

    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        attendance_date = request.form.get('attendance_date')
        student_ids = request.form.getlist('student_ids')

        if not subject_id or not attendance_date or not student_ids:
            flash(
                'Subject, Date, and at least one student are required to mark attendance.',
                'danger')
            return redirect(url_for('mark_attendance'))

        try:
            # Batch upsert attendance for each student
            for sid in student_ids:
                status = request.form.get(f'status_{sid}', 'Present')
                remarks = request.form.get(f'remarks_{sid}', '').strip()

                # Using INSERT OR REPLACE to update existing records if
                # re-marking for same date/subject
                conn.execute("""
                    INSERT INTO attendance (student_id, subject_id, attendance_date, status, remarks)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(student_id, subject_id, attendance_date)
                    DO UPDATE SET status=excluded.status, remarks=excluded.remarks
                """, (sid, subject_id, attendance_date, status, remarks))

            conn.commit()
            flash(
                f'Attendance recorded successfully for {
                    len(student_ids)} student(s) on {attendance_date}!',
                'success')
            return redirect(url_for('attendance_report',
                            subject_id=subject_id, date=attendance_date))
        except Exception as e:
            flash(f'Error recording attendance: {str(e)}', 'danger')

    # GET Request
    selected_subject_id = request.args.get('subject_id', type=int)
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))

    subjects_list = conn.execute(
        "SELECT * FROM subjects ORDER BY department, subject_code").fetchall()

    students_for_attendance = []
    selected_subject = None
    existing_attendance_map = {}

    if selected_subject_id:
        selected_subject = conn.execute(
            "SELECT * FROM subjects WHERE id = ?", (selected_subject_id,)).fetchone()
        if selected_subject:
            # Fetch students matching subject's department and semester (or all
            # students if semester/dept not restricted)
            students_for_attendance = conn.execute(
                "SELECT * FROM students WHERE department = ? AND semester = ? ORDER BY roll_number",
                (selected_subject['department'], selected_subject['semester'])
            ).fetchall()

            # If no students match exact dept/semester, fallback to all
            # students in that department
            if not students_for_attendance:
                students_for_attendance = conn.execute(
                    "SELECT * FROM students WHERE department = ? ORDER BY roll_number",
                    (selected_subject['department'],)
                ).fetchall()

            # Fetch existing attendance if already marked for this subject and
            # date
            existing_records = conn.execute(
                "SELECT student_id, status, remarks FROM attendance WHERE subject_id = ? AND attendance_date = ?",
                (selected_subject_id, selected_date)
            ).fetchall()
            for r in existing_records:
                existing_attendance_map[r['student_id']] = {
                    'status': r['status'], 'remarks': r['remarks']}

    conn.close()

    return render_template(
        'mark_attendance.html',
        subjects=subjects_list,
        selected_subject_id=selected_subject_id,
        selected_subject=selected_subject,
        selected_date=selected_date,
        students=students_for_attendance,
        existing_attendance=existing_attendance_map
    )


# ==========================================
# ATTENDANCE REPORTS & PERCENTAGE CALCULATION
# ==========================================

@app.route('/attendance/report')
@login_required
def attendance_report():
    """
    Detailed Attendance Report:
    View attendance history, filter by subject, date, or student name/roll.
    Displays calculated percentage per student per subject.
    """
    conn = database.get_db_connection()

    subject_filter = request.args.get('subject_id', type=int)
    date_filter = request.args.get('date', '').strip()
    student_search = request.args.get('search', '').strip()

    # Query for individual attendance logs
    sql = """
        SELECT
            a.id,
            a.attendance_date,
            a.status,
            a.remarks,
            s.roll_number,
            s.name AS student_name,
            s.department,
            sub.subject_code,
            sub.subject_name
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN subjects sub ON a.subject_id = sub.id
        WHERE 1=1
    """
    params = []

    if subject_filter:
        sql += " AND a.subject_id = ?"
        params.append(subject_filter)

    if date_filter:
        sql += " AND a.attendance_date = ?"
        params.append(date_filter)

    if student_search:
        sql += " AND (s.name LIKE ? OR s.roll_number LIKE ?)"
        term = f"%{student_search}%"
        params.extend([term, term])

    sql += " ORDER BY a.attendance_date DESC, s.roll_number ASC"
    records = conn.execute(sql, params).fetchall()

    # Query for summary percentages per student (subject-wise or overall)
    summary_sql = """
        SELECT
            s.id AS student_id,
            s.roll_number,
            s.name AS student_name,
            sub.subject_code,
            sub.subject_name,
            COUNT(a.id) AS total_classes,
            SUM(CASE WHEN a.status IN ('Present', 'Late') THEN 1 ELSE 0 END) AS attended_classes,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_classes
        FROM students s
        CROSS JOIN subjects sub
        LEFT JOIN attendance a ON s.id = a.student_id AND sub.id = a.subject_id
    """
    summary_params = []
    if subject_filter:
        summary_sql += " WHERE sub.id = ?"
        summary_params.append(subject_filter)

    summary_sql += " GROUP BY s.id, sub.id HAVING total_classes > 0 ORDER BY s.roll_number, sub.subject_code"
    summaries = conn.execute(summary_sql, summary_params).fetchall()

    calculated_summaries = []
    for row in summaries:
        tot = row['total_classes']
        att = row['attended_classes']
        pct = round((att / tot * 100), 1) if tot > 0 else 0.0
        calculated_summaries.append({
            'roll_number': row['roll_number'],
            'student_name': row['student_name'],
            'subject_code': row['subject_code'],
            'subject_name': row['subject_name'],
            'total_classes': tot,
            'attended_classes': att,
            'absent_classes': row['absent_classes'],
            'percentage': pct
        })

    subjects_list = conn.execute(
        "SELECT * FROM subjects ORDER BY subject_code").fetchall()
    conn.close()

    return render_template(
        'attendance_report.html',
        records=records,
        summaries=calculated_summaries,
        subjects=subjects_list,
        selected_subject_id=subject_filter,
        selected_date=date_filter,
        search_query=student_search
    )


@app.route('/attendance/low-attendance')
@login_required
def low_attendance():
    """
    Low Attendance Warning View (< 75%):
    Filters all students whose overall attendance percentage is strictly below 75%.
    Calculates exact deficit classes needed to reach 75% threshold.
    """
    conn = database.get_db_connection()

    query = """
        SELECT
            s.id,
            s.roll_number,
            s.name,
            s.email,
            s.department,
            s.semester,
            COUNT(a.id) AS total_classes,
            SUM(CASE WHEN a.status IN ('Present', 'Late') THEN 1 ELSE 0 END) AS attended_classes,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_classes
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id
        GROUP BY s.id
        HAVING total_classes > 0
    """
    stats = conn.execute(query).fetchall()

    defaulters = []
    for s in stats:
        tot = s['total_classes']
        att = s['attended_classes']
        pct = round((att / tot * 100), 1) if tot > 0 else 100.0

        if pct < 75.0:
            # Classes needed to reach 75% = ceil(0.75 * total - attended)
            needed = max(0, int((0.75 * tot) - att + 0.99))
            defaulters.append({
                'id': s['id'],
                'roll_number': s['roll_number'],
                'name': s['name'],
                'email': s['email'],
                'department': s['department'],
                'semester': s['semester'],
                'total_classes': tot,
                'attended_classes': att,
                'absent_classes': s['absent_classes'],
                'percentage': pct,
                'needed_classes': needed
            })

    conn.close()
    return render_template('low_attendance.html', defaulters=defaulters)


# ==========================================
# APPLICATION ENTRYPOINT
# ==========================================

if __name__ == '__main__':
    database.init_db()
    print("=" * 60)
    print(" Student Attendance Management System running on http://127.0.0.1:5000")
    print(" Admin Credentials -> Username: admin | Password: admin123")
    print("=" * 60)
    app.run(debug=True, port=5000)
