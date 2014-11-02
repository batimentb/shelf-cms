from flask.ext.admin.form import RenderTemplateWidget
from flask import Blueprint
from flask.ext.admin.contrib.sqla.fields import InlineModelFormList
from flask.ext.admin.model.fields import InlineModelFormField
from flask.ext.admin.form.fields import Select2Field

_unset_value = object()

class OrderViewMixin:
    pass

config = {
    "name": "Order",
    "description": "Manage order of your models",
    "admin": {
        "view_subclass": OrderViewMixin,
        "template": {
            "modelview.edit_view": {
                "tail_js":"ordering-inline-tail.html"
            },
            "modelview.create_view": {
                "tail_js": "ordering-inline-tail.html"
            }
        }
    } 
}
'''"extend": {
    "admin": {
        "actions": "actions",
        "form": "form",
        "list_column": "list_column",
        "sortable_columns": "sortable_columns"
    },
    "view": {
        "modelview.list": {
            "tail_js": "tail",
            "head_css": "head"
        },
    }
    "security": ["sorter"]
},
"config": [
    "SHELF_ORDER_DESCEND"
]'''

class PositionField(Select2Field):
    pass

class Order:
    def __init__(self):
        self.config = config

    def init_app(self, app):
        self.bp = Blueprint("order", __name__, url_prefix="/order",
            static_folder="static", template_folder="templates")
        app.register_blueprint(self.bp)


class OrderingInlineFieldListWidget(RenderTemplateWidget):
    def __init__(self):
        super(OrderingInlineFieldListWidget, self).__init__('ordering-inline-field-list.html')

class OrderingInlineFormWidget(RenderTemplateWidget):
    def __init__(self):
        super(OrderingInlineFormWidget, self).__init__('ordering-inline-form.html')

    def __call__(self, field, **kwargs):
        kwargs.setdefault('form_opts', getattr(field, 'form_opts', None))
        return super(OrderingInlineFormWidget, self).__call__(field, **kwargs)


class OrderingModelMixin:
    def get_position(self, context=None):
        return self.position

    def set_position(self, position, context=None):
        self.position = position

    def get_position_attr(self, context=None):
        return "position"


class OrderingInlineModelFormField(InlineModelFormField):
    widget = OrderingInlineFormWidget()

    def is_position_field(self, name):
        return field == self.position_field

    def process(self, formdata, data=None):
        res = super(OrderingInlineModelFormField, self).process(formdata, data)
        for f in self.form:
            if isinstance(f, PositionField):
                self.position_field = f
                if data:
                    f.choices = [(i, i) for i in range(1, self.size_list+1)]
                else:
                    delattr(self.form, f.name)
        return res

class OrderingInlineFieldList(InlineModelFormList):
    widget = OrderingInlineFieldListWidget()

    form_field_type = OrderingInlineModelFormField

    def _add_entry(self, formdata=None, data=_unset_value, index=None):
        assert not self.max_entries or len(self.entries) < self.max_entries, \
            'You cannot have more than max_entries entries in this FieldList'
        new_index = self.last_index = index or (self.last_index + 1)
        name = '%s-%d' % (self.short_name, new_index)
        id   = '%s-%d' % (self.id, new_index)
        field = self.unbound_field.bind(form=None, name=name, prefix=self._prefix, id=id)
        field.size_list = self.size_list
        if hasattr(data, "get_inline_title"):
            field.inline_title = data.get_inline_title()
        if hasattr(data, "get_inline_thumbnail"):    
            field.inline_thumbnail = data.get_inline_thumbnail()
        field.process(formdata, data)
        self.entries.append(field)
        return field

    def process(self, formdata, data=_unset_value):
        self.entries = []
        if data is _unset_value or not data:
            try:
                data = self.default()
            except TypeError:
                data = self.default

        self.object_data = data

        if formdata:  
            indices = sorted(set(self._extract_indices(self.name, formdata)))
            if self.max_entries:
                indices = indices[:self.max_entries]

            idata = iter(data)
            self.size_list = len(indices)
            for index in indices:
                try:
                    obj_data = next(idata)
                except StopIteration:
                    obj_data = _unset_value
                self._add_entry(formdata, obj_data, index=index)
                key = 'del-%s-%d' % (self.id, index)
                self.entries[index]._should_delete = key in formdata
        else:
            self.size_list = len(data)
            for obj_data in data:
                new = self._add_entry(formdata, obj_data)                

        while len(self.entries) < self.min_entries:
            self._add_entry(formdata)

            
