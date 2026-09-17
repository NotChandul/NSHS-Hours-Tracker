from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(8), unique=True, nullable=False)  # MCPS ID, 6-8 digits
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='student')  # 'student' or 'coordinator'
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    # New self-registrations need a coordinator's approval before they can log in.
    # The very first account, and any account a coordinator creates directly, skip this.
    is_approved = db.Column(db.Boolean, default=False)

    # Brute-force protection: count failed attempts, and lock the account out
    # temporarily once too many happen in a row.
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

    semester_hours = db.Column(db.Float, default=0.0)     # progress toward this semester's minimum, resettable
    total_hours_year = db.Column(db.Float, default=0.0)   # cumulative hours for the whole school year, never auto-resets

    # cascade='all, delete-orphan' means deleting a User also deletes all of their
    # HourSubmission rows automatically -- no separate cleanup code needed.
    submissions = db.relationship('HourSubmission', backref='student', lazy=True, cascade='all, delete-orphan')


class HourSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hours = db.Column(db.Float, nullable=False)
    date_completed = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')   # 'pending', 'approved', 'rejected'
    source = db.Column(db.String(20), default='student')   # 'student' (submitted, needs approval) or 'coordinator' (added directly)
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class SemesterSettings(db.Model):
    """A single-row table holding club-wide settings: the target hours and the
    human-readable semester label shown in page headers (e.g. 'Fall 2026')."""
    id = db.Column(db.Integer, primary_key=True)
    target_hours = db.Column(db.Float, default=4.0)
    semester_label = db.Column(db.String(100), default='Current Semester')


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    posted_by = db.Column(db.Integer, db.ForeignKey('user.id'))