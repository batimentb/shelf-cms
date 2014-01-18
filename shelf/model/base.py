from sqlalchemy.ext.declarative import AbstractConcreteBase
from sqlalchemy.types import String, Integer, Text, Enum
from flask_sqlalchemy import SQLAlchemy

computed_models = {}
computed_pages = []

class ShelfSQLAlchemy(SQLAlchemy):
	def create_all(self):
		super(ShelfSQLAlchemy, self).create_all()
		for c in computed_pages:
			if self.session.query(c).count() == 0:
				self.session.add(c())
		self.session.commit()

db = ShelfSQLAlchemy()

def shelf_computed_models():
	return computed_models

def shelf_computed_model(cls):
	def get_full_dict(obj):
		return dict(sum([cls.__dict__.items() for cls in obj.__bases__ if cls.__name__ != "object"], obj.__dict__.items()))

	if cls.__name__ not in computed_models:
		sc = cls
		name = sc.__name__
		params = {}
		for k, w in get_full_dict(sc).items():
			if k.startswith("__"):
				continue
			else:
				params[k] = w				
		computed_models[name] = type(sc.__name__, (db.Model,), params)
	return computed_models[cls.__name__]

def shelf_db():
	return db

class ShelfColumn:
	class_name = None

	def __init__(self, *args, **kwargs):
		self.class_name = args[0]

class ShelfOneToOne(ShelfColumn):
	pass

class ShelfOneToMany(ShelfColumn):
	pass

class ShelfManyToMany(ShelfColumn):
	pass

'''class Coordinate:
	longitude = String(20)
	latitude = String(20)

class Picture:
	path = String(255)
	width = Integer
	height = Integer

class FullSlide:
	picture = ShelfColumn(Picture)
	position = Integer
	share = String(255)
	video = String(255)
	legend = Text

class FullSlider:
	mode = Enum("fade", "slide")
	slides = ShelfOneToMany(FullSlide)

class Tag:
	name = String(255)

class RemoteFile:
	path = String(255)'''

'''class LocalizedString(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	lang = db.Column(String(2))
	value = db.Column(String(255))
	trad = db.relationship('LocalizedString')
	parent_id = db.Column(db.Integer, db.ForeignKey('localized_string.id'))'''

class LocalizedString:
    id = db.Column(db.Integer, primary_key=True)
    lang = db.Column(db.String(2))
    value = db.Column(db.String(255))
    trad = db.relationship('LocalizedString', backref=db.backref("parent", remote_side=[id]))
    parent_id = db.Column(db.Integer, db.ForeignKey('localized_string.id'))

class LocalizedText:
    id = db.Column(db.Integer, primary_key=True)
    lang = db.Column(db.String(2))
    value = db.Column(db.Text)
    trad = db.relationship('LocalizedText', backref=db.backref("parent", remote_side=[id]))
    parent_id = db.Column(db.Integer, db.ForeignKey('localized_text.id'))

class RemoteFile:
	id = db.Column(db.Integer, primary_key=True)
	path = db.Column(db.String(255))

class Picture:
	id = db.Column(db.Integer, primary_key=True)
	path = db.Column(db.String(255))
	x = db.Column(db.Integer)
	y = db.Column(db.Integer)
	width = db.Column(db.Integer)
	height = db.Column(db.Integer)
	thumbs = db.relationship('Picture')
	parent_id = db.Column(db.Integer, db.ForeignKey('picture.id'))

class Marker:
	id = db.Column(db.Integer, primary_key=True)
	longitude = db.Column(db.Float)
	latitude = db.Column(db.Float)

class Page(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	name = db.Column(db.String(50))

	__mapper_args__ = {
		'polymorphic_on': name,
		'polymorphic_identity': 'page'
	}


def register_page(model, db, name=None, view=None):
	params = {}
	for k, v in model.__dict__.items():
		if k.startswith('_'):
			continue
		params[k] = v

	params['__mapper_args__'] = {'polymorphic_identity': name if name else model.__name__.lower() }
	computed_models[model.__name__] = type(model.__name__, (Page,), params)

	prepare_model(computed_models[model.__name__], db)
	if computed_models[model.__name__] not in computed_pages:
		computed_pages.append(computed_models[model.__name__])
	


def prepare_model(model, db):
	compute_model = True
	while compute_model:
		compute_model = False
		tmp = model.__dict__.copy()
		for col in tmp:
			if col.startswith("__"):
				continue
			val = tmp[col]
			if isinstance(val, ShelfOneToOne):
				mod = shelf_computed_model(val.class_name)
				setattr(model, col+"_id", db.Column(db.Integer, db.ForeignKey(mod.__tablename__ + ".id")))
				setattr(model, col, db.relationship(mod, foreign_keys=(getattr(model, col+"_id"),)))
			elif isinstance(val, ShelfOneToMany):
				name = model.__name__ + val.class_name.__name__
				if name in computed_models:
					mod = computed_models[name]
				else:
					basemod = shelf_computed_model(val.class_name)
					params = { 
						'id': db.Column(db.Integer, db.ForeignKey(basemod.__tablename__ + ".id"), primary_key=True),
					}
					params[model.__tablename__+"_id"] = db.Column(db.Integer, db.ForeignKey(model.__tablename__ + ".id"))
					mod = type(name, (basemod,), params)
					computed_models[name] = mod
				setattr(model, col, db.relationship(mod, backref=mod.__tablename__))
			'''elif isinstance(val, ShelfManyToMany):				
				secondary_table_name = model.__tablename__ + "_" + col
				mod = shelf_computed_model(val.class_name)
				prepare_model(mod, db)
				computed_models[name] = mod

				setattr(mod, model.__tablename__, db.relationship(model, secondary=secondary_table_name))
				setattr(model, col, db.relationship(mod, secondary=secondary_table_name))

				hoho = db.Table(secondary_table_name,
					db.Column(model.__tablename__ + "_id", db.Integer, db.ForeignKey(model.__tablename__ + ".id")),
					db.Column(mod.__tablename__ + "_id", db.Integer, db.ForeignKey(mod.__tablename__ + ".id"))
				)

			elif isinstance(val, ShelfColumn):
				sc = val.class_name
				for k, w in sc.__dict__.iteritems():
					if k.startswith("__"):
						continue
					if not isinstance(w, ShelfColumn):
						setattr(model, col + "_" + k, db.Column(w))
					else:
						setattr(model, col + "_" + k, w)
				delattr(model, col)'''
		for col in tmp.values():
			if isinstance(col, ShelfColumn) or isinstance(col, ShelfOneToMany):
				compute_model = True
				break
			