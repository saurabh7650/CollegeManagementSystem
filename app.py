from flask import Flask, render_template, request, session, redirect
from database import get_connection
from camera import capture_photo
import os
from qr_generator import generate_qr
from datetime import datetime
from flask import flash, redirect, render_template, session




app = Flask(__name__)

app = Flask(__name__)
app.secret_key = "college_management_system_secret_key"


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

# Admin panel Routes Testing

@app.route("/admin_login", methods=["GET","POST"])
def admin_login():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT admin_id FROM admin
            WHERE email=%s AND password=%s
        """, (email,password))

        admin = cursor.fetchone()
        conn.close()

        if admin:
            session["admin_id"] = admin[0]
            return redirect("/admin_dashboard")
        else:
            error = "Invalid email or password"

    return render_template("admin_login.html", error=error)

@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect("/admin_login")

    return render_template("admin_dashboard.html")

@app.route("/admin/add_student", methods=["GET", "POST"])
def admin_add_student():
    if "admin_id" not in session:
        return redirect("/admin_login")

    if request.method == "POST":
        name = request.form.get("name")
        roll = request.form.get("roll")
        email = request.form.get("email")
        password = request.form.get("password")

        # 📸 Capture photo
        image_path = f"static/images/{roll}.jpg"
        capture_photo(image_path)

        # 🔳 Generate QR
        qr_path = f"static/qr_codes/{roll}.png"
        generate_qr(roll, qr_path)

        # 💾 Insert into DB
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO students 
            (name, roll_no, email, password, photo, qr_code)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, roll, email, password, image_path, qr_path))

        conn.commit()
        conn.close()

        return redirect("/admin/view_students")

    return render_template("add_student.html")


@app.route("/admin/view_students")
def view_students():
    if "admin_id" not in session:
        return redirect("/admin_login")

    search = request.args.get("search")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if search:
        cursor.execute("""
            SELECT * FROM students
            WHERE roll_no LIKE %s OR name LIKE %s
        """, (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM students")

    students = cursor.fetchall()
    conn.close()

    return render_template("view_students.html", students=students, search=search)



@app.route("/admin/edit_student/<int:id>", methods=["GET","POST"])
def edit_student(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute("""
            UPDATE students SET name=%s,email=%s
            WHERE student_id=%s
        """, (request.form["name"], request.form["email"], id))
        conn.commit()
        conn.close()
        return redirect("/admin/view_students")

    cursor.execute("SELECT * FROM students WHERE student_id=%s", (id,))
    student = cursor.fetchone()
    conn.close()

    return render_template("edit_student.html", student=student)

@app.route("/admin/delete_student/<int:id>")
def delete_student(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE student_id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin/view_students")

@app.route("/admin/add_faculty", methods=["GET", "POST"])
def admin_add_faculty():
    if "admin_id" not in session:
        return redirect("/admin_login")

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        subject = request.form["subject"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO faculty (name, email, password, subject)
            VALUES (%s, %s, %s, %s)
        """, (name, email, password, subject))

        conn.commit()
        conn.close()

        return redirect("/admin/view_faculty")

    return render_template("add_faculty.html")

@app.route("/admin/view_faculty")
def view_faculty():
    if "admin_id" not in session:
        return redirect("/admin_login")

    search = request.args.get("search")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if search:
        cursor.execute("""
            SELECT * FROM faculty
            WHERE name LIKE %s OR subject LIKE %s
        """, (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM faculty")

    faculty = cursor.fetchall()
    conn.close()

    return render_template("view_faculty.html", faculty=faculty, search=search)



@app.route("/admin/edit_faculty/<int:id>", methods=["GET","POST"])
def edit_faculty(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute("""
            UPDATE faculty 
            SET name=%s, email=%s, subject=%s
            WHERE faculty_id=%s
        """, (
            request.form["name"],
            request.form["email"],
            request.form["subject"],
            id
        ))
        conn.commit()
        conn.close()
        return redirect("/admin/view_faculty")

    cursor.execute("SELECT * FROM faculty WHERE faculty_id=%s", (id,))
    faculty = cursor.fetchone()
    conn.close()

    return render_template("edit_faculty.html", faculty=faculty)

@app.route("/admin/delete_faculty/<int:id>")
def delete_faculty(id):
    if "admin_id" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM faculty WHERE faculty_id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin/view_faculty")



# end of testing


# ---------------- STUDENT LOGIN ----------------
@app.route("/student_login", methods=[ "POST"])
def student_login():
        roll_no = request.form.get("roll_no")
        password = request.form.get("password")

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM students WHERE roll_no=%s AND password=%s",
            (roll_no, password)
        )
        student = cursor.fetchone()
        conn.close()

        if student:
            session["student_id"] = student["student_id"]
            session["roll_no"] = student["roll_no"]
            return redirect("/student_dashboard")
        else:
            return 'Invalid roll number or password'
        
            



@app.route("/student_qr")
def student_qr():
    if "student_id" not in session:
        return redirect("/login")

    qr_file = f"{session['roll_no']}.png"
    return render_template("student_qr.html", qr_file=qr_file)



@app.route("/faculty_login", methods=["GET", "POST"])
def faculty_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT * FROM faculty
            WHERE email=%s AND password=%s
        """, (email, password))

        faculty = cursor.fetchone()
        conn.close()

        if faculty:
            session["faculty_id"] = faculty["faculty_id"]
            session["faculty_name"] = faculty["name"]
            session["subject"] = faculty["subject"]
            return redirect("/faculty_dashboard")
        else:
            return "Invalid email or password"

    return render_template("faculty_login.html")




@app.route("/faculty_dashboard")
def faculty_dashboard():
    if "faculty_id" not in session:
        return redirect("/faculty_login")

    from database import get_connection

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT name, subject FROM faculty WHERE faculty_id=%s",
        (session["faculty_id"],)
    )
    faculty = cursor.fetchone()
    conn.close()

    return render_template(
        "faculty_dashboard.html",
        faculty=faculty
    )



@app.route("/mark_attendance")
def mark_attendance():
    import cv2
    from datetime import datetime
    from database import get_connection
    from flask import flash, redirect, url_for

    if "faculty_id" not in session:
        return redirect("/faculty_login")

    faculty_id = session["faculty_id"]
    subject = session["subject"]

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

            cursor.execute(
                "SELECT student_id FROM students WHERE roll_no=%s",
                (roll_no,)
            )
            result = cursor.fetchone()

            if not result:
                conn.close()
                cap.release()
                cv2.destroyAllWindows()
                flash("Student not registered", "danger")
                return redirect("/faculty_dashboard")

            student_id = result[0]

            cursor.execute("""
                SELECT 1 FROM attendance
                WHERE student_id=%s AND subject=%s AND date=%s
            """, (student_id, subject, now.date()))

            if cursor.fetchone():
                conn.close()
                cap.release()
                cv2.destroyAllWindows()
                flash("Attendance already marked", "warning")
                return redirect("/faculty_dashboard")

            cursor.execute("""
                INSERT INTO attendance
                (student_id, faculty_id, subject, date, time, method)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                student_id,
                faculty_id,
                subject,
                now.date(),
                now.time(),
                "QR"
            ))

            conn.commit()
            conn.close()

            cap.release()
            cv2.destroyAllWindows()
            flash("Attendance marked successfully", "success")
            return redirect("/faculty_dashboard")

        cv2.imshow("Scan QR", frame)
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    flash("Camera closed", "info")
    return redirect("/faculty_dashboard")


# ---------------- STUDENT DASHBOARD ----------------
@app.route("/student_dashboard")
def student_dashboard():
    if "student_id" not in session:
        return redirect("/student_login")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Student Info
    cursor.execute(
        "SELECT * FROM students WHERE student_id=%s",
        (session["student_id"],)
    )
    student = cursor.fetchone()

    # Attendance History 
    cursor.execute( 
        "SELECT subject,date, time, method FROM attendance WHERE student_id=%s ORDER BY date DESC", 
        (session["student_id"],)
    ) 
    attendance = cursor.fetchall()

    conn.close()

    qr_file = f"{student['roll_no']}.png"

    return render_template(
        "student_dashboard.html",
        student=student,
        attendance=attendance,
        qr_file=qr_file
    )



# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")



@app.route("/test")
def test():
    return "TEST OK"






if __name__ == "__main__":
    app.run(debug=True)
