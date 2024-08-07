from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email,regexp, EqualTo
from wtforms import ValidationError
from ..models import User

# form to get data for login
class LoginForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(),Length(1,64),Email()])
    password = PasswordField('Password',validators=[DataRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')
    
# form to get data for registration.
class RegistrationForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(),Length(1,64),Email()])
    username = StringField('Username', validators=[DataRequired(), Length(1,64), 
                                                   regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,
                                                          'username must have only letters, numbres, dots or underscores.')])
    password = PasswordField('Password',validators=[DataRequired(),EqualTo('password2',message='Password must match.')])
    password2 = PasswordField('Confirm password',validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered')
        
    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("Username already in use")