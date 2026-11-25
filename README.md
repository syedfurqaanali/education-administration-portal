# Education Administration Portal — V2

A portfolio-ready education administration, analytics and engagement platform built with Flask, SQLite and server-rendered HTML/CSS.

## V2 highlights

### Administration
- Role-based authentication: Admin, Teacher, Parent
- Student directory with search and class filtering
- Student profiles
- Class-level attendance benchmarking
- Activity log
- CSV attendance export

### Attendance & automation
- Daily attendance capture
- 30-day attendance KPI
- 14-day attendance trend
- At-risk student detection below 75%
- Automatic parent notification when a student is marked absent
- Student-level attendance history

### Parent experience
- Parent dashboard
- Child-specific student profiles
- Attendance trend
- Notifications
- Feedback tracking

### Learning & engagement
- Study material library
- Feedback and escalation workflow
- Feedback close-out for Admin/Teacher

### Analytics
- Attendance health KPI
- Class benchmarking
- Risk register
- Decision-oriented dashboard

## Demo accounts

All use password `demo123`.

- Admin: `admin@school.local`
- Teacher: `teacher@school.local`
- Parent: `parent@school.local`
- Parent 2: `parent2@school.local`

## Python compatibility

Designed for Python 3.8.x.

## Run

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python run.py
```

Open `http://127.0.0.1:5000`.

## Portfolio positioning

This project demonstrates:
- Relational data modeling
- SQL-backed analytics
- Role-based application design
- KPI/dashboard development
- Attendance and risk analytics
- Automated notification logic
- CRUD operations
- CSV reporting
- Search/filter workflows
- Parent/teacher/admin user journeys
- Business process automation patterns
