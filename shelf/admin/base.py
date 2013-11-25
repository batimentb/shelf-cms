from flask.ext.admin import Admin
from flask import Blueprint

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
        super(ShelfAdmin, self).__init__(app, name, url, subdomain, 
            index_view, translations_path, 
            endpoint, static_url_path, base_template)

    def _init_extension(self):
        super(ShelfAdmin, self)._init_extension()
        shelf_admin = Blueprint('shelf', 'shelf', url_prefix="/shelf", 
            template_folder="templates", static_folder="static")
        self.app.register_blueprint(shelf_admin)
