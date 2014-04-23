from flask_admin import Admin
from view import DashboardView, Library
from flask_admin.base import MenuItem
import os.path as op

class ShelfAdmin(Admin):
    def __init__(self, app=None, name=None,
                 url=None, subdomain=None,
                 index_view=None,
                 translations_path=None,
                 endpoint=None,
                 static_url_path=None, 
                 base_template=None, shelf=None):
        if base_template is None:
            base_template = "shelf/base/base.html"
        if index_view is None:
            index_view = DashboardView(name="Dashboard", endpoint=endpoint, url=url, template='shelf/base/dashboard.html')
        super(ShelfAdmin, self).__init__(app, name, url, subdomain, 
            index_view, translations_path, 
            endpoint, static_url_path, base_template)
        if shelf:
            self.shelf = shelf
        if app:
            if "SHELF_LIBRARY_FOLDER" in app.config:
                self.library = Library(app.config["SHELF_LIBRARY_FOLDER"], "/"+app.config["SHELF_LIBRARY_FOLDER"]+"/", name="Files")
            else:
                self.library = Library('static', "/static/", name="Files")
        if app:
            app.register_blueprint(self.library.create_blueprint(self))         

    def add_widget(self, view):
        self.index_view.add_widget(view)

    def add_setting(self, view):
    	pass

    def menu(self):
        tmp = super(ShelfAdmin, self).menu()
        content = tmp[2:]
        content_item = MenuItem("Content")
        library_item = MenuItem(self.library.name, view=self.library)
        for c in content:
            content_item.add_child(c)
        return [tmp[0], content_item, library_item]
    	#return super(ShelfAdmin, self).menu()

    def menu_links(self):
    	return super(ShelfAdmin, self).menu_links()

    def content(self):
        return super(ShelfAdmin, self).menu()[2:]