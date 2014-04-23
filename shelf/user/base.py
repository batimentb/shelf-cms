import flask_login
from flask.ext.bcrypt import Bcrypt
from functools import wraps
from flask import redirect, url_for, request

login = None

def shelf_login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if login._login_disabled:
            return func(*args, **kwargs)
        elif not flask_login.current_user.is_authenticated():
            return redirect(flask_login.login_url("admin.signin", request.url))
        elif not flask_login.current_user.can_admin():
        	return redirect(flask_login.login_url("admin.signin", request.url))
        return func(*args, **kwargs)
    return decorated_view

class ShelfLoginManager(flask_login.LoginManager):
	shelf = None
	bcrypt = None

	def generate_password_hash(self, pw):
		return self.bcrypt.generate_password_hash(pw)

	def check_password_hash(self, pw_hash, pw):
		return self.bcrypt.check_password_hash(pw_hash, pw)

	def __init__(self, app=None, add_context_processor=True, shelf=None):
		if shelf:
			self.shelf = shelf
		super(ShelfLoginManager, self).__init__(app, add_context_processor)

	def init_app(self, app, add_context_processor=True):
		super(ShelfLoginManager, self).init_app(app, add_context_processor)
		self.bcrypt = Bcrypt(app)

login = ShelfLoginManager()