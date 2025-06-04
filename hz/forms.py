from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class LoginForm(FlaskForm):
    email = StringField('E-Mail', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=4)])
    email = StringField('E-Mail', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[
        DataRequired(),
        Length(min=6, message='Минимальная длина пароля должна составлять 6 символов.')
    ])
    confirm_password = PasswordField('Подтверждение пароля', validators=[
        DataRequired(),
        EqualTo('password', message='Пароли должны совпадать.')
    ])
    submit = SubmitField('Зарегистрироваться')