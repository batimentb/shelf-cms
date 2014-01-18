from flask.ext.admin import Admin
from flask import Blueprint, render_template, request, redirect

from flask.ext.admin.base import expose, AdminIndexView
import wtforms
from flask_wtf import Form
from flask.ext.login import LoginManager, login_user, UserMixin, login_required

class User(UserMixin):
    pass

login_manager = LoginManager()

@login_manager.user_loader
def load_user(userid):
    user = User()
    user.id = userid
    return user

login_manager.login_view = "/admin/login/"

class LoginForm(Form):
        email = wtforms.fields.TextField("Email")
        password = wtforms.fields.PasswordField("Password")


class ShelfIndexView(AdminIndexView):
    @expose('/login/', methods=("GET", "POST"))
    def login(self):
        form = LoginForm(request.form)
        print form.data
        if form.validate_on_submit():
            user = User()
            user.id = u"1"
            login_user(user)
            #flash("Logged in successfully.")
            print "REDIRECT TO:", request.args.get("next")
            return redirect(request.args.get("next") or url_for("admin.index"))
        return render_template("shelf-admin/login.html", form=form)

    @expose()
    @login_required
    def index(self):
        return self.render(self._template)




class ShelfAdmin(Admin):
    def __init__(self, app=None, name=None,
                 url=None, subdomain=None,
                 index_view=None,
                 translations_path=None,
                 endpoint=None,
                 static_url_path=None,
                 base_template=None):
        if base_template is None:
            base_template = "shelf-admin/base.html"
        if index_view is None:
            index_view = ShelfIndexView(endpoint=endpoint, url=url)
        super(ShelfAdmin, self).__init__(app, name, url, subdomain, 
            index_view, translations_path, 
            endpoint, static_url_path, base_template)

    def _init_extension(self):
        super(ShelfAdmin, self)._init_extension()
        shelf_admin = Blueprint('shelf', 'shelf', url_prefix="/shelf", 
            template_folder="templates", static_folder="static")
        self.app.register_blueprint(shelf_admin)
        login_manager.init_app(self.app)
    
    