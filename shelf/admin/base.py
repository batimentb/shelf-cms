from flask.ext.admin import Admin
from flask import Blueprint, render_template, request, redirect, flash

from flask.ext.admin.base import expose, AdminIndexView
import wtforms
from flask_wtf import Form
from flask.ext.login import LoginManager, login_user, UserMixin, login_required

from shelf.contrib.analytics import Analytics
import datetime

class User(UserMixin):
    pass

login_manager = LoginManager()

@login_manager.user_loader
def load_user(userid):
    user = User()
    user.id = userid
    return user

login_manager.login_view = "/admin/login/"

analytics = Analytics("lol")

class LoginForm(Form):
        email = wtforms.fields.TextField("Email")
        password = wtforms.fields.PasswordField("Password")


class DashboardWidget:
    shouldUpdate = False
    template = None
    title = None

    def __init__(self, title):
        self.shouldUpdate = True
        self.template = None
        self.title = title

    def update(self):
        raise NotImplementedError

    def render(self):
        if self.shouldUpdate:
            self.update()
        if not self.template:
            raise NotImplementedError
        else:
            return render_template(self.template)


class TextDashboardWidget(DashboardWidget):
    def __init__(self, title, metric, icon=None):
        DashboardWidget.__init__(self, title)
        self.template = "shelf-admin/dashboard/simple-text.html"
        self.metric = metric
        if icon:
            self.icon = icon

    def update(self):
        current_month = analytics.get_stats((self.metric,), start=datetime.date.today() - datetime.timedelta(days=30))[self.metric]
        last_month = analytics.get_stats((self.metric,), start=datetime.date.today() - datetime.timedelta(days=60), end=datetime.date.today() - datetime.timedelta(days=30))[self.metric]

        self.data = current_month

        evolution = int(current_month) - int(last_month)
        if evolution > 0:
            self.legend = "<span class='value'>+{0} ({1}%)</span> since last month".format(evolution, round(100 * (abs(evolution) / float(current_month))))
        elif evolution < 0:
            self.legend = "<span class='value-bad'>-{0} ({1}%)</span> since last month".format(evolution, round(100 * (abs(evolution) / float(current_month))))
        else:
            self.legend = "Same than last month"

        self.shouldUpdate = False

    def render(self):
        if self.shouldUpdate:
            self.update()
        return render_template(self.template, title=self.title, legend=self.legend, data=self.data, icon=self.icon)


class ShelfIndexView(AdminIndexView):
    _template = "shelf-admin/index.html"
    widgets = []

    @expose('/login/', methods=("GET", "POST"))
    def login(self):
        form = LoginForm(request.form)
        if form.validate_on_submit():
            user = User()
            user.id = u"1"

            if form.password.data != "SigfoxWeb!31":
                flash("Bad email/password", "error")
                return render_template("shelf-admin/login.html", form=form)

            login_user(user)
            #flash("Logged in successfully.")
            print "REDIRECT TO:", request.args.get("next")
            return redirect(request.args.get("next") or url_for("admin.index"))
        return render_template("shelf-admin/login.html", form=form)

    @expose()
    @login_required
    def index(self):
        return self.render(self._template, widgets=[])

    def add_widget(self, view):
        if not self.widgets:
            self.widgets = []
        self.widgets.append(view)



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
            index_view = ShelfIndexView(endpoint=endpoint, url=url, template='shelf-admin/index.html')
        super(ShelfAdmin, self).__init__(app, name, url, subdomain, 
            index_view, translations_path, 
            endpoint, static_url_path, base_template)

    def _init_extension(self):
        super(ShelfAdmin, self)._init_extension()
        shelf_admin = Blueprint('shelf', 'shelf', url_prefix="/shelf", 
            template_folder="templates", static_folder="static")
        self.app.register_blueprint(shelf_admin)
        login_manager.init_app(self.app)

    def add_widget(self, view):
        self.index_view.add_widget(view)
    
    