from datetime import date, datetime, timedelta
from functools import wraps
import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from sqlalchemy import func
from . import db
from .models import User, Student, Attendance, Material, Feedback, ClassRoom, Notification, ActivityLog

bp = Blueprint("main", __name__)


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("main.dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def log_action(action, entity=None, entity_id=None):
    db.session.add(ActivityLog(user_id=current_user.id, action=action,
                                entity=entity, entity_id=entity_id))


def create_notification(user_id, title, message, notification_type="info"):
    db.session.add(Notification(user_id=user_id, title=title, message=message,
                                 notification_type=notification_type))


def attendance_summary(student_id, days=30):
    start = date.today() - timedelta(days=days - 1)
    rows = Attendance.query.filter(
        Attendance.student_id == student_id,
        Attendance.date >= start
    ).all()
    total = len(rows)
    present = sum(r.status == "Present" for r in rows)
    late = sum(r.status == "Late" for r in rows)
    absent = sum(r.status == "Absent" for r in rows)
    rate = round(((present + late) / total) * 100, 1) if total else 0
    return {"total": total, "present": present, "late": late, "absent": absent, "rate": rate}


def overall_attendance(days=30, student_ids=None):
    start = date.today() - timedelta(days=days - 1)
    q = Attendance.query.filter(Attendance.date >= start)
    if student_ids is not None:
        if not student_ids:
            return {"total": 0, "present": 0, "absent": 0, "late": 0, "rate": 0}
        q = q.filter(Attendance.student_id.in_(student_ids))
    rows = q.all()
    total = len(rows)
    present = sum(r.status == "Present" for r in rows)
    late = sum(r.status == "Late" for r in rows)
    absent = sum(r.status == "Absent" for r in rows)
    rate = round(((present + late) / total) * 100, 1) if total else 0
    return {"total": total, "present": present, "absent": absent, "late": late, "rate": rate}


def build_trend(days=14, student_ids=None):
    result = []
    start = date.today() - timedelta(days=days - 1)
    for i in range(days):
        d = start + timedelta(days=i)
        q = Attendance.query.filter(Attendance.date == d)
        if student_ids is not None:
            if not student_ids:
                rows = []
            else:
                rows = q.filter(Attendance.student_id.in_(student_ids)).all()
        else:
            rows = q.all()
        total = len(rows)
        present = sum(r.status == "Present" for r in rows)
        rate = round(present / total * 100, 1) if total else 0
        result.append({"date": d.strftime("%d %b"), "rate": rate, "total": total})
    return result


def low_attendance_students(threshold=75):
    students = Student.query.order_by(Student.name).all()
    result = []
    for s in students:
        summary = attendance_summary(s.id, 30)
        if summary["total"] and summary["rate"] < threshold:
            result.append((s, summary))
    return result


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, request.form["password"]):
            login_user(user)
            return redirect(url_for("main.dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    # Parent gets a dedicated dashboard experience.
    if current_user.role == "parent":
        children = Student.query.filter_by(parent_id=current_user.id).order_by(Student.name).all()
        ids = [s.id for s in children]
        summary = overall_attendance(30, ids)
        trend = build_trend(14, ids)
        unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
        recent_feedback = Feedback.query.filter_by(submitted_by=current_user.id).order_by(Feedback.created_at.desc()).limit(5).all()
        return render_template("parent_dashboard.html", children=children, summary=summary, trend=trend,
                               unread=unread, notifications=notifications, recent_feedback=recent_feedback)

    students = Student.query.count()
    teachers = User.query.filter_by(role="teacher").count()
    summary = overall_attendance(30)
    today = overall_attendance(1)
    low = low_attendance_students(75)
    open_feedback = Feedback.query.filter_by(status="Open").count()
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    trend = build_trend(14)
    activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(8).all()
    class_stats = []
    for c in ClassRoom.query.order_by(ClassRoom.name).all():
        ids = [s.id for s in Student.query.filter_by(class_id=c.id).all()]
        s = overall_attendance(30, ids)
        class_stats.append({"name": c.name, "students": len(ids), "rate": s["rate"]})
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()

    return render_template("dashboard.html", students=students, teachers=teachers,
                           summary=summary, today=today, low=low,
                           open_feedback=open_feedback, unread=unread, trend=trend,
                           class_stats=class_stats, activities=activities,
                           notifications=notifications,
                           materials=Material.query.order_by(Material.created_at.desc()).limit(5).all())


@bp.route("/students", methods=["GET", "POST"])
@role_required("admin", "teacher")
def students():
    classes = ClassRoom.query.order_by(ClassRoom.name).all()
    if request.method == "POST":
        student = Student(
            name=request.form["name"].strip(),
            roll_no=request.form["roll_no"].strip(),
            email=request.form.get("email", "").strip(),
            class_id=int(request.form["class_id"]) if request.form.get("class_id") else None,
            parent_id=int(request.form["parent_id"]) if request.form.get("parent_id") else None
        )
        db.session.add(student)
        db.session.flush()
        log_action(f"Added student {student.name}", "student", student.id)
        db.session.commit()
        flash("Student added successfully.", "success")
        return redirect(url_for("main.students"))

    q = Student.query
    search = request.args.get("q", "").strip()
    class_id = request.args.get("class_id", "").strip()
    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(Student.name.ilike(like), Student.roll_no.ilike(like), Student.email.ilike(like)))
    if class_id:
        q = q.filter(Student.class_id == int(class_id))
    return render_template("students.html", students=q.order_by(Student.name).all(),
                           classes=classes, parents=User.query.filter_by(role="parent").all(),
                           search=search, selected_class=class_id)


@bp.route("/student/<int:student_id>")
@login_required
def student_detail(student_id):
    student = Student.query.get_or_404(student_id)
    if current_user.role == "parent" and student.parent_id != current_user.id:
        flash("You cannot access this student record.", "danger")
        return redirect(url_for("main.dashboard"))
    summary = attendance_summary(student.id, 30)
    history = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date.desc()).limit(20).all()
    feedback = Feedback.query.filter_by(student_id=student.id).order_by(Feedback.created_at.desc()).limit(10).all()
    return render_template("student_detail.html", student=student, summary=summary, history=history, feedback=feedback)


@bp.route("/attendance", methods=["GET", "POST"])
@role_required("admin", "teacher")
def attendance():
    students = Student.query.order_by(Student.name).all()
    selected_date = request.args.get("date", date.today().isoformat())
    record_date = date.fromisoformat(selected_date)

    if request.method == "POST":
        record_date = date.fromisoformat(request.form["date"])
        for s in students:
            status = request.form.get(f"status_{s.id}", "Absent")
            record = Attendance.query.filter_by(student_id=s.id, date=record_date).first()
            if not record:
                record = Attendance(student_id=s.id, date=record_date, marked_by=current_user.id)
                db.session.add(record)
            record.status = status

            # Automation: create an alert for a parent when a child is absent.
            if status == "Absent" and s.parent_id:
                create_notification(
                    s.parent_id,
                    f"Attendance alert: {s.name}",
                    f"{s.name} was marked absent on {record_date.strftime('%d %b %Y')}.",
                    "warning"
                )

        log_action(f"Recorded attendance for {record_date.strftime('%d %b %Y')}", "attendance")
        db.session.commit()
        flash("Attendance saved. Parent alerts were generated for absent students.", "success")
        return redirect(url_for("main.attendance", date=record_date.isoformat()))

    records = {a.student_id: a for a in Attendance.query.filter_by(date=record_date).all()}
    return render_template("attendance.html", students=students, records=records, selected_date=selected_date)


@bp.route("/analytics")
@role_required("admin", "teacher")
def analytics():
    summary = overall_attendance(30)
    trend = build_trend(14)
    low = low_attendance_students(75)
    class_stats = []
    for c in ClassRoom.query.order_by(ClassRoom.name).all():
        ids = [s.id for s in Student.query.filter_by(class_id=c.id).all()]
        s = overall_attendance(30, ids)
        class_stats.append({"name": c.name, "students": len(ids), "rate": s["rate"]})
    return render_template("analytics.html", summary=summary, trend=trend, low=low, class_stats=class_stats)


@bp.route("/materials", methods=["GET", "POST"])
@login_required
def materials():
    if request.method == "POST":
        if current_user.role not in ("admin", "teacher"):
            flash("Only teachers and administrators can upload materials.", "danger")
            return redirect(url_for("main.materials"))
        material = Material(title=request.form["title"].strip(),
                            subject=request.form.get("subject", "").strip(),
                            description=request.form.get("description", "").strip(),
                            file_name=request.form.get("file_name", "").strip() or "resource")
        material.uploaded_by = current_user.id
        db.session.add(material)
        log_action(f"Published material {material.title}", "material")
        db.session.commit()
        flash("Study material published.", "success")
        return redirect(url_for("main.materials"))
    return render_template("materials.html", materials=Material.query.order_by(Material.created_at.desc()).all())


@bp.route("/feedback", methods=["GET", "POST"])
@login_required
def feedback():
    students = Student.query.filter_by(parent_id=current_user.id).all() if current_user.role == "parent" else Student.query.all()
    if request.method == "POST":
        student_id = int(request.form["student_id"])
        if current_user.role == "parent":
            if not Student.query.filter_by(id=student_id, parent_id=current_user.id).first():
                flash("Invalid student selected.", "danger")
                return redirect(url_for("main.feedback"))
        item = Feedback(student_id=student_id, submitted_by=current_user.id,
                        category=request.form["category"],
                        message=request.form["message"].strip())
        db.session.add(item)
        log_action(f"Submitted feedback for student {student_id}", "feedback")
        db.session.commit()
        flash("Feedback submitted.", "success")
        return redirect(url_for("main.feedback"))
    items = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return render_template("feedback.html", students=students, feedback_items=items)


@bp.route("/feedback/<int:feedback_id>/close", methods=["POST"])
@role_required("admin", "teacher")
def close_feedback(feedback_id):
    item = Feedback.query.get_or_404(feedback_id)
    item.status = "Closed"
    log_action(f"Closed feedback #{feedback_id}", "feedback", feedback_id)
    db.session.commit()
    flash("Feedback closed.", "success")
    return redirect(url_for("main.feedback"))


@bp.route("/notifications")
@login_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template("notifications.html", notifications=items)


@bp.route("/notifications/read/<int:notification_id>", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    item = Notification.query.get_or_404(notification_id)
    if item.user_id != current_user.id:
        return redirect(url_for("main.notifications"))
    item.is_read = True
    db.session.commit()
    return redirect(request.referrer or url_for("main.notifications"))


@bp.route("/reports/attendance.csv")
@role_required("admin", "teacher")
def attendance_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student", "Roll No", "Class", "Date", "Status"])
    rows = Attendance.query.order_by(Attendance.date.desc()).all()
    for r in rows:
        writer.writerow([
            r.student.name, r.student.roll_no,
            r.student.classroom.name if r.student.classroom else "",
            r.date.isoformat(), r.status
        ])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=attendance_report.csv"})


@bp.route("/api/dashboard")
@login_required
def api_dashboard():
    summary = overall_attendance(30)
    return jsonify({
        "students": Student.query.count(),
        "teachers": User.query.filter_by(role="teacher").count(),
        "attendance_rate": summary["rate"],
        "open_feedback": Feedback.query.filter_by(status="Open").count(),
        "low_attendance_students": len(low_attendance_students(75))
    })
