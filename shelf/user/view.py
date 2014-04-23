from ..admin.view import ShelfModelView
from wtforms.fields.html5 import EmailField
import wtforms
from flask.ext.admin.helpers import get_form_data

import flask_login

import shelf.user
login = shelf.user.login

from flask import flash

from ..model import db

class CreateUserForm(wtforms.Form):
    id = wtforms.HiddenField()
    firstname = wtforms.TextField()
    lastname = wtforms.TextField()
    email = EmailField()

class AdminEditOwnUserForm(wtforms.Form):
    id = wtforms.HiddenField()
    firstname = wtforms.TextField()
    lastname = wtforms.TextField()
    profile = wtforms.SelectField(choices=(("Subscriber", "Subscriber"), 
                                            ("Contributor", "Contributor"), 
                                            ("Author", "Author"), 
                                            ("Editor", "Editor"), 
                                            ("Admin", "Admin")))
    email = EmailField()
    pw = wtforms.PasswordField("Change password")
    confirm_pw = wtforms.PasswordField("Password confirmation")
    is_active = wtforms.BooleanField()

class AdminEditUserForm(wtforms.Form):
    id = wtforms.HiddenField()
    firstname = wtforms.TextField()
    lastname = wtforms.TextField()
    profile = wtforms.SelectField(choices=(("Subscriber", "Subscriber"), 
                                            ("Contributor", "Contributor"), 
                                            ("Author", "Author"), 
                                            ("Editor", "Editor"), 
                                            ("Admin", "Admin")))
    email = EmailField()
    is_active = wtforms.BooleanField()

class EditOwnUserForm(wtforms.Form):
    id = wtforms.HiddenField()
    firstname = wtforms.TextField()
    lastname = wtforms.TextField()
    email = EmailField()
    pw = wtforms.PasswordField("Change password")
    confirm_pw = wtforms.PasswordField("Password confirmation")

class ShelfUserView(ShelfModelView):
    column_list = ('email', 'profile')

    def create_form(self, obj=None):
        return CreateUserForm()

    def on_model_change(self, form, model, is_created):
        if is_created:
            #Ajout d'un utilisateur
            pass
        else:
            if isinstance(form, AdminEditOwnUserForm) or isinstance(form, EditOwnUserForm):
                if form.pw.data and form.pw.data == form.confirm_pw.data:
                    hashpw = login.generate_password_hash(form.pw.data)
                    user = current_user
                    user.hashpw = hashpw
                    db.session.commit()
                    flash("Password has been changed")
                elif form.pw.data:
                    flash("Different passwords", "error")

    def edit_form(self, obj):
        if obj.profile == "Admin" and obj == flask_login.current_user:
            return AdminEditOwnUserForm(get_form_data(), obj=obj)
        if flask_login.current_user.profile == "Admin":
            return AdminEditUserForm(get_form_data(), obj=obj)
        elif obj == flask_login.current_user:
            return EditOwnUserForm(get_form_data(), obj=obj)
        