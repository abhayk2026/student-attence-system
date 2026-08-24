"""
Database Module for Student Attendance Management System
Handles SQLite database connection, initialization, schema setup, and sample data seeding.
"""

import os
import sqlite3
from werkzeug.security import generate_password_hash

# Database file name
DATABASE_NAME = 'attendance.db'


def get_db_connection():
    """
    Establishes and returns a connection to the SQLite database.
    Row factory is configured to sqlite3.Row so query results can be accessed by column name.
    Foreign key constraints are explicitly enabled for data integrity.
    """
    db_path = os.path.join(os.path.dirname(__file__), DATABASE_NAME)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """
    Initializes database tables using schema.sql and populates initial sample data if empty.
    Useful for quick demonstration and viva testing.
    """
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    conn = get_db_connection()

    with open(schema_path, mode='r', encoding='utf-8') as f:
        conn.executescript(f.read())

    cursor = conn.cursor()

    # 1. Create Default Admin User (username: admin, password: admin123)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_password = generate_password_hash('admin123')
        cursor.execute(
            "INSERT INTO users (username, password, full_name) VALUES (?, ?, ?)",
            ('admin', admin_password, 'System Administrator')
        )
        print("Default admin created: admin / admin123")

    # 2. Seed Sample Students
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        sample_students = [
            ('CS202401',
             'Aarav Sharma',
             'aarav.sharma@example.com',
             'Computer Science',
             6),
            ('CS202402',
             'Priya Patel',
             'priya.patel@example.com',
             'Computer Science',
             6),
            ('CS202403',
             'Rohan Gupta',
             'rohan.gupta@example.com',
             'Computer Science',
             6),
            ('CS202404',
             'Ananya Singh',
             'ananya.singh@example.com',
             'Computer Science',
             6),
            ('CS202405',
             'Vikram Verma',
             'vikram.verma@example.com',
             'Computer Science',
             6),
            ('IT202401',
             'Neha Reddy',
             'neha.reddy@example.com',
             'Information Technology',
             4),
        ]
        cursor.executemany(
            "INSERT INTO students (roll_number, name, email, department, semester) VALUES (?, ?, ?, ?, ?)",
            sample_students
        )
        print("Sample students seeded.")

    # 3. Seed Sample Subjects
    cursor.execute("SELECT COUNT(*) FROM subjects")
    if cursor.fetchone()[0] == 0:
        sample_subjects = [
            ('CS601', 'Database Management Systems', 'Computer Science', 6),
            ('CS602', 'Web Technologies', 'Computer Science', 6),
            ('CS603', 'Software Engineering', 'Computer Science', 6),
            ('IT401', 'Data Structures & Algorithms', 'Information Technology', 4),
        ]
        cursor.executemany(
            "INSERT INTO subjects (subject_code, subject_name, department, semester) VALUES (?, ?, ?, ?)",
            sample_subjects
        )
        print("Sample subjects seeded.")

    # 4. Seed Sample Attendance Records
    cursor.execute("SELECT COUNT(*) FROM attendance")
    if cursor.fetchone()[0] == 0:
        # Student IDs: 1 (Aarav), 2 (Priya), 3 (Rohan), 4 (Ananya), 5 (Vikram)
        # Subject ID 1: DBMS (CS601)
        # Subject ID 2: Web Tech (CS602)
        # Rohan Gupta (ID 3) will have < 75% attendance to demonstrate low
        # attendance warnings.
        attendance_records = [
            # Day 1 - DBMS
            (1, 1, '2026-08-01', 'Present', 'On time'),
            (2, 1, '2026-08-01', 'Present', 'On time'),
            (3, 1, '2026-08-01', 'Absent', 'Medical leave'),
            (4, 1, '2026-08-01', 'Present', 'On time'),
            (5, 1, '2026-08-01', 'Present', 'On time'),
            # Day 2 - DBMS
            (1, 1, '2026-08-02', 'Present', 'On time'),
            (2, 1, '2026-08-02', 'Present', 'On time'),
            (3, 1, '2026-08-02', 'Absent', 'Uninformed'),
            (4, 1, '2026-08-02', 'Present', 'On time'),
            (5, 1, '2026-08-02', 'Late', '15 mins late'),
            # Day 3 - DBMS
            (1, 1, '2026-08-03', 'Present', 'On time'),
            (2, 1, '2026-08-03', 'Present', 'On time'),
            (3, 1, '2026-08-03', 'Absent', 'Uninformed'),
            (4, 1, '2026-08-03', 'Present', 'On time'),
            (5, 1, '2026-08-03', 'Present', 'On time'),
            # Day 4 - DBMS
            (1, 1, '2026-08-04', 'Present', 'On time'),
            (2, 1, '2026-08-04', 'Present', 'On time'),
            (3, 1, '2026-08-04', 'Present', 'On time'),
            (4, 1, '2026-08-04', 'Present', 'On time'),
            (5, 1, '2026-08-04', 'Present', 'On time'),
            # Day 5 - Web Tech
            (1, 2, '2026-08-05', 'Present', 'On time'),
            (2, 2, '2026-08-05', 'Present', 'On time'),
            (3, 2, '2026-08-05', 'Absent', 'Personal'),
            (4, 2, '2026-08-05', 'Present', 'On time'),
            (5, 2, '2026-08-05', 'Present', 'On time'),
        ]
        cursor.executemany(
            "INSERT INTO attendance (student_id, subject_id, attendance_date, status, remarks) VALUES (?, ?, ?, ?, ?)",
            attendance_records
        )
        print("Sample attendance seeded.")

    conn.commit()
    conn.close()


if __name__ == '__main__':
    # Running database.py directly creates/resets the database file
    init_db()
    print("Database initialization complete.")
