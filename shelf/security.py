from flask.ext.principal import Principal, Identity, AnonymousIdentity, identity_changed, Permission, RoleNeed
from flask.ext.login import LoginManager, login_user, UserMixin, login_required

from model.user import User

from form.user import LoginForm, RecoverForm, RegisterForm

from flask.ext.bcrypt import Bcrypt

login_manager = LoginManager()
login_bcrypt = Bcrypt()

@login_manager.user_loader
def load_user(userid):
    user = User()
    user.id = userid
    return user

def validate_register_on_submit(form):
    form = RegisterForm(form)
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first()
        pw_hash = login_bcrypt.generate_password_hash(form.password.data)
        if not user:
            user = User(email=form.email.data, password_hash=pw_hash, active=False)
            db.session.add()
            db.session.commit()
            flash("Account will soon be activated by admin", "error")
        else:
            user.active = True
            db.session.commit()
            flash("Account is now activated", "error")
        return True
    else:
        return False

def validate_recover_on_submit(form):
    form = RecoverForm(form)
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("User does not exist", "error")
            return False
        elif not user.active:
            flash("User is not active", "error")
            return False
        else:
            user.active = False
            db.session.commit()
            flash("You will soon receive your new password")
            return True
    else:
        return False

def validate_login_on_submit(form):
    form = LoginForm(form)
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("User does not exist", "error")
            return False
        pw_hash = form.password.data
        candidate = 'secret'        
        if not pw_hash:
            flash("Missing password", "error")
            return False
        if not login_bcrypt.check_password_hash(candidate, pw_hash):
            flash("Bas password", "error")
            return False
        login_user(user)
        return True
    return False

login_manager.login_view = "/admin/login/"