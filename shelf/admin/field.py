from .widget import ShelfInlineFieldListWidget, ShelfInlineFormWidget
from flask.ext.admin.contrib.sqla.fields import InlineModelFormList
from flask.ext.admin.model.fields import InlineModelFormField

_unset_value = object()

class ShelfInlineModelFormField(InlineModelFormField):
    widget = ShelfInlineFormWidget()

class ShelfInlineFieldList(InlineModelFormList):
    widget = ShelfInlineFieldListWidget()

    form_field_type = ShelfInlineModelFormField

    def process(self, formdata, data=_unset_value):
        res = super(ShelfInlineFieldList, self).process(formdata, data)
        titles = [obj.get_title() for obj in data]
        for i in range(len(self.entries)):
            f = self.entries[i]
            try:
                title = titles[i]
            except IndexError:
                pass
            f.label = title