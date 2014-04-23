from wtforms.fields.html5 import EmailField
import wtforms
from model import User
from flask_login import login_user
from ..model import db
from base import login

class LoginForm(wtforms.Form):
	email = EmailField()
	password = wtforms.PasswordField()
	remember = wtforms.BooleanField()
	submit = wtforms.SubmitField()

class RegisterForm(wtforms.Form):
	email = EmailField()
	password = wtforms.PasswordField()
	check_password = wtforms.PasswordField()
	submit = wtforms.SubmitField()

class RecoverForm(wtforms.Form):
	email = EmailField()
	submit = wtforms.SubmitField()

def validate_recover_on_submit(form):
	form = RecoverForm(form)
	user = User.query.filter_by(email=form.email.data).first()
	if not user:
		return False
	return True

def validate_login_on_submit(form):
	form = LoginForm(form)
	user = User.query.filter_by(email=form.email.data).first()
	if not user:
		return False
	elif login.check_password_hash(user.hashpw, form.password.data):
		login_user(user, remember=form.remember.data)
		return True
	return False

def validate_register_on_submit(form):
	form = RegisterForm(form)
	if not form.email.data:
		return False
	if not form.password.data:
		return False
	if form.password.data != form.check_password.data:
		return False

	user = User.query.filter_by(email=form.email.data).first()
	if not user:
		user = User(email=form.email.data, _mail_activated=False, _is_active=True, _password_lost=False, 
			hashpw=login.generate_password_hash(form.password.data), profile="Subscriber")
		db.session.add(user)
		db.session.commit()
		return True
	elif not user._is_active:
		pw_hash = login.generate_password_hash(form.password.data)
		return True
	return False
