# NSHS Service Hours Tracker

A small Flask web app for the National Science Honors Society to replace the
current workflow of physical paper slips to track student service hours. Students submit hours digitally; a
coordinator approves or rejects them; approved hours count toward each
student's total.

## Project structure

```
nshs-hours-tracker/
├── app.py                    # routes + app setup
├── models.py                 # database tables: User, HourSubmission, Announcement
├── forms.py                  # WTForms (validation + CSRF protection)
├── make_coordinator.py       # one-time helper to promote a user to coordinator
├── requirements.txt
├── templates/
│   ├── _coordinator_header_actions.html
│   ├── account_approvals.html
│   ├── add_hours.html
│   ├── announcements.html
│   ├── auth_base.html
│   ├── base.html
│   ├── coordinator_dashboard.html
│   ├── home.html
│   ├── login.html
│   ├── public_base.html
│   ├── register.html
│   ├── reset_password.html
│   ├── semester_admin.html
│   ├── student_base.html
│   ├── student_dashboard.html
│   ├── student_master.html
│
└── static/css/style.css
```

## Running it locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. The first run creates `nshs_tracker.db`
automatically (a local SQLite file) — that's your database, no setup needed.

## Setting up your first coordinator

The very first account created on the website will automatically promote to the coordinator role. Each account that is registered afterward has to be approved by the coordinator and will be given the role of a student. The coordinator has the ability to promote other accounts to the coordinator level and have the ability to remove accounts from the database of students. There will always be one coordinator account active at all times.

Every new account registers as a `student` on purpose, so nobody can
self-promote into the coordinator role. To make yourself (or a teacher)
a coordinator:

1. Register a normal account on the site.
2. In the terminal, run:
   ```bash
   python make_coordinator.py your-email@school.edu
   ```
3. Log out and back in — you'll now land on the coordinator dashboard.

## Before you deploy this publicly

- Move `SECRET_KEY` out of `app.py` and into an environment variable.
- Turn off `debug=True` in production.
- Double check with your sponsor teacher / school IT that storing student
  names and activity records on your chosen free host is fine under school
  policy.

See the security checklist from earlier in this build for the full list.

# to reset the database, enter into the venv terminal on vscode,
#python -c "from app import app; from models import db; app.app_context().push(); db.drop_all(); db.create_all(); print('Database reset.')"

## NOTICE

This web application was made with the help of AI GENERATED CODE, - Claude Code. This project was simply an application that allows me to help out a school club I am apart of while being able to experiment with AI. Instead of taking on the role of creating each line of code, I instead took the chance to act as a lead developer/project manager. 

Through this project I was able to debug and tweak any of the code that was generated. I was able to improve my problem solving and critical thinking skills while working on this project. I ran into issues such as website security, responsiveness on different screens, and errors when students submit hours into the portal.

## How has this project helped the club

This project is currently used by ____ members and _____ faculty members apart of the National Science Honors Society at Northwest High School. Before this application was created, coordinators tracking hours would use a google spread sheet and document each students service hours through physical paper slips. With this method of tracking hours, the spread sheet was often times not updated frequently or paper slips that students turned in would end up being lost or never entered into the spread sheet.

I personally spent an entire 45 minute lunch break going through a stack of student slips and entering them into the google spread sheet. It was tedious and time-consuming, having to find each individual student and enter their hours. 

This project eliminates both time consumption and lost slip issues. By allowing students to create an account at the begining of the school year, they can request and track their progress throughout the year wihtout having to wonder if they have enough hours before the end of each semester. This project also lets coordinators efficiently accept each request that students make with just a click of a button. 



