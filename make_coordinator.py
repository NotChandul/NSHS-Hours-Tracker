"""
One-time helper: change a registered user's role.

Usage:
    python make_coordinator.py <student_id>              (promotes to coordinator)
    python make_coordinator.py <student_id> student       (demotes back to student)
"""
import sys
from app import app
from models import db, User

if len(sys.argv) < 2:
    print("Usage: python make_coordinator.py <student_id> [role]")
    sys.exit(1)

student_id = sys.argv[1]
role = sys.argv[2] if len(sys.argv) > 2 else 'coordinator'

if role not in ('student', 'coordinator'):
    print("Role must be 'student' or 'coordinator'.")
    sys.exit(1)

with app.app_context():
    user = User.query.filter_by(student_id=student_id).first()
    if not user:
        print(f"No user found with student ID {student_id}.")
        sys.exit(1)
    user.role = role
    db.session.commit()
    print(f"{user.name} ({student_id}) is now a {role}.")