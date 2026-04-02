from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from src import mysql

class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=5, max=25)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=25)])
    confirmPassword = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Create Account")

    def validate_email(self, email):
        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id FROM Users WHERE email=%s", (email.data,))
        if cur.fetchone():
            raise ValidationError("Email is already in use.")
        cur.close()

    def validate_username(self, username):
        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id FROM Users WHERE username=%s", (username.data,))
        if cur.fetchone():
            raise ValidationError("Username is already taken.")
        cur.close()

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=5, max=20)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")