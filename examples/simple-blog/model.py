from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import UserMixin, RoleMixin

from shelf.plugins.library import PictureModelMixin
from shelf.plugins.workflow import WorkflowModelMixin, WORKFLOW_STATES

db = SQLAlchemy()

roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)

    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    email = db.Column(db.String(69), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())


class Picture(db.Model, PictureModelMixin):
    id = db.Column(db.Integer, primary_key=True)

    path = db.Column(db.String(255))


class Post(db.Model, WorkflowModelMixin):
    id = db.Column(db.Integer, primary_key=True)
    picture_id = db.Column(db.Integer, db.ForeignKey('picture.id'))

    picture = db.relationship("Picture")

    title = db.Column(db.String(150))
    content = db.Column(db.Text)
    state = db.Column(db.Enum(*WORKFLOW_STATES))