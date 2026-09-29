# EduSmart — Academic Management System

A role-based school academic management portal built with **Python**, **Flask**,
and flat-file **CSV** storage — Student Workspace, Teacher Dashboard, and Admin
Control Panel in one system.

## Features

**Student Workspace**
- My Profile — personal & academic details
- Attendance — daily log + overall percentage
- Fee Report — total due, paid, balance, status
- Results — subject-wise marks and grades
- Notice Board — school announcements

**Teacher Dashboard**
- View Students — roster by class & division
- Mark Attendance — daily roll call (Present / Absent / Holiday / Leave)
- Complaint Center — raise technical/facility issues
- Complaint Tracker — check resolution status
- Add Results — enter subject marks (auto-graded)
- Notice Board — publish announcements

**Admin Control Panel**
- Add / View Students, Promote Class
- Fee Control — view balances by class, process payments at a counter
- Add / View Teachers
- Complaints — review and resolve faculty-raised issues

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## Demo Logins

| Role    | ID      | Password  |
|---------|---------|-----------|
| Student | STU101  | stud123   |
| Teacher | T101    | teach123  |
| Admin   | ADM001  | admin123  |

## Data storage

All records live as plain CSV files under `/data` — no database server
required. Each table (`students`, `teachers`, `attendance`, `fees`,
`results`, `notices`, `complaints`, `admin`) maps to one CSV file, read
and written with Python's built-in `csv` module.

## Tech stack

Python 3 · Flask · HTML5 · CSS3 (custom design system, no framework) ·
Jinja2 templating · CSV flat-file storage

## Project structure

```
edusmart/
├── app.py                 # Flask app: routes, CSV I/O, auth
├── requirements.txt
├── data/                  # CSV "database"
├── static/css/style.css   # design system
└── templates/
    ├── base.html, login.html
    ├── student/            # 6 pages
    ├── teacher/            # 6 pages
    └── admin/              # 8 pages
```
