from flask import Blueprint
from shelf.admin.view import SQLAModelView
from flask.ext.admin.contrib.sqla import form as contribform
from flask.ext.admin.helpers import get_form_data

config = {
    "name": "Page",
    "description": "Manage content of your pages",
}

class PageModelView(SQLAModelView):
    edit_template = "page-admin-edit.html"
    form_excluded_columns = ("name",)
    subclass = {}

    def edit_form(self, obj=None):
        """
            Instantiate model editing form and return it.

            Override to implement custom behavior.
        """
        if not obj:
            raise ValueError

        view_subclass = self.subclass.get(obj.__class__)
        if view_subclass and view_subclass != self.__class__:
            view = view_subclass(obj.__class__, self.session)
            return view.edit_form(obj)

        return self._edit_form_class(get_form_data(), obj=obj)

class PageModelMixin:
    def get_title(self):
        return self.title

    def get_description(self):
        return self.description

    def get_name(self):
        return self.name

class Page:
    def __init__(self):
        self.config = config

    def init_app(self, app):
        self.bp = Blueprint("page", __name__, url_prefix="/page",
            static_folder="static", template_folder="templates")
        app.register_blueprint(self.bp)

    def register_pages(self, app, db):
        pages = app.config.get("SHELF_PAGES", {})
        for url in pages:
            if isinstance(pages[url], tuple):
                cls, view = pages[url]
                PageModelView.subclass[cls] = view
            elif issubclass(pages[url], PageModelMixin):
                cls = pages[url]
            if cls.query.count() == 0:
                model = cls()
                db.session.add(model)
        db.session.commit()


