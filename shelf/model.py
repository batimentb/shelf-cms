import flask_sqlalchemy
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.ext.declarative.base import _declarative_constructor
from sqlalchemy.orm import ColumnProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import Table, MetaData, Column

db = None

class _VirtualColumn:
    class_name = None

    def __init__(self, *args, **kwargs):
        self.class_name = args[0]

class _Map(_VirtualColumn):
    pass

class _Array(_VirtualColumn):
    pass

class _Tags(_VirtualColumn):
    pass

class _ShelfBoundDeclarativeMeta(flask_sqlalchemy._BoundDeclarativeMeta):

    def __new__(cls, name, bases, d):
        tablename = d.get('__tablename__')

        # generate a table name automatically if it's missing and the
        # class dictionary declares a primary key.  We cannot always
        # attach a primary key to support model inheritance that does
        # not use joins.  We also don't want a table name if a whole
        # table is defined
        if not tablename and d.get('__table__') is None and \
                flask_sqlalchemy._defines_primary_key(d):
            def _join(match):
                word = match.group()
                if len(word) > 1:
                    return ('_%s_%s' % (word[:-1], word[-1])).lower()
                return '_' + word.lower()
            d['__tablename__'] = flask_sqlalchemy._camelcase_re.sub(_join, name).lstrip('_')

        if "Page" in [x.__name__ for x in bases]:
            def _join(match):
                word = match.group()
                if len(word) > 1:
                    return ('_%s_%s' % (word[:-1], word[-1])).lower()
                return '_' + word.lower()

            if hasattr(cls, "pagename"):
                name = cls.pagename
            else:
                name = flask_sqlalchemy._camelcase_re.sub(_join, name).lstrip('_').replace('_page', '').replace('_', '-')
            
            __mapper_args__ = {
                'polymorphic_identity': name
            }
            d['__mapper_args__'] = __mapper_args__
            
            for col in d:
                if col.startswith("__"):
                    continue
                val = d[col]
                if isinstance(val, Column):
                    val.name = name + "_" + col

            tmp = cls.__dict__.copy()
            for col in tmp:
                if col.startswith("__"):
                    continue
                if col in cls.__bases__[0].__dict__:
                    continue
                val = tmp[col]
                if isinstance(val, _Map):
                    setattr(cls, name+"_"+col, val)
                    delattr(cls, col)
                elif isinstance(val, _Array):
                    setattr(cls, name+"_"+col, val)
                    delattr(cls, col)
                elif isinstance(val, InstrumentedAttribute):
                    setattr(cls, name+"_"+col, val)
                    delattr(cls, col)

        return DeclarativeMeta.__new__(cls, name, bases, d)

    def __init__(self, name, bases, d):
        is_page = False
        for cls in bases:
            if cls.__name__ == "Page":
                is_page = True
                break
        if is_page:
            db.pages.add(self)

        super(_ShelfBoundDeclarativeMeta, self).__init__(name, bases, d)

        for attr in d.keys():
            val = d[attr]
            if isinstance(val, _Map) or isinstance(val, _Array) \
                                     or isinstance(val, _Tags):
                db.need_preprocessing.add(self)

class ShelfAlchemy(flask_sqlalchemy.SQLAlchemy):
    need_preprocessing = None
    pages = None

    class Computed(dict):
        classes = {}

        def __getattr__(self, attr):
            if attr in self.classes:
                return self.classes[attr]
            else:
                return None
    computed = Computed()

    def __init__(self, app=None,
                 use_native_unicode=True,
                 session_options=None):
        super(ShelfAlchemy, self).__init__(app, use_native_unicode, session_options)
        self.Map = _Map
        self.Array = _Array
        self.Tags = _Tags
        self.need_preprocessing = set([])
        self.pages = set([])

    def create_all(self):
        for cls in self.need_preprocessing:
            tmp = cls.__dict__.copy()

            for col in tmp:
                if col.startswith("__"):
                    continue
                val = tmp[col]
                if isinstance(val, _Map):
                    mod = val.class_name
                    '''if cls in self.pages:
                        def _join(match):
                            word = match.group()
                            if len(word) > 1:
                                return ('_%s_%s' % (word[:-1], word[-1])).lower()
                            return '_' + word.lower()
                        prefix = flask_sqlalchemy._camelcase_re.sub(_join, cls.__name__).lstrip('_').replace('_page', '')
                        setattr(cls, col+"_id", db.Column("%s_%s_id" % (prefix, col), db.Integer, db.ForeignKey(mod.__tablename__ + ".id")))
                        setattr(cls, col, db.relationship(mod, foreign_keys=(getattr(cls, col+"_id"),)))
                    else:'''
                    setattr(cls, col+"_id", db.Column(db.Integer, db.ForeignKey(mod.__tablename__ + ".id")))
                    setattr(cls, col, db.relationship(mod, foreign_keys=(getattr(cls, col+"_id"),), join_depth=2, lazy="joined"))
                elif isinstance(val, _Array):
                    name = cls.__name__ + val.class_name.__name__
                    if name in self.computed.classes:
                        mod = self.computed.classes[name]
                    else:
                        basemod = val.class_name
                        def _join(match):
                            word = match.group()
                            if len(word) > 1:
                                return ('_%s_%s' % (word[:-1], word[-1])).lower()
                            return '_' + word.lower()
                        params = {
                            'id': db.Column(db.Integer, db.ForeignKey(basemod.__tablename__ + ".id"), primary_key=True),
                            '__tablename__': flask_sqlalchemy._camelcase_re.sub(_join, name).lstrip('_')
                        }
                        params[cls.__tablename__+"_id"] = db.Column(db.Integer, db.ForeignKey(cls.__tablename__ + ".id"))
                        mod = type(name, (basemod,), params)
                        self.computed.classes[name] = mod
                    setattr(cls, col, db.relationship(mod, backref=mod.__tablename__, foreign_keys=(getattr(mod, cls.__tablename__+"_id"),)))

        super(ShelfAlchemy, self).create_all()

        for cls in self.pages:
            if self.session.query(cls).count() == 0:
                self.session.add(cls())
        self.session.commit()

        

    def make_declarative_base(self):
        base = declarative_base(cls=flask_sqlalchemy.Model, name='Model',
                                metaclass=_ShelfBoundDeclarativeMeta)
        base.query = flask_sqlalchemy._QueryProperty(self)
        return base

db = ShelfAlchemy()
