from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import User, Student, Attendance, Material, Feedback, ClassRoom, Notification, ActivityLog

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    admin = User(name="System Admin", email="admin@school.local",
                 password_hash=generate_password_hash("demo123"), role="admin")
    teacher = User(name="Anita Sharma", email="teacher@school.local",
                   password_hash=generate_password_hash("demo123"), role="teacher")
    parent = User(name="Rahul Verma", email="parent@school.local",
                  password_hash=generate_password_hash("demo123"), role="parent")
    parent2 = User(name="Priya Mehta", email="parent2@school.local",
                   password_hash=generate_password_hash("demo123"), role="parent")
    db.session.add_all([admin, teacher, parent, parent2])
    db.session.flush()

    c1 = ClassRoom(name="Grade 8 - A", academic_year="2026-27", teacher_id=teacher.id)
    c2 = ClassRoom(name="Grade 9 - B", academic_year="2026-27", teacher_id=teacher.id)
    c3 = ClassRoom(name="Grade 10 - A", academic_year="2026-27", teacher_id=teacher.id)
    db.session.add_all([c1, c2, c3])
    db.session.flush()

    students = [
        Student(name="Aarav Verma", roll_no="8A01", email="aarav@example.com", parent_id=parent.id, class_id=c1.id),
        Student(name="Ishita Singh", roll_no="8A02", email="ishita@example.com", parent_id=parent.id, class_id=c1.id),
        Student(name="Kabir Khan", roll_no="8A03", email="kabir@example.com", parent_id=parent2.id, class_id=c1.id),
        Student(name="Meera Joshi", roll_no="8A04", email="meera@example.com", parent_id=parent2.id, class_id=c2.id),
        Student(name="Rohan Gupta", roll_no="9B01", email="rohan@example.com", parent_id=parent.id, class_id=c2.id),
        Student(name="Sara Ali", roll_no="9B02", email="sara@example.com", parent_id=parent2.id, class_id=c2.id),
        Student(name="Dev Malhotra", roll_no="10A01", email="dev@example.com", parent_id=parent.id, class_id=c3.id),
        Student(name="Zoya Khan", roll_no="10A02", email="zoya@example.com", parent_id=parent2.id, class_id=c3.id),
    ]
    db.session.add_all(students)
    db.session.flush()

    # 20-day attendance history with deliberately varied patterns.
    for day_offset in range(20, -1, -1):
        d = date.today() - timedelta(days=day_offset)
        for idx, s in enumerate(students):
            if idx == 2:
                status = "Absent" if day_offset % 3 != 0 else "Present"
            elif idx == 5:
                status = "Absent" if day_offset % 5 == 0 else "Present"
            elif idx == 7:
                status = "Late" if day_offset % 4 == 0 else "Present"
            else:
                status = "Absent" if (day_offset + idx) % 13 == 0 else "Present"
            db.session.add(Attendance(student_id=s.id, date=d, status=status, marked_by=teacher.id))

    materials = [
        Material(title="Algebra Revision Notes", subject="Mathematics",
                 description="Revision notes and practice questions for the upcoming assessment.",
                 uploaded_by=teacher.id, file_name="algebra_revision_notes.pdf"),
        Material(title="Science Lab Safety Guide", subject="Science",
                 description="Lab safety procedures and practical checklist.",
                 uploaded_by=teacher.id, file_name="science_lab_safety.pdf"),
        Material(title="English Writing Framework", subject="English",
                 description="Structured framework for essays and analytical writing.",
                 uploaded_by=teacher.id, file_name="english_writing.pdf"),
    ]
    db.session.add_all(materials)

    db.session.add(Feedback(student_id=students[0].id, submitted_by=parent.id,
                            category="Academic", message="Please share additional mathematics practice material.",
                            status="Open"))
    db.session.add(Feedback(student_id=students[2].id, submitted_by=parent2.id,
                            category="Attendance", message="Please advise if there are any attendance concerns.",
                            status="Open"))

    db.session.add(Notification(
        user_id=parent.id,
        title="Welcome to EduAdmin",
        message="Your parent dashboard is ready. You can review attendance, materials and feedback here.",
        notification_type="info"
    ))
    db.session.add(Notification(
        user_id=parent2.id,
        title="Attendance attention required",
        message="Kabir Khan has attendance below the 75% monitoring threshold.",
        notification_type="warning"
    ))

    for action in [
        "Published Algebra Revision Notes",
        "Updated student records",
        "Reviewed attendance dashboard",
        "Generated monthly attendance report",
    ]:
        db.session.add(ActivityLog(user_id=admin.id, action=action, entity="system"))

    db.session.commit()
    print("EduAdmin V2 demo database created successfully.")
