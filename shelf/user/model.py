import shelf.model
import flask_login

db = shelf.model.db

class User(db.Model, flask_login.UserMixin):
	id = db.Column(db.Integer, primary_key=True)
	firstname = db.Column(db.String(50))
	lastname = db.Column(db.String(50))
	email = db.Column(db.String(50))
	hashpw = db.Column(db.String(60))
	profile = db.Column(db.Enum("Subscriber", "Contributor", "Author", "Editor", "Admin"))
	_mail_activated = db.Column("mail_activated", db.Boolean)
	_password_lost = db.Column("password_lost", db.Boolean)
	_is_active = db.Column("is_active", db.Boolean)

	def is_active(self):
		return self._is_active

	def can_admin(self):
		cans = ("Contributor", "Author", "Editor", "Admin")
		return self.profile and self.profile in cans