# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FileField, SubmitField
from wtforms.validators import DataRequired, Length
from wtforms.validators import InputRequired, Length, Optional

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
    name = StringField('Your Clone\'s Name', validators=[InputRequired(), Length(min=2, max=50)])
    submit = SubmitField('Create Clone')