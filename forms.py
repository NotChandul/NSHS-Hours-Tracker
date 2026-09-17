from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, DateField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange, Regexp

STUDENT_ID_VALIDATORS = [
    DataRequired(),
    Regexp(r'^\d{6,8}$', message='Student ID must be 6 to 8 digits, numbers only.')
]


class RegistrationForm(FlaskForm):
    student_id = StringField('Student ID', validators=STUDENT_ID_VALIDATORS)
    name = StringField('Full name', validators=[DataRequired(), Length(max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        'Confirm password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match.')]
    )


class LoginForm(FlaskForm):
    student_id = StringField('Student ID', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class HourSubmissionForm(FlaskForm):
    hours = FloatField(
        'Hours completed',
        validators=[DataRequired(), NumberRange(min=0.25, max=24, message='Enter a realistic number of hours.')]
    )
    date_completed = DateField('Date completed', validators=[DataRequired()])
    description = TextAreaField('What did you do?', validators=[Length(max=200)])


class AnnouncementForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    body = TextAreaField('Announcement', validators=[DataRequired()])


class AddStudentForm(FlaskForm):
    """Coordinator-only: pre-register a student with a temporary password."""
    student_id = StringField('Student ID', validators=STUDENT_ID_VALIDATORS)
    name = StringField('Full name', validators=[DataRequired(), Length(max=100)])
    password = PasswordField('Temporary password', validators=[DataRequired(), Length(min=8)])


class ManualHoursForm(FlaskForm):
    """Coordinator-only: add already-approved hours directly to a student's profile."""
    hours = FloatField(
        'Hours to add',
        validators=[DataRequired(), NumberRange(min=0.25, max=24, message='Enter a realistic number of hours.')]
    )
    date_completed = DateField('Date completed', validators=[DataRequired()])
    description = TextAreaField('Description (optional)', validators=[Length(max=200)])


class SemesterSettingsForm(FlaskForm):
    """Coordinator-only: update the club-wide semester label and required hours target."""
    semester_label = StringField('Semester Label', validators=[DataRequired(), Length(max=100)])
    target_hours = FloatField(
        'Required Semester Service Hours Target',
        validators=[DataRequired(), NumberRange(min=1, max=100)]
    )


class RoleActionForm(FlaskForm):
    """No fields — exists purely to carry a CSRF token for the promote/demote buttons."""
    pass


class ResetSemesterForm(FlaskForm):
    """No fields — exists purely to carry a CSRF token for the reset-semester button."""
    pass


class ConfirmActionForm(FlaskForm):
    """No fields — a reusable CSRF carrier for any button-only action: delete, wipe,
    approve, approve-all. These don't need their own input fields, just protection
    against a malicious site submitting the action on a coordinator's behalf."""
    pass


class ResetPasswordForm(FlaskForm):
    """Coordinator-only: set a brand new password for a student who lost access."""
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])