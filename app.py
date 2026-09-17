import os
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

# All imports happen first
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, HourSubmission, Announcement, SemesterSettings
from forms import (
    RegistrationForm, LoginForm, HourSubmissionForm, AnnouncementForm,
    AddStudentForm, ManualHoursForm, SemesterSettingsForm, ResetSemesterForm,
    RoleActionForm, ConfirmActionForm, ResetPasswordForm
)

# Load environment variables
load_dotenv() 

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

# Initialize the app once
app = Flask(__name__)

# Use the environment variable for the secret key, with a fallback
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-later')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nshs_tracker.db'

db.init_app(app)

login_manager = LoginManager()

login_manager.login_view = 'login'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def coordinator_required():
    """Call at the top of any coordinator-only view. Blocks students even if they guess the URL."""
    if current_user.role != 'coordinator':
        abort(403)


def get_settings():
    """There's always exactly one settings row. Create it with defaults the first time it's needed."""
    settings = SemesterSettings.query.first()
    if not settings:
        settings = SemesterSettings()
        db.session.add(settings)
        db.session.commit()
    return settings


@app.context_processor
def inject_globals():
    """Makes these available in every template without passing them into each render_template() call."""
    settings = get_settings()

    today = date.today()
    if today.month >= 7:
        academic_year = f"{today.year}-{today.year + 1}"
    else:
        academic_year = f"{today.year - 1}-{today.year}"

    reset_form = None
    pending_approval_count = 0
    if current_user.is_authenticated and current_user.role == 'coordinator':
        reset_form = ResetSemesterForm()
        pending_approval_count = User.query.filter_by(is_approved=False).count()

    return dict(
        target_hours=settings.target_hours,
        semester_label=settings.semester_label,
        academic_year=academic_year,
        global_reset_form=reset_form,
        pending_approval_count=pending_approval_count
    )


# ---------- Public routes ----------

@app.route('/')
def home():
    latest = Announcement.query.order_by(Announcement.date_posted.desc()).limit(5).all()
    return render_template('home.html', announcements=latest)


@app.route('/announcements', methods=['GET', 'POST'])
def announcements():
    form = None
    if current_user.is_authenticated and current_user.role == 'coordinator':
        form = AnnouncementForm()
        if form.validate_on_submit():
            announcement = Announcement(
                title=form.title.data,
                body=form.body.data,
                posted_by=current_user.id
            )
            db.session.add(announcement)
            db.session.commit()
            flash('Announcement posted.', 'success')
            return redirect(url_for('announcements'))

    # Coordinators get the sidebar shell; everyone else gets the simple public bar.
    layout = 'base.html' if (current_user.is_authenticated and current_user.role == 'coordinator') else 'public_base.html'

    all_announcements = Announcement.query.order_by(Announcement.date_posted.desc()).all()
    return render_template('announcements.html', announcements=all_announcements, form=form, layout=layout)


# ---------- Auth routes ----------

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(student_id=form.student_id.data).first():
            flash('That student ID is already registered.', 'danger')
            return redirect(url_for('register'))

        # The very first account ever created becomes the coordinator automatically,
        # and is approved immediately since there's no one else around to approve it.
        # This means there's always at least one coordinator without needing
        # terminal/shell access on whatever server this ends up deployed on.
        is_first_account = User.query.count() == 0

        user = User(
            student_id=form.student_id.data,
            name=form.name.data,
            password_hash=generate_password_hash(form.password.data, method='pbkdf2:sha256'),
            role='coordinator' if is_first_account else 'student',
            is_approved=is_first_account
        )
        db.session.add(user)
        db.session.commit()

        if is_first_account:
            flash('Account created! As the first account on this site, you are now the coordinator.', 'success')
        else:
            flash('Account created. A coordinator needs to approve it before you can log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(student_id=form.student_id.data).first()

        # Locked out from too many recent failed attempts? Stop here, before even
        # checking the password, so the lockout can't be bypassed by guessing faster.
        if user and user.locked_until and user.locked_until > datetime.utcnow():
            minutes_left = int((user.locked_until - datetime.utcnow()).total_seconds() // 60) + 1
            flash(f'Too many failed attempts. Try again in about {minutes_left} minute(s).', 'danger')
            return render_template('login.html', form=form)

        if user and check_password_hash(user.password_hash, form.password.data):
            # Correct password -- clear any lockout tracking.
            user.failed_login_attempts = 0
            user.locked_until = None
            db.session.commit()

            if not user.is_approved:
                flash('Your account is still awaiting coordinator approval.', 'warning')
                return render_template('login.html', form=form)

            login_user(user)
            if user.role == 'coordinator':
                return redirect(url_for('coordinator_dashboard'))
            return redirect(url_for('student_dashboard'))

        # Wrong password. Only track attempts against a real account -- there's no
        # account to lock out if the student ID doesn't exist in the first place.
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                user.failed_login_attempts = 0
                db.session.commit()
                flash(f'Too many failed attempts. This account is locked for {LOCKOUT_MINUTES} minutes.', 'danger')
            else:
                db.session.commit()
                flash('Incorrect student ID or password.', 'danger')
        else:
            # Same generic message as a wrong password, so this never reveals
            # whether a given student ID is registered.
            flash('Incorrect student ID or password.', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


# ---------- Student routes ----------

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def student_dashboard():
    form = HourSubmissionForm()
    if form.validate_on_submit():
        submission = HourSubmission(
            hours=form.hours.data,
            date_completed=form.date_completed.data,
            description=form.description.data,
            user_id=current_user.id,
            source='student'
        )
        db.session.add(submission)
        db.session.commit()
        flash('Hours submitted for approval.', 'success')
        return redirect(url_for('student_dashboard'))

    my_submissions = HourSubmission.query.filter_by(user_id=current_user.id) \
        .order_by(HourSubmission.date_submitted.desc()).all()
    pending_hours = sum(s.hours for s in my_submissions if s.status == 'pending')
    latest_announcements = Announcement.query.order_by(Announcement.date_posted.desc()).limit(3).all()

    settings = get_settings()
    if settings.target_hours:
        progress_percent = round(min((current_user.semester_hours / settings.target_hours) * 100, 100))
    else:
        progress_percent = 0

    return render_template(
        'student_dashboard.html',
        form=form,
        submissions=my_submissions,
        pending_hours=pending_hours,
        announcements=latest_announcements,
        progress_percent=progress_percent
    )


# ---------- Coordinator routes: approval queue ----------

@app.route('/coordinator')
@login_required
def coordinator_dashboard():
    coordinator_required()

    pending = HourSubmission.query.filter_by(status='pending') \
        .order_by(HourSubmission.date_submitted.asc()).all()
    recent_history = HourSubmission.query.filter(HourSubmission.status != 'pending') \
        .order_by(HourSubmission.id.desc()).limit(5).all()

    return render_template('coordinator_dashboard.html', pending=pending, recent_history=recent_history)


@app.route('/coordinator/approve/<int:submission_id>')
@login_required
def approve_submission(submission_id):
    coordinator_required()
    submission = HourSubmission.query.get_or_404(submission_id)
    submission.status = 'approved'

    student = submission.student
    student.semester_hours += submission.hours
    student.total_hours_year += submission.hours

    db.session.commit()
    flash('Submission approved.', 'success')
    return redirect(url_for('coordinator_dashboard'))


@app.route('/coordinator/reject/<int:submission_id>')
@login_required
def reject_submission(submission_id):
    coordinator_required()
    submission = HourSubmission.query.get_or_404(submission_id)
    submission.status = 'rejected'
    db.session.commit()
    flash('Submission rejected — ask the student to resubmit.', 'warning')
    return redirect(url_for('coordinator_dashboard'))


# ---------- Coordinator routes: account approvals ----------

@app.route('/coordinator/approvals')
@login_required
def account_approvals():
    coordinator_required()
    pending = User.query.filter_by(is_approved=False).order_by(User.date_created.asc()).all()
    approve_form = ConfirmActionForm()
    return render_template('account_approvals.html', pending=pending, approve_form=approve_form)


@app.route('/coordinator/approvals/<int:user_id>/approve', methods=['POST'])
@login_required
def approve_account(user_id):
    coordinator_required()
    form = ConfirmActionForm()
    if form.validate_on_submit():
        user = User.query.get_or_404(user_id)
        user.is_approved = True
        db.session.commit()
        flash(f'{user.name} approved. They can now log in.', 'success')
    return redirect(url_for('account_approvals'))


@app.route('/coordinator/approvals/approve-all', methods=['POST'])
@login_required
def approve_all_accounts():
    coordinator_required()
    form = ConfirmActionForm()
    if form.validate_on_submit():
        pending = User.query.filter_by(is_approved=False).all()
        count = len(pending)
        for user in pending:
            user.is_approved = True
        db.session.commit()
        flash(f'Approved {count} account(s).', 'success')
    return redirect(url_for('account_approvals'))


# ---------- Coordinator routes: student roster ----------

@app.route('/coordinator/students')
@login_required
def students_master():
    coordinator_required()
    all_users = User.query.order_by(User.name.asc()).all()
    coordinator_count = User.query.filter_by(role='coordinator').count()
    role_form = RoleActionForm()
    return render_template(
        'students_master.html',
        all_users=all_users,
        coordinator_count=coordinator_count,
        role_form=role_form
    )


@app.route('/coordinator/students/<int:user_id>/promote', methods=['POST'])
@login_required
def promote_student(user_id):
    coordinator_required()
    form = RoleActionForm()
    if form.validate_on_submit():
        user = User.query.get_or_404(user_id)
        user.role = 'coordinator'
        db.session.commit()
        flash(f'{user.name} is now a coordinator.', 'success')
    return redirect(url_for('students_master'))


@app.route('/coordinator/students/<int:user_id>/demote', methods=['POST'])
@login_required
def demote_coordinator(user_id):
    coordinator_required()
    form = RoleActionForm()
    if form.validate_on_submit():
        user = User.query.get_or_404(user_id)
        coordinator_count = User.query.filter_by(role='coordinator').count()

        if user.role == 'coordinator' and coordinator_count <= 1:
            flash('Cannot demote the last remaining coordinator. Promote someone else first.', 'danger')
        else:
            user.role = 'student'
            db.session.commit()
            flash(f'{user.name} is now a student.', 'success')

    return redirect(url_for('students_master'))


@app.route('/coordinator/students/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_student(user_id):
    coordinator_required()
    form = ConfirmActionForm()
    if form.validate_on_submit():
        user = User.query.get_or_404(user_id)
        if user.role == 'coordinator':
            flash('Coordinators cannot be deleted this way. Demote them to a student first if needed.', 'danger')
        else:
            name = user.name
            db.session.delete(user)  # cascade='all, delete-orphan' also removes their HourSubmission rows
            db.session.commit()
            flash(f"{name}'s account and all of their hour records have been permanently deleted.", 'success')
    return redirect(url_for('students_master'))


@app.route('/coordinator/students/<int:user_id>/reset-password', methods=['GET', 'POST'])
@login_required
def reset_password(user_id):
    coordinator_required()
    student = User.query.get_or_404(user_id)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        student.password_hash = generate_password_hash(form.new_password.data, method='pbkdf2:sha256')
        student.failed_login_attempts = 0
        student.locked_until = None
        db.session.commit()
        flash(f'New password set for {student.name}. Share it with them directly.', 'success')
        return redirect(url_for('students_master'))
    return render_template('reset_password.html', form=form, student=student)


@app.route('/coordinator/students/<int:user_id>/add-hours', methods=['GET', 'POST'])
@login_required
def add_hours(user_id):
    coordinator_required()
    student = User.query.get_or_404(user_id) 
    form = ManualHoursForm()
    if form.validate_on_submit():
        submission = HourSubmission(
            hours=form.hours.data,
            date_completed=form.date_completed.data,
            description=form.description.data or 'Added directly by coordinator',
            user_id=student.id,
            status='approved',
            source='coordinator'
        )
        db.session.add(submission)
        student.semester_hours += form.hours.data
        student.total_hours_year += form.hours.data
        db.session.commit()
        flash(f'Added {form.hours.data} hours to {student.name}.', 'success')
        return redirect(url_for('students_master'))

    return render_template('add_hours.html', form=form, student=student)


# ---------- Coordinator routes: semester administration ----------

@app.route('/coordinator/semester-admin')
@login_required
def semester_admin():
    coordinator_required()
    settings = get_settings()
    settings_form = SemesterSettingsForm(
        semester_label=settings.semester_label,
        target_hours=settings.target_hours
    )
    add_form = AddStudentForm()
    wipe_form = ConfirmActionForm()
    return render_template('semester_admin.html', settings_form=settings_form, add_form=add_form, wipe_form=wipe_form)


@app.route('/coordinator/semester-admin/update', methods=['POST'])
@login_required
def update_semester_settings():
    coordinator_required()
    settings_form = SemesterSettingsForm()
    if settings_form.validate_on_submit():
        settings = get_settings()
        settings.semester_label = settings_form.semester_label.data
        settings.target_hours = settings_form.target_hours.data
        db.session.commit()
        flash('Semester settings updated.', 'success')
    return redirect(url_for('semester_admin'))


@app.route('/coordinator/students/add', methods=['POST'])
@login_required
def add_student():
    coordinator_required()
    form = AddStudentForm()
    if form.validate_on_submit():
        if User.query.filter_by(student_id=form.student_id.data).first():
            flash('That student ID is already registered.', 'danger')
            return redirect(url_for('semester_admin'))

        student = User(
            student_id=form.student_id.data,
            name=form.name.data,
            password_hash=generate_password_hash(form.password.data, method='pbkdf2:sha256'),
            role='student',
            is_approved=True
        )
        db.session.add(student)
        db.session.commit()
        flash(f'{student.name} was added. Share their student ID and the password you just set so they can log in.', 'success')
        return redirect(url_for('students_master'))

    # Validation failed — re-render the Semester Admin page so the errors are visible.
    settings = get_settings()
    settings_form = SemesterSettingsForm(
        semester_label=settings.semester_label,
        target_hours=settings.target_hours
    )
    wipe_form = ConfirmActionForm()
    return render_template('semester_admin.html', settings_form=settings_form, add_form=form, wipe_form=wipe_form)


@app.route('/coordinator/reset-semester', methods=['POST'])
@login_required
def reset_semester():
    coordinator_required()
    form = ResetSemesterForm()
    if form.validate_on_submit():
        User.query.filter_by(role='student').update({User.semester_hours: 0.0})
        db.session.commit()
        flash('Semester hours reset to 0 for every student. Yearly totals were not affected.', 'success')
    return redirect(url_for('students_master'))


@app.route('/coordinator/students/wipe-all', methods=['POST'])
@login_required
def wipe_all_students():
    coordinator_required()
    form = ConfirmActionForm()
    if form.validate_on_submit():
        students = User.query.filter_by(role='student').all()
        count = len(students)
        for student in students:
            db.session.delete(student)  # cascade also removes each student's HourSubmission rows
        db.session.commit()
        flash(f'Deleted {count} student account(s) and all of their hour records. Coordinator accounts were not affected.', 'success')
    return redirect(url_for('semester_admin'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode)