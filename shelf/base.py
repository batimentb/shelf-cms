from flask import Blueprint
import admin
from flask.ext.security import Security, SQLAlchemyUserDatastore, url_for_security
from security.view import UserModelView
from werkzeug.utils import import_string

class Shelf:
    """The Shelf object handles the admin, the plugins and the
    link between them"""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Init shelf with the app object"""
        self.app = app
        self.bp = Blueprint('shelf', 'shelf',
                            url_prefix="/shelf",
                            template_folder="templates",
                            static_folder="static")
        app.register_blueprint(self.bp)
        app.shelf = self 

    def init_admin(self, *args, **kwargs):
        adm = admin.Admin(self.app, *args, **kwargs)
        self.admin = adm

    def init_db(self, db):
        """Init shelf with the db object"""
        if self.app is None:
            raise ValueError
        self.db = db
        db.create_all()

    def init_security(self, user_cls, role_cls, datastore_cls=SQLAlchemyUserDatastore):
        self.user_datastore = datastore_cls(self.db, user_cls, role_cls)
        self.admin.add_view(UserModelView(user_cls, self.db.session))
        self.user_datastore.find_or_create_role("admin", description="Enable admin access")
        self.user_datastore.find_or_create_role("superadmin", description="Enable debug access")
        self.db.session.commit()

        if "SECURITY_LOGIN_USER_TEMPLATE" not in self.app.config:
            self.app.config["SECURITY_LOGIN_USER_TEMPLATE"] = "shelf-security/login.html"

        if "SECURITY_REGISTER_USER_TEMPLATE" not in self.app.config:
            self.app.config["SECURITY_REGISTER_USER_TEMPLATE"] = "shelf-security/register.html"

        if "SECURITY_FORGOT_PASSWORD_TEMPLATE" not in self.app.config:
            self.app.config["SECURITY_FORGOT_PASSWORD_TEMPLATE"] = "shelf-security/forgot_password.html"

        if "SECURITY_RESET_PASSWORD_TEMPLATE" not in self.app.config:
            self.app.config["SECURITY_RESET_PASSWORD_TEMPLATE"] = "shelf-security/reset_password.html"

        if "SECURITY_CHANGE_PASSWORD_TEMPLATE" not in self.app.config:
            self.app.config["SECURITY_CHANGE_PASSWORD_TEMPLATE"] = "shelf-security/change_password.html"

        if "SECURITY_SEND_CONFIRMATION_TEMPLATE" not in self.app.config:
            self.app.config["SECURITY_SEND_CONFIRMATION_TEMPLATE"] = "shelf-security/send_confirmation.html"

        if "SECURITY_POST_LOGIN_VIEW" not in self.app.config:
            self.app.config["SECURITY_POST_LOGIN_VIEW"] = "/admin/"

        if "SECURITY_POST_LOGOUT_VIEW" not in self.app.config:
            self.app.config["SECURITY_POST_LOGOUT_VIEW"] = "/login"

        self.security = Security(self.app, self.user_datastore)

    def load_plugins(self, plugins):
        self.plugins = []
        for plugin in plugins:
            try:
                package = import_string(plugin)
                name = package.config["name"]
                cls = getattr(package, name)
                instance = cls()
                instance.init_app(self.app)
                self.plugins.append(instance)

            except ImportError:
                raise ImportError(
                    "Could not import {0} plugin".format((plugin,))
                )

    def setup_plugins(self):
        for plugin in self.plugins:
            model_config = plugin.config.get("model")
            if model_config:
                subclass = model_config.get("model_subclass")
                view_subclass = model_config.get("view_subclass")
                sort_fct = model_config.get("sort")

                if sort_fct:
                    for view in self.admin._views: 
                        if isinstance(view, view_subclass):
                            view.extend_sort(subclass, sort_fct)

            admin_config = plugin.config.get("admin")
            if admin_config:
                subclass = admin_config.get("view_subclass")

                template_config = admin_config.get("template", {})
                for endpoint in template_config:
                    for block in template_config[endpoint]:
                        template = template_config[endpoint][block]
                        for view in self.admin._views:
                            if isinstance(view, subclass):
                                view.extend_view(endpoint, block, template)

                form_config = admin_config.get("form", {})
                for key in form_config:
                    for view in self.admin._views:
                        field, args = form_config[key]
                        for view in self.admin._views:
                            if isinstance(view, subclass):
                                view.extend_form(key, field, args)

            security_config = plugin.config.get("security")
            if security_config:
                roles_config = security_config.get("roles")
                for role, description in roles_config:
                    self.user_datastore.find_or_create_role(role, description=description)
                    self.db.session.commit()

            for view in self.admin._views:
                if hasattr(view, "_refresh_cache"):
                    view._refresh_cache()

    def get_plugin_by_class(self, cls):
        for plugin in self.plugins:
            if isinstance(plugin, cls):
                return plugin
        return None

