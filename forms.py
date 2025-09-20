# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FileField, SubmitField
from wtforms.validators import DataRequired, Length

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CloneCreationForm(FlaskForm):
    text_file = FileField('Upload Text Messages File (optional, .txt)')
    profile_pic = FileField('Upload Profile Picture (optional, .jpg, .png, .jpeg)')
    submit = SubmitField('Create Clone')