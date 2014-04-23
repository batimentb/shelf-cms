import shelf.model
from sqlalchemy import event
from sqlalchemy.sql import func

db = shelf.model.db

class WorkflowMixin:
    shelf_state = db.Column(db.Enum("draft", "private", "public"))

class OrderableMixin:
    shelf_order = db.Column(db.Integer)

    @staticmethod
    def create_order(mapper, connection, target):
        last = target.__class__.query.order_by(target.__class__.id.desc()).first()
        target.shelf_order = last.id + 1 if last else 1

    @classmethod
    def __declare_last__(cls):
        event.listen(cls, 'before_insert', cls.create_order)

class LocalizedString(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lang = db.Column(db.String(2))
    value = db.Column(db.String(255))
    trad = db.relationship('LocalizedString', lazy="joined", backref=db.backref("parent", remote_side=[id]))
    parent_id = db.Column(db.Integer, db.ForeignKey('localized_string.id'))

class LocalizedText(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lang = db.Column(db.String(2))
    value = db.Column(db.Text)
    trad = db.relationship('LocalizedText', lazy="joined", backref=db.backref("parent", remote_side=[id]))
    parent_id = db.Column(db.Integer, db.ForeignKey('localized_text.id'))

class RemoteFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255))

class Picture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255))
    x = db.Column(db.Integer)
    y = db.Column(db.Integer)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    thumbs = db.relationship('Picture')
    parent_id = db.Column(db.Integer, db.ForeignKey('picture.id'))

class Marker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    longitude = db.Column(db.Float)
    latitude = db.Column(db.Float)

class Page(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(50))
    title_id = db.Column(db.Integer, db.ForeignKey('localized_string.id'))
    title = db.relationship('LocalizedString', lazy="joined", foreign_keys=(title_id,))
    description_id = db.Column(db.Integer, db.ForeignKey('localized_string.id'))
    description = db.relationship('LocalizedString', lazy="joined", foreign_keys=(description_id,))

    __mapper_args__ = {
        'polymorphic_on': name,
        'polymorphic_identity': 'page'
    }