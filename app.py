from flask import Flask, render_template, request, session, redirect, flash
from database import get_connection
from camera import capture_photo
from qr_generator import generate_qr
import os
import cv2
from datetime import datetime
import pandas as pd
from flask import send_file
from io import BytesIO

app = Flask(__name__)
app.secret_key = "college_management_system_secret_key"

# ---------------- HOME PAGES ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/About")
def about():
    return render_template("about.html")

@app.route("/BCA")
def bca():
    return render_template("bca.html")

@app.route("/BscIT")
def bsc_it():
    return render_template("Bsc.it.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

# ---------------- ADMIN LOGIN ----------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT admin_id FROM admin WHERE email=%s AND password=%s",
            (email, password),
        )
        admin = cursor.fetchone()
        conn.close()

        if admin:
            session["admin_id"] = admin[0]
            return redirect("/admin_dashboard")
        else:
            error = "Invalid email or password"

    return render_template("admin_login.html", error=error)

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect("/admin_login")
    return render_template("admin_dashboard.html")

# ---------------- ADD STUDENT ----------------
@app.route("/admin/add_student", methods=["GET", "POST"])
def admin_add_student():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()

    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    if request.method == "POST":
        name = request.form.get("name")
        roll = request.form.get("roll")
        address = request.form.get("address")
        password = request.form.get("password")
        course_id = request.form.get("course_id")
        dept_id = request.form.get("department_id")

        # 🔥 ADD THIS LINE
        admission_date = datetime.now().date()

        os.makedirs("static/images", exist_ok=True)
        os.makedirs("static/qr_codes", exist_ok=True)

        image_path = f"static/images/{roll}.jpg"
        capture_photo(image_path)

        qr_path = f"static/qr_codes/{roll}.png"
        generate_qr(roll, qr_path)

        cursor.execute(
            """
            INSERT INTO students
            (name, address, roll_no, password, photo, qr_code, course_id, department_id, admission_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (name, address, roll, password, image_path, qr_path, course_id, dept_id, admission_date),
        )

        conn.commit()
        conn.close()

        flash("Student added successfully", "success")
        return redirect("/admin/view_students")

    conn.close()
    return render_template(
        "add_student.html", departments=departments, courses=courses
    )

# ---------------- VIEW STUDENTS ----------------
@app.route("/admin/view_students")
def view_students():
    if "admin_id" not in session:
        return redirect("/admin_login")

    search = request.args.get("search")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if search:
        cursor.execute("""
        SELECT students.*, courses.course_name, departments.department_name
        FROM students
        JOIN courses ON students.course_id = courses.course_id
        JOIN departments ON students.department_id = departments.department_id
        WHERE students.roll_no LIKE %s OR students.name LIKE %s
        """, (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("""
        SELECT students.*, courses.course_name, departments.department_name
        FROM students
        JOIN courses ON students.course_id = courses.course_id
        JOIN departments ON students.department_id = departments.department_id
        """)

    students = cursor.fetchall()
    conn.close()

    return render_template("view_students.html", students=students)

# ---------------- EDIT STUDENT ----------------
@app.route("/admin/edit_student/<int:id>", methods=["GET", "POST"])
def edit_student(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM students WHERE student_id=%s", (id,))
    student = cursor.fetchone()

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()

    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    if request.method == "POST":
        name = request.form["name"]
        roll = request.form["roll"]
        address = request.form["address"]
        dept = request.form["department_id"]
        course = request.form["course_id"]

        cursor.execute("""
        UPDATE students
        SET name=%s, roll_no=%s, address=%s,
            department_id=%s, course_id=%s
        WHERE student_id=%s
        """, (name, roll, address, dept, course, id))

        conn.commit()
        conn.close()
        flash("Student updated", "success")
        return redirect("/admin/view_students")

    conn.close()
    return render_template(
        "edit_student.html",
        student=student,
        departments=departments,
        courses=courses
    )

# ---------------- DELETE STUDENT ----------------
@app.route("/admin/delete_student/<int:id>")
def delete_student(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM students WHERE student_id=%s", (id,))
    conn.commit()
    conn.close()

    flash("Student deleted", "danger")
    return redirect("/admin/view_students")

# ---------------- ADD FACULTY ----------------
@app.route("/admin/add_faculty", methods=["GET", "POST"])
def admin_add_faculty():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        dept_id = request.form["department_id"]

        cursor.execute(
            "INSERT INTO faculty (name, email, password, department_id) VALUES (%s, %s, %s, %s)",
            (name, email, password, dept_id),
        )
        conn.commit()
        conn.close()
        flash("Faculty added successfully", "success")
        return redirect("/admin/view_faculty")

    conn.close()
    return render_template("add_faculty.html", departments=departments)

# ---------------- VIEW FACULTY ----------------
@app.route("/admin/view_faculty")
def view_faculty():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT faculty.*, departments.department_name
    FROM faculty
    JOIN departments
    ON faculty.department_id = departments.department_id
    """)

    faculty = cursor.fetchall()
    conn.close()

    return render_template("view_faculty.html", faculty=faculty)

# ---------------- EDIT FACULTY ----------------
@app.route("/admin/edit_faculty/<int:id>", methods=["GET", "POST"])
def edit_faculty(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM faculty WHERE faculty_id=%s", (id,))
    faculty = cursor.fetchone()

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        dept = request.form["department_id"]

        cursor.execute("""
        UPDATE faculty
        SET name=%s, email=%s, department_id=%s
        WHERE faculty_id=%s
        """, (name, email, dept, id))

        conn.commit()
        conn.close()
        flash("Faculty updated", "success")
        return redirect("/admin/view_faculty")

    conn.close()
    return render_template(
        "edit_faculty.html",
        faculty=faculty,
        departments=departments
    )

# ---------------- DELETE FACULTY ----------------
@app.route("/admin/delete_faculty/<int:id>")
def delete_faculty(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM faculty WHERE faculty_id=%s", (id,))
    conn.commit()
    conn.close()

    flash("Faculty deleted", "danger")
    return redirect("/admin/view_faculty")

# ---------------- STUDENT LOGIN ----------------
@app.route("/student_login", methods=["POST"])
def student_login():
    roll_no = request.form.get("roll_no")
    password = request.form.get("password")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM students WHERE roll_no=%s AND password=%s",
        (roll_no, password),
    )
    student = cursor.fetchone()
    conn.close()

    if student:
        session["student_id"] = student["student_id"]
        return redirect("/student_dashboard")
    else:
        flash("Invalid roll number or password", "danger")
        return redirect("/")

# ---------------- STUDENT DASHBOARD ----------------
@app.route("/student_dashboard")
def student_dashboard():
    if "student_id" not in session:
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    student_id = session["student_id"]

    # 👤 Profile
    cursor.execute("""
    SELECT students.*, courses.course_name, departments.department_name
    FROM students
    JOIN courses ON students.course_id = courses.course_id
    JOIN departments ON students.department_id = departments.department_id
    WHERE student_id=%s
    """, (student_id,))
    student = cursor.fetchone()

    # 📊 Attendance
    cursor.execute("""
    SELECT 
        subjects.subject_name,
        attendance.date,
        attendance.status,
        faculty.name AS faculty_name
    FROM attendance
    JOIN subjects ON attendance.subject_id = subjects.subject_id
    JOIN faculty_subjects fs ON fs.subject_id = subjects.subject_id
    JOIN faculty ON fs.faculty_id = faculty.faculty_id
    WHERE attendance.student_id=%s
    ORDER BY attendance.date DESC
    """, (student_id,))
    attendance = cursor.fetchall()

    # 🔔 Notices
    cursor.execute("""
    SELECT COUNT(*) AS total
    FROM notices
    WHERE target_type IN ('ALL','STUDENT')
    """)
    notice_count = cursor.fetchone()["total"]

    cursor.execute("""
    SELECT * FROM notices
    WHERE target_type IN ('ALL','STUDENT')
    ORDER BY created_on DESC
    """)
    notices = cursor.fetchall()

    # 💰 Fee Details
    cursor.execute("""
    SELECT 
        f.total_fee,
        COALESCE(SUM(fp.amount_paid), 0) AS paid_amount
    FROM students s
    JOIN fees f ON s.course_id = f.course_id
    LEFT JOIN fee_payments fp ON s.student_id = fp.student_id
    WHERE s.student_id = %s
    GROUP BY f.total_fee
    """, (student_id,))

    fee_data = cursor.fetchone()

    if fee_data:
        total_fee = fee_data["total_fee"]
        paid = fee_data["paid_amount"]
        pending = total_fee - paid
    else:
        total_fee = 0
        paid = 0
        pending = 0

    # 💳 Payment History
    cursor.execute("""
    SELECT amount_paid, payment_date
    FROM fee_payments
    WHERE student_id=%s
    ORDER BY payment_date DESC
    """, (student_id,))
    payments = cursor.fetchall()

    conn.close()

    return render_template(
        "student_dashboard.html",
        student=student,
        attendance=attendance,
        notice_count=notice_count,
        notices=notices,
        total_fee=total_fee,
        paid=paid,
        pending=pending,
        payments=payments
    )

# ---------------- FACULTY LOGIN ----------------
@app.route("/faculty_login", methods=["GET", "POST"])
def faculty_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM faculty WHERE email=%s AND password=%s",
            (email, password),
        )
        faculty = cursor.fetchone()
        conn.close()

        if faculty:
            session["faculty_id"] = faculty["faculty_id"]
            return redirect("/faculty_dashboard")
        else:
            flash("Invalid email or password", "danger")

    return render_template("index.html")

# ---------------- FACULTY DASHBOARD ----------------
@app.route("/faculty_dashboard")
def faculty_dashboard():
    if "faculty_id" not in session:
        return redirect("/faculty_login")

    faculty_id = session["faculty_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # faculty profile
    cursor.execute("""
    SELECT faculty.*, departments.department_name
    FROM faculty
    JOIN departments ON faculty.department_id = departments.department_id
    WHERE faculty_id=%s
    """, (faculty_id,))
    faculty = cursor.fetchone()

    # subjects
    cursor.execute("""
    SELECT 
        subjects.subject_id,
        subjects.subject_name, 
        courses.course_name
    FROM faculty_subjects fs
    JOIN subjects ON fs.subject_id = subjects.subject_id
    JOIN courses ON subjects.course_id = courses.course_id
    WHERE fs.faculty_id=%s
    """, (faculty_id,))
    subjects = cursor.fetchall()

    # 🔔 notice count
    cursor.execute("""
    SELECT COUNT(*) AS total
    FROM notices
    WHERE target_type IN ('ALL','FACULTY')
    """)
    notice_count = cursor.fetchone()["total"]

    # NOTICE DATA
    cursor.execute("""
    SELECT * FROM notices
    WHERE target_type IN ('ALL','FACULTY')
    ORDER BY created_on DESC
    """)
    notices = cursor.fetchall()

    conn.close()

    return render_template(
        "faculty_dashboard.html",
        faculty=faculty,
        subjects=subjects,
        notice_count=notice_count,
        notices=notices 
    )

# ---------------- SELECT SUBJECT ----------------
@app.route("/select_subject", methods=["POST"])
def select_subject():


    subject_id = request.form.get("subject_id")

    if not subject_id:
        flash("Please select a subject first", "warning")
        return redirect("/faculty_dashboard")

    session["subject_id"] = int(subject_id)

    return redirect("/mark_attendance")

# ---------------- START ATTENDANCE ----------------
@app.route("/start_attendance", methods=["POST"])
def start_attendance():

    if "faculty_id" not in session:
        return redirect("/faculty_login")

    subject_id = request.form.get("subject_id")

    if not subject_id:
        flash("Please select subject", "warning")
        return redirect("/faculty_dashboard")

    subject_id = int(subject_id)
    session["subject_id"] = subject_id

    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().date()

    # 🔥 STEP 1: sabko ABSENT mark karo
    cursor.execute("""
    SELECT student_id FROM students
    WHERE course_id = (
        SELECT course_id FROM subjects WHERE subject_id=%s
    )
    """, (subject_id,))

    students = cursor.fetchall()

    for s in students:
        try:
            cursor.execute("""
            INSERT INTO attendance (student_id, subject_id, date, status, method)
            VALUES (%s,%s,%s,'Absent','Manual')
            """, (s[0], subject_id, today))
        except:
            pass  # already exist ignore

    conn.commit()
    conn.close()

    # 🔥 STEP 2: camera start
    return redirect("/mark_attendance")

@app.route("/mark_attendance")
def mark_attendance():

    if "faculty_id" not in session or "subject_id" not in session:
        return redirect("/faculty_dashboard")

    subject_id = session["subject_id"]

    detector = cv2.QRCodeDetector()
    cap = cv2.VideoCapture(0)
    now = datetime.now()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        data, bbox, _ = detector.detectAndDecode(frame)

        if bbox is not None and data:
            roll_no = data.strip()

            conn = get_connection()
            cursor = conn.cursor()

            # ✅ student find
            cursor.execute(
                "SELECT student_id FROM students WHERE roll_no=%s", (roll_no,)
            )
            result = cursor.fetchone()

            if not result:
                conn.close()
                cap.release()
                cv2.destroyAllWindows()
                flash("Student not registered", "danger")
                return redirect("/faculty_dashboard")

            student_id = result[0]

            # ✅ check current status
            cursor.execute("""
            SELECT status FROM attendance
            WHERE student_id=%s AND subject_id=%s AND date=%s
            """, (student_id, subject_id, now.date()))

            record = cursor.fetchone()

            if not record:
                conn.close()
                cap.release()
                cv2.destroyAllWindows()
                flash("Attendance not initialized", "warning")
                return redirect("/faculty_dashboard")

            if record[0] == "Present":
                conn.close()
                cap.release()
                cv2.destroyAllWindows()
                flash("Already marked!", "warning")
                return redirect("/faculty_dashboard")

            # ✅ update only once
            cursor.execute("""
            UPDATE attendance
            SET status='Present', method='QR'
            WHERE student_id=%s AND subject_id=%s AND date=%s
            """, (student_id, subject_id, now.date()))

            conn.commit()
            conn.close()

            cap.release()
            cv2.destroyAllWindows()
            flash("Attendance marked successfully", "success")
            return redirect("/faculty_dashboard")

        cv2.imshow("Scan QR - Press ESC to exit", frame)

        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    flash("Camera closed", "info")
    return redirect("/faculty_dashboard")

# ----------------- Attendance Records ----------------

@app.route("/faculty/attendance_records")
def faculty_attendance_records():
    if "faculty_id" not in session:
        return redirect("/faculty_login")

    faculty_id = session["faculty_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT a.date, s.roll_no, s.name AS student_name,
           sub.subject_name, c.course_name
    FROM attendance a
    JOIN students s ON a.student_id = s.student_id
    JOIN subjects sub ON a.subject_id = sub.subject_id
    JOIN courses c ON sub.course_id = c.course_id
    WHERE sub.subject_id IN (
        SELECT subject_id FROM faculty_subjects WHERE faculty_id=%s
    )
    ORDER BY a.date DESC
    """, (faculty_id,))

    records = cursor.fetchall()
    conn.close()

    return render_template("attendance_records.html", records=records)

# ---------------- ADD DEPARTMENT ----------------

@app.route("/admin/add_department", methods=["GET", "POST"])
def add_department():
    if "admin_id" not in session:
        return redirect("/admin_login")

    if request.method == "POST":
        name = request.form["department_name"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO departments (department_name) VALUES (%s)", (name,)
        )
        conn.commit()
        conn.close()

        flash("Department added", "success")
        return redirect("/admin/view_departments")

    return render_template("add_department.html")

# ---------------- VIEW DEPARTMENTS ----------------

@app.route("/admin/view_departments")
def view_departments():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()
    conn.close()

    return render_template("view_departments.html", departments=departments)

# ---------------- EDIT DEPARTMENT ----------------

@app.route("/admin/edit_department/<int:id>", methods=["GET", "POST"])
def edit_department(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM departments WHERE department_id=%s", (id,))
    department = cursor.fetchone()

    if request.method == "POST":
        name = request.form["department_name"]

        cursor.execute("""
        UPDATE departments
        SET department_name=%s
        WHERE department_id=%s
        """, (name, id))

        conn.commit()
        conn.close()
        return redirect("/admin/view_departments")

    conn.close()
    return render_template("edit_department.html", department=department)

# ---------------- DELETE DEPARTMENT ----------------

@app.route("/admin/delete_department/<int:id>")
def delete_department(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM departments WHERE department_id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin/view_departments")

# ---------------- ADD COURSE ----------------

@app.route("/admin/add_course", methods=["GET", "POST"])
def add_course():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()

    if request.method == "POST":
        name = request.form["course_name"]
        duration = request.form["duration"]
        fee = request.form["fee"]
        dept_id = request.form["department_id"]

        cursor.execute(
            """
            INSERT INTO courses (course_name, duration_years, total_fee, department_id)
            VALUES (%s, %s, %s, %s)
            """,
            (name, duration, fee, dept_id),
        )

        conn.commit()
        conn.close()

        flash("Course added", "success")
        return redirect("/admin/view_courses")

    conn.close()
    return render_template("add_course.html", departments=departments)

# ---------------- VIEW COURSES ----------------

@app.route("/admin/view_courses")
def view_courses():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT courses.*, departments.department_name
    FROM courses
    JOIN departments
    ON courses.department_id = departments.department_id
    """)

    courses = cursor.fetchall()
    conn.close()

    return render_template("view_courses.html", courses=courses)

# ---------------- EDIT COURSE ----------------

@app.route("/admin/edit_course/<int:id>", methods=["GET", "POST"])
def edit_course(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM courses WHERE course_id=%s", (id,))
    course = cursor.fetchone()

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()

    if request.method == "POST":
        name = request.form["course_name"]
        duration = request.form["duration"]
        fee = request.form["fee"]
        dept = request.form["department_id"]

        cursor.execute("""
        UPDATE courses
        SET course_name=%s, duration_years=%s,
            total_fee=%s, department_id=%s
        WHERE course_id=%s
        """, (name, duration, fee, dept, id))

        conn.commit()
        conn.close()
        return redirect("/admin/view_courses")

    conn.close()
    return render_template("edit_course.html", course=course, departments=departments)

# ---------------- DELETE COURSE ----------------

@app.route("/admin/delete_course/<int:id>")
def delete_course(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM courses WHERE course_id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin/view_courses")

# ---------------- ADD SUBJECT ----------------

@app.route("/admin/add_subject", methods=["GET", "POST"])
def add_subject():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    if request.method == "POST":
        name = request.form["subject_name"]
        semester = request.form["semester"]
        course_id = request.form["course_id"]

        cursor.execute("""
        INSERT INTO subjects(subject_name, semester, course_id)
        VALUES(%s, %s, %s)
        """, (name, semester, course_id))

        conn.commit()
        conn.close()
        return redirect("/admin/view_subjects")

    conn.close()
    return render_template("add_subject.html", courses=courses)

# ---------------- VIEW SUBJECTS ----------------

@app.route("/admin/view_subjects")
def view_subjects():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT subjects.*, courses.course_name
    FROM subjects
    JOIN courses ON subjects.course_id = courses.course_id
    """)

    subjects = cursor.fetchall()
    conn.close()

    return render_template("view_subjects.html", subjects=subjects)

# ---------------- EDIT SUBJECT ----------------

@app.route("/admin/edit_subject/<int:id>", methods=["GET", "POST"])
def edit_subject(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM subjects WHERE subject_id=%s", (id,))
    subject = cursor.fetchone()

    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    if request.method == "POST":
        name = request.form["subject_name"]
        semester = request.form["semester"]
        course_id = request.form["course_id"]

        cursor.execute("""
        UPDATE subjects
        SET subject_name=%s, semester=%s, course_id=%s
        WHERE subject_id=%s
        """, (name, semester, course_id, id))

        conn.commit()
        conn.close()
        return redirect("/admin/view_subjects")

    conn.close()
    return render_template("edit_subject.html", subject=subject, courses=courses)

# ---------------- DELETE SUBJECT ----------------

@app.route("/admin/delete_subject/<int:id>")
def delete_subject(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM subjects WHERE subject_id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin/view_subjects")

# ----------------- Assign Faculty to Subject ----------------

@app.route("/admin/assign_subject", methods=["GET", "POST"])
def assign_subject():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # dropdown data
    cursor.execute("SELECT faculty_id, name FROM faculty")
    faculty = cursor.fetchall()

    cursor.execute("SELECT subject_id, subject_name FROM subjects")
    subjects = cursor.fetchall()

    if request.method == "POST":
        faculty_id = request.form["faculty_id"]
        subject_id = request.form["subject_id"]

        try:
            cursor.execute("""
            INSERT INTO faculty_subjects (faculty_id, subject_id)
            VALUES (%s, %s)
            """, (faculty_id, subject_id))
            conn.commit()
        except:
            pass  # duplicate assign ignore

        conn.close()
        return redirect("/admin/view_assigned_subjects")

    conn.close()
    return render_template(
        "assign_subject.html",
        faculty=faculty,
        subjects=subjects
    )

# ----------------- View Assigned Subjects ----------------

@app.route("/admin/view_assigned_subjects")
def view_assigned_subjects():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT fs.id,
           faculty.name AS faculty_name,
           subjects.subject_name
    FROM faculty_subjects fs
    JOIN faculty ON fs.faculty_id = faculty.faculty_id
    JOIN subjects ON fs.subject_id = subjects.subject_id
    """)

    data = cursor.fetchall()
    conn.close()

    return render_template("view_assigned_subjects.html", data=data)

# ----------------- Edit Assigned Subject ----------------

@app.route("/admin/edit_assignment/<int:id>", methods=["GET", "POST"])
def edit_assignment(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM faculty_subjects WHERE id=%s", (id,))
    assignment = cursor.fetchone()

    cursor.execute("SELECT faculty_id, name FROM faculty")
    faculty = cursor.fetchall()

    cursor.execute("SELECT subject_id, subject_name FROM subjects")
    subjects = cursor.fetchall()

    if request.method == "POST":
        faculty_id = request.form["faculty_id"]
        subject_id = request.form["subject_id"]

        cursor.execute("""
        UPDATE faculty_subjects
        SET faculty_id=%s, subject_id=%s
        WHERE id=%s
        """, (faculty_id, subject_id, id))

        conn.commit()
        conn.close()
        return redirect("/admin/view_assigned_subjects")

    conn.close()
    return render_template(
        "edit_assignment.html",
        assignment=assignment,
        faculty=faculty,
        subjects=subjects
    )

# ----------------- Delete Assigned Subject ----------------

@app.route("/admin/delete_assignment/<int:id>")
def delete_assignment(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM faculty_subjects WHERE id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin/view_assigned_subjects")

# ---------------- Add Notice ----------------

@app.route("/admin/add_notice", methods=["GET", "POST"])
def add_notice():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # department dropdown ke liye
    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()

    if request.method == "POST":
        title = request.form["title"]
        message = request.form["message"]
        target_type = request.form["target_type"]
        department_id = request.form.get("department_id")

        cursor.execute("""
        INSERT INTO notices (title, message, target_type, department_id)
        VALUES (%s, %s, %s, %s)
        """, (title, message, target_type, department_id or None))

        conn.commit()
        conn.close()
        return redirect("/admin/view_notices")

    conn.close()
    return render_template("add_notice.html", departments=departments)

# ---------------- View Notices ----------------

@app.route("/admin/view_notices")
def view_notices():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT notices.*, departments.department_name
    FROM notices
    LEFT JOIN departments
    ON notices.department_id = departments.department_id
    ORDER BY created_on DESC
    """)

    notices = cursor.fetchall()
    conn.close()

    return render_template("view_notices.html", notices=notices)

# ----------------- Delete Notice ----------------

@app.route("/admin/delete_notice/<int:id>")
def delete_notice(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notices WHERE notice_id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin/view_notices")

# ----------------- Set Course Fee ----------------
@app.route("/admin/set_fee", methods=["GET", "POST"])
def set_fee():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    if request.method == "POST":
        course_id = request.form["course_id"]
        total_fee = request.form["total_fee"]

        cursor.execute("""
        INSERT INTO fees (course_id, total_fee)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE total_fee=%s
        """, (course_id, total_fee, total_fee))

        conn.commit()
        conn.close()

        flash("Fee set successfully", "success")
        return redirect("/admin/set_fee")

    conn.close()
    return render_template("set_fee.html", courses=courses)

# ----------------- Student Fees ----------------
@app.route("/admin/student_fees")
def student_fees():
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT 
        s.student_id,
        s.name,
        s.roll_no,
        c.course_name,
        f.total_fee,
        IFNULL(SUM(fp.amount_paid),0) AS paid,
        (f.total_fee - IFNULL(SUM(fp.amount_paid),0)) AS pending
    FROM students s
    JOIN courses c ON s.course_id = c.course_id
    JOIN fees f ON c.course_id = f.course_id
    LEFT JOIN fee_payments fp ON s.student_id = fp.student_id
    GROUP BY s.student_id
    """)

    students = cursor.fetchall()
    conn.close()

    return render_template("student_fees.html", students=students)

# ----------------- Add Fee Payment ----------------
@app.route("/admin/add_payment/<int:student_id>", methods=["GET", "POST"])
def add_payment(student_id):

    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM students WHERE student_id=%s", (student_id,))
    student = cursor.fetchone()

    cursor.execute("""
    SELECT 
        f.total_fee,
        IFNULL(SUM(fp.amount_paid),0) AS paid
    FROM students s
    JOIN fees f ON s.course_id = f.course_id
    LEFT JOIN fee_payments fp ON s.student_id = fp.student_id
    WHERE s.student_id=%s
    """, (student_id,))

    fee = cursor.fetchone()
    pending = fee["total_fee"] - fee["paid"]

    if request.method == "POST":
        amount = int(request.form["amount"])

        if amount > pending:
            flash("Amount exceeds pending", "danger")
            return redirect(request.url)

        cursor.execute("""
        INSERT INTO fee_payments (student_id, amount_paid, payment_date)
        VALUES (%s,%s,CURDATE())
        """, (student_id, amount))

        conn.commit()
        conn.close()

        flash("Payment added", "success")
        return redirect("/admin/student_fees")

    conn.close()
    return render_template("add_payment.html", student=student, fee=fee, pending=pending)

# ----------------- Attendance Report ----------------
@app.route("/admin/attendance_report")
def attendance_report():

    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()

    query = """
    SELECT 
        s.name AS student_name,
        s.roll_no,
        sub.subject_name,
        c.course_name,
        a.date,
        a.status
    FROM attendance a
    JOIN students s ON a.student_id = s.student_id
    JOIN subjects sub ON a.subject_id = sub.subject_id
    JOIN courses c ON sub.course_id = c.course_id
    ORDER BY a.date DESC
    """

    df = pd.read_sql(query, conn)
    conn.close()

    # Excel file memory me banana
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return send_file(
        output,
        download_name="attendance_report.xlsx",
        as_attachment=True
    )

# ---------------- Student Report ----------------
@app.route("/admin/student_report")
def student_report():

    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()

    query = """
    SELECT 
        s.name AS student_name,
        s.roll_no,
        s.address,
        d.department_name,
        c.course_name,
        s.admission_date
    FROM students s
    JOIN departments d ON s.department_id = d.department_id
    JOIN courses c ON s.course_id = c.course_id
    ORDER BY s.name
    """

    df = pd.read_sql(query, conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return send_file(
        output,
        download_name="student_report.xlsx",
        as_attachment=True
    )
# ---------------- Fee Report ----------------
@app.route("/admin/fee_report")
def fee_report():

    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()

    query = """
    SELECT 
        s.name AS student_name,
        s.roll_no,
        c.course_name,
        f.total_fee,
        IFNULL(SUM(fp.amount_paid), 0) AS paid_amount,
        (f.total_fee - IFNULL(SUM(fp.amount_paid), 0)) AS pending_amount
    FROM students s
    JOIN courses c ON s.course_id = c.course_id
    JOIN fees f ON f.course_id = c.course_id
    LEFT JOIN fee_payments fp ON fp.student_id = s.student_id
    GROUP BY s.student_id, f.total_fee
    ORDER BY s.name
    """

    df = pd.read_sql(query, conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return send_file(
        output,
        download_name="fee_report.xlsx",
        as_attachment=True
    )
# ---------------- Faculty Report ----------------
@app.route("/admin/faculty_report")
def faculty_report():

    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()

    query = """
    SELECT 
        f.name AS faculty_name,
        f.email,
        d.department_name,
        c.course_name,
        s.subject_name
    FROM faculty f
    JOIN departments d ON f.department_id = d.department_id
    LEFT JOIN faculty_subjects fs ON fs.faculty_id = f.faculty_id
    LEFT JOIN subjects s ON fs.subject_id = s.subject_id
    LEFT JOIN courses c ON s.course_id = c.course_id
    ORDER BY f.name
    """

    df = pd.read_sql(query, conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return send_file(
        output,
        download_name="faculty_report.xlsx",
        as_attachment=True
    )

# ---------------- Course & Subject Report ----------------
@app.route("/admin/course_subject_report")
def course_subject_report():

    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()

    query = """
    SELECT 
        d.department_name,
        c.course_name,
        s.subject_name
    FROM courses c
    JOIN departments d ON c.department_id = d.department_id
    LEFT JOIN subjects s ON s.course_id = c.course_id
    ORDER BY d.department_name, c.course_name
    """

    df = pd.read_sql(query, conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return send_file(
        output,
        download_name="course_subject_report.xlsx",
        as_attachment=True
    )

# ---------------- Notice Report ----------------
@app.route("/admin/notice_report")
def notice_report():

    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()

    query = """
    SELECT 
        n.title,
        n.message,
        n.target_type,
        IFNULL(d.department_name, 'ALL') AS department,
        n.created_on
    FROM notices n
    LEFT JOIN departments d ON n.department_id = d.department_id
    ORDER BY n.created_on DESC
    """

    df = pd.read_sql(query, conn)
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return send_file(
        output,
        download_name="notice_report.xlsx",
        as_attachment=True
    )

# ----------------- Daily Report ----------------
@app.route("/admin/daily_report")
def daily_report():

    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 📅 Today date
    today = datetime.now().date()

    # 📊 Attendance Summary
    cursor.execute("""
        SELECT 
            COUNT(*) AS total_attendance,
            SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present_count,
            SUM(CASE WHEN status='Absent' THEN 1 ELSE 0 END) AS absent_count
        FROM attendance
        WHERE date=%s
    """, (today,))
    attendance_data = cursor.fetchone()

    # 💰 Fee Collection Today
    cursor.execute("""
        SELECT 
            IFNULL(SUM(amount_paid), 0) AS total_collection
        FROM fee_payments
        WHERE DATE(payment_date)=%s
    """, (today,))
    fee_data = cursor.fetchone()

    conn.close()

    # 📄 DataFrame banana
    data = [{
        "Date": today,
        "Total Attendance": attendance_data["total_attendance"] or 0,
        "Present": attendance_data["present_count"] or 0,
        "Absent": attendance_data["absent_count"] or 0,
        "Total Fee Collection": fee_data["total_collection"] or 0
    }]

    df = pd.DataFrame(data)

    # Excel generate
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return send_file(
        output,
        download_name="daily_activity_report.xlsx",
        as_attachment=True
    )

# ---------------- faculty attendance report ----------------
@app.route("/faculty/attendance_report")
def faculty_attendance_report():

    if "faculty_id" not in session:
        return redirect("/faculty_login")

    faculty_id = session["faculty_id"]

    conn = get_connection()

    query = """
    SELECT 
        st.name AS student_name,
        st.roll_no,
        sub.subject_name,
        a.date,
        a.status
    FROM attendance a
    JOIN students st ON a.student_id = st.student_id
    JOIN subjects sub ON a.subject_id = sub.subject_id
    JOIN faculty_subjects fs ON fs.subject_id = sub.subject_id
    WHERE fs.faculty_id = %s
    ORDER BY a.date DESC
    """

    df = pd.read_sql(query, conn, params=(faculty_id,))
    conn.close()

    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return send_file(
        output,
        download_name="faculty_attendance_report.xlsx",
        as_attachment=True
    )

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)