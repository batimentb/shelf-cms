from flask_admin.base import AdminIndexView, expose
from flask import Blueprint
from shelf.security.mixin import LoginMixin

config = {
    "name": "Dashboard",
    "description": "Dashboard-like view using tiles containing text and chart."
}

class DashboardView(LoginMixin, AdminIndexView):
    widgets = []

    def __init__(self, *args, **kwargs):
        if "template" not in kwargs:
            kwargs["template"] = "dashboard.html"
        return super(DashboardView, self).__init__(*args, **kwargs)

    def add_widget(self, view, provider=None):
        if not self.widgets:
            self.widgets = []
        if provider:
            view.provider = provider
        self.widgets.append(view)

    @expose("/")
    def index(self):
        return self.render(self._template, widgets=[w.render() for w in self.widgets])

class Dashboard:
    def __init__(self):
        self.config = config

    def init_app(self, app):
        self.bp = Blueprint("dashboard", __name__, url_prefix="/dashboard",
            static_folder="static", template_folder="templates")
        app.register_blueprint(self.bp)