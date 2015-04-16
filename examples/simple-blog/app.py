from flask import Flask

from shelf import Shelf
from shelf.plugins.library import FileAdmin

import admin
import model

app = Flask(__name__)
app.debug = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SECRET_KEY'] = 'notasecret'
app.config['SECURITY_REGISTERABLE'] = True
app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'
app.config['SECURITY_PASSWORD_SALT'] = 'mysalt'#"hash_123678*",
app.config['SECURITY_REGISTER_EMAIL'] = False
model.db.init_app(app)
model.db.app = app

shlf = Shelf(app)
shlf.init_db(model.db)
shlf.init_admin()
shlf.init_security(model.User, model.Role)
shlf.load_plugins((
    "shelf.plugins.wysiwyg",
    "shelf.plugins.workflow",
    "shelf.plugins.library"
))
shlf.admin.add_view(admin.PostModelView(model.Post, model.db.session))
shlf.admin.add_view(FileAdmin("static/", name="Media"))
shlf.setup_plugins()
app.run('0.0.0.0')