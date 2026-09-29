"""
EduSmart — Academic Management System
Built with Python, Flask, and flat-file CSV storage.
"""
import csv
import os
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                    session, flash)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

app = Flask(__name__)
app.secret_key = "edusmart-dev-secret-key-change-me"

FILES = {
    "admin": "admin.csv",
    "students": "students.csv",
    "teachers": "teachers.csv",
    "attendance": "attendance.csv",
    "fees": "fees.csv",
    "results": "results.csv",
    "notices": "notices.csv",
    "complaints": "complaints.csv",
}

FIELDS = {
    "admin": ["admin_id", "password", "name", "email"],
    "students": ["student_id", "password", "first_name", "last_name",
                 "class", "division", "email", "phone"],
    "teachers": ["teacher_id", "password", "name", "subject", "email", "phone"],
    "attendance": ["student_id", "date", "status", "marked_by"],
    "fees": ["student_id", "total_fee", "paid_fee", "status"],
    "results": ["student_id", "subject", "marks", "grade", "term"],
    "notices": ["id", "title", "description", "date", "posted_by"],
    "complaints": ["id", "teacher_id", "date", "class", "division",
                    "location", "issue_type", "description", "status"],
}
# ---------------------------------------------------------------- storage --

def _path(table):
    return os.path.join(DATA_DIR, FILES[table])

def read_rows(table):
    path = _path(table)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_rows(table, rows):
    path = _path(table)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS[table])
        writer.writeheader()
        writer.writerows(rows)


def append_row(table, row):
    rows = read_rows(table)
    rows.append(row)
    write_rows(table, rows)


def next_id(rows, key="id", start=100001):
    if not rows:
        return str(start)
    existing = [int(r[key]) for r in rows if r.get(key, "").isdigit()]
    return str(max(existing) + 1) if existing else str(start)


def grade_from_marks(marks):
    marks = int(marks)
    if marks >= 90:
        return "A+"
    if marks >= 80:
        return "A"
    if marks >= 70:
        return "B"
    if marks >= 60:
        return "C"
    if marks >= 50:
        return "D"
    return "F"


# ----------------------------------------------------------------- guards --

def login_required(role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                flash("Please sign in to continue.", "error")
                return redirect(url_for("login"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def current_student():
    rows = read_rows("students")
    for r in rows:
        if r["student_id"] == session.get("user_id"):
            return r
    return None


def current_teacher():
    rows = read_rows("teachers")
    for r in rows:
        if r["teacher_id"] == session.get("user_id"):
            return r
    return None


# ------------------------------------------------------------------- auth --

@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role", "student")
        user_id = request.form.get("user_id", "").strip()
        password = request.form.get("password", "")

        table = {"student": "students", "teacher": "teachers", "admin": "admin"}[role]
        id_field = {"student": "student_id", "teacher": "teacher_id", "admin": "admin_id"}[role]

        rows = read_rows(table)
        match = next((r for r in rows if r[id_field] == user_id and r["password"] == password), None)

        if match:
            session["role"] = role
            session["user_id"] = user_id
            session["name"] = match.get("name") or f'{match.get("first_name", "")} {match.get("last_name", "")}'.strip()
            return redirect(url_for(f"{role}_dashboard"))

        flash("Invalid credentials. Please check your ID and password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------- student --

@app.route("/student/dashboard")
@login_required("student")
def student_dashboard():
    return render_template("student/dashboard.html", student=current_student())


@app.route("/student/profile")
@login_required("student")
def student_profile():
    return render_template("student/profile.html", student=current_student())


@app.route("/student/attendance")
@login_required("student")
def student_attendance():
    sid = session["user_id"]
    records = [r for r in read_rows("attendance") if r["student_id"] == sid]
    records.sort(key=lambda r: r["date"], reverse=True)
    present = sum(1 for r in records if r["status"] == "Present")
    total = len(records) or 1
    pct = round((present / total) * 100, 1)
    return render_template("student/attendance.html", student=current_student(),
                            records=records, pct=pct, total=len(records))


@app.route("/student/fees")
@login_required("student")
def student_fees():
    sid = session["user_id"]
    fee = next((r for r in read_rows("fees") if r["student_id"] == sid), None)
    return render_template("student/fees.html", student=current_student(), fee=fee)


@app.route("/student/results")
@login_required("student")
def student_results():
    sid = session["user_id"]
    records = [r for r in read_rows("results") if r["student_id"] == sid]
    return render_template("student/results.html", student=current_student(), records=records)


@app.route("/student/notices")
@login_required("student")
def student_notices():
    notices = sorted(read_rows("notices"), key=lambda r: r["date"], reverse=True)
    return render_template("student/notices.html", student=current_student(), notices=notices)


# ---------------------------------------------------------------- teacher --

@app.route("/teacher/dashboard")
@login_required("teacher")
def teacher_dashboard():
    return render_template("teacher/dashboard.html", teacher=current_teacher())


@app.route("/teacher/students", methods=["GET", "POST"])
@login_required("teacher")
def teacher_students():
    students = read_rows("students")
    classes = sorted(set(s["class"] for s in students))
    filtered = None
    cls = div = None
    if request.method == "POST":
        cls = request.form.get("class")
        div = request.form.get("division")
        filtered = [s for s in students if s["class"] == cls and s["division"] == div]
    return render_template("teacher/view_students.html", teacher=current_teacher(),
                            classes=classes, students=filtered, cls=cls, div=div)


@app.route("/teacher/attendance", methods=["GET", "POST"])
@login_required("teacher")
def teacher_attendance():
    students = read_rows("students")
    classes = sorted(set(s["class"] for s in students))
    roster = None
    cls = div = None
    if request.method == "POST" and "load" in request.form:
        cls = request.form.get("class")
        div = request.form.get("division")
        roster = [s for s in students if s["class"] == cls and s["division"] == div]
    elif request.method == "POST" and "save" in request.form:
        date = request.form.get("date") or datetime.now().strftime("%Y-%m-%d")
        rows = read_rows("attendance")
        ids = request.form.getlist("student_ids")
        for sid in ids:
            status = request.form.get(f"status_{sid}", "Present")
            rows.append({"student_id": sid, "date": date, "status": status,
                         "marked_by": session["user_id"]})
        write_rows("attendance", rows)
        flash("Attendance saved successfully.", "success")
        return redirect(url_for("teacher_attendance"))
    return render_template("teacher/mark_attendance.html", teacher=current_teacher(),
                            classes=classes, roster=roster, cls=cls, div=div,
                            today=datetime.now().strftime("%Y-%m-%d"))


@app.route("/teacher/complaint", methods=["GET", "POST"])
@login_required("teacher")
def teacher_complaint():
    if request.method == "POST":
        rows = read_rows("complaints")
        new_id = next_id(rows)
        rows.append({
            "id": new_id,
            "teacher_id": session["user_id"],
            "date": request.form.get("date") or datetime.now().strftime("%Y-%m-%d"),
            "class": request.form.get("class", ""),
            "division": request.form.get("division", ""),
            "location": request.form.get("location", ""),
            "issue_type": request.form.get("issue_type", "Technical"),
            "description": request.form.get("description", ""),
            "status": "Pending",
        })
        write_rows("complaints", rows)
        flash("Complaint submitted and logged for review.", "success")
        return redirect(url_for("teacher_complaint_tracker"))
    return render_template("teacher/complaint_center.html", teacher=current_teacher(),
                            today=datetime.now().strftime("%Y-%m-%d"))


@app.route("/teacher/complaint/tracker")
@login_required("teacher")
def teacher_complaint_tracker():
    tid = session["user_id"]
    rows = [r for r in read_rows("complaints") if r["teacher_id"] == tid]
    rows.sort(key=lambda r: r["date"], reverse=True)
    return render_template("teacher/complaint_tracker.html", teacher=current_teacher(), complaints=rows)


@app.route("/teacher/results", methods=["GET", "POST"])
@login_required("teacher")
def teacher_results():
    students = read_rows("students")
    classes = sorted(set(s["class"] for s in students))
    if request.method == "POST":
        sid = request.form.get("student_id")
        subject = request.form.get("subject")
        marks = request.form.get("marks")
        term = request.form.get("term", "Term 1")
        if sid and subject and marks:
            rows = read_rows("results")
            rows.append({"student_id": sid, "subject": subject, "marks": marks,
                         "grade": grade_from_marks(marks), "term": term})
            write_rows("results", rows)
            flash(f"Marks recorded for {sid} — {subject}.", "success")
        return redirect(url_for("teacher_results"))
    return render_template("teacher/add_results.html", teacher=current_teacher(),
                            classes=classes, students=students)


@app.route("/teacher/notices", methods=["GET", "POST"])
@login_required("teacher")
def teacher_notices():
    if request.method == "POST":
        rows = read_rows("notices")
        new_id = next_id(rows)
        rows.append({
            "id": new_id,
            "title": request.form.get("title", ""),
            "description": request.form.get("description", ""),
            "date": request.form.get("date") or datetime.now().strftime("%Y-%m-%d"),
            "posted_by": session["name"],
        })
        write_rows("notices", rows)
        flash("Announcement published to the notice board.", "success")
        return redirect(url_for("teacher_notices"))
    notices = sorted(read_rows("notices"), key=lambda r: r["date"], reverse=True)
    return render_template("teacher/notices.html", teacher=current_teacher(), notices=notices,
                            today=datetime.now().strftime("%Y-%m-%d"))


# ------------------------------------------------------------------ admin --

@app.route("/admin/dashboard")
@login_required("admin")
def admin_dashboard():
    students = read_rows("students")
    teachers = read_rows("teachers")
    fees = read_rows("fees")
    pending_fee_count = sum(1 for f in fees if f["status"] != "Paid")
    open_complaints = sum(1 for c in read_rows("complaints") if c["status"] != "Completed")
    return render_template("admin/dashboard.html",
                            total_students=len(students), total_teachers=len(teachers),
                            pending_fee_count=pending_fee_count, open_complaints=open_complaints)


@app.route("/admin/students/add", methods=["GET", "POST"])
@login_required("admin")
def admin_add_student():
    if request.method == "POST":
        rows = read_rows("students")
        new_id = "STU" + str(101 + len(rows))
        rows.append({
            "student_id": new_id,
            "password": request.form.get("password") or "stud123",
            "first_name": request.form.get("first_name", ""),
            "last_name": request.form.get("last_name", ""),
            "class": request.form.get("class", ""),
            "division": request.form.get("division", ""),
            "email": request.form.get("email", ""),
            "phone": request.form.get("phone", ""),
        })
        write_rows("students", rows)
        # default fee record
        fees = read_rows("fees")
        fees.append({"student_id": new_id, "total_fee": "0", "paid_fee": "0", "status": "Pending"})
        write_rows("fees", fees)
        flash(f"Student enrolled with ID {new_id}.", "success")
        return redirect(url_for("admin_add_student"))
    return render_template("admin/add_student.html")


@app.route("/admin/students", methods=["GET", "POST"])
@login_required("admin")
def admin_view_students():
    students = read_rows("students")
    classes = sorted(set(s["class"] for s in students))
    filtered = None
    cls = div = None
    if request.method == "POST":
        cls = request.form.get("class")
        div = request.form.get("division")
        filtered = [s for s in students if s["class"] == cls and s["division"] == div]
    return render_template("admin/view_students.html", classes=classes,
                            students=filtered, cls=cls, div=div)


@app.route("/admin/promote", methods=["GET", "POST"])
@login_required("admin")
def admin_promote():
    students = read_rows("students")
    classes = sorted(set(s["class"] for s in students))
    if request.method == "POST":
        cls = request.form.get("class")
        div = request.form.get("division")
        count = 0
        for s in students:
            if s["class"] == cls and s["division"] == div:
                s["class"] = str(int(s["class"]) + 1)
                count += 1
        write_rows("students", students)
        flash(f"Promoted {count} student(s) from Class {cls}-{div} to Class {int(cls)+1}.", "success")
        return redirect(url_for("admin_promote"))
    return render_template("admin/promote.html", classes=classes)


@app.route("/admin/fees", methods=["GET", "POST"])
@login_required("admin")
def admin_fees():
    students = read_rows("students")
    classes = sorted(set(s["class"] for s in students))
    breakdown = None
    cls = div = None
    if request.method == "POST":
        cls = request.form.get("class")
        div = request.form.get("division")
        fees = {f["student_id"]: f for f in read_rows("fees")}
        matched = [s for s in students if s["class"] == cls and s["division"] == div]
        breakdown = []
        for s in matched:
            f = fees.get(s["student_id"], {"total_fee": "0", "paid_fee": "0", "status": "Pending"})
            breakdown.append({**s, **f})
    return render_template("admin/fees_control.html", classes=classes,
                            breakdown=breakdown, cls=cls, div=div)


@app.route("/admin/fees/pay", methods=["GET", "POST"])
@login_required("admin")
def admin_pay_fees():
    record = None
    student = None
    if request.method == "POST" and "verify" in request.form:
        sid = request.form.get("student_id", "").strip().upper()
        student = next((s for s in read_rows("students") if s["student_id"] == sid), None)
        record = next((f for f in read_rows("fees") if f["student_id"] == sid), None)
        if not student or not record:
            flash("No matching student or fee record found.", "error")
    elif request.method == "POST" and "confirm_payment" in request.form:
        sid = request.form.get("student_id")
        fees = read_rows("fees")
        for f in fees:
            if f["student_id"] == sid:
                f["paid_fee"] = f["total_fee"]
                f["status"] = "Paid"
        write_rows("fees", fees)
        flash(f"Full balance collected for {sid}. Marked as Paid.", "success")
        return redirect(url_for("admin_pay_fees"))
    return render_template("admin/pay_fees.html", record=record, student=student)


@app.route("/admin/teachers/add", methods=["GET", "POST"])
@login_required("admin")
def admin_add_teacher():
    if request.method == "POST":
        rows = read_rows("teachers")
        new_id = "T" + str(101 + len(rows))
        rows.append({
            "teacher_id": new_id,
            "password": "teach123",
            "name": request.form.get("name", ""),
            "subject": request.form.get("subject", ""),
            "email": request.form.get("email", ""),
            "phone": request.form.get("phone", ""),
        })
        write_rows("teachers", rows)
        flash(f"Faculty profile created with ID {new_id}.", "success")
        return redirect(url_for("admin_add_teacher"))
    return render_template("admin/add_teacher.html")


@app.route("/admin/teachers", methods=["GET", "POST"])
@login_required("admin")
def admin_view_teachers():
    teachers = read_rows("teachers")
    subjects = sorted(set(t["subject"] for t in teachers))
    filtered = None
    subject = None
    if request.method == "POST":
        subject = request.form.get("subject")
        filtered = [t for t in teachers if t["subject"] == subject]
    return render_template("admin/view_teachers.html", subjects=subjects,
                            teachers=filtered, subject=subject)


@app.route("/admin/complaints", methods=["GET", "POST"])
@login_required("admin")
def admin_complaints():
    if request.method == "POST":
        cid = request.form.get("complaint_id")
        rows = read_rows("complaints")
        for c in rows:
            if c["id"] == cid:
                c["status"] = "Completed"
        write_rows("complaints", rows)
        flash("Complaint marked as resolved.", "success")
        return redirect(url_for("admin_complaints"))
    complaints = sorted(read_rows("complaints"), key=lambda r: r["date"], reverse=True)
    return render_template("admin/complaints.html", complaints=complaints)


if __name__ == "__main__":
    app.run(debug=True)
