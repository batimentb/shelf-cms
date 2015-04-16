from flask.ext.admin.contrib.sqla import form
from field import ShelfInlineFieldList
from shelf.plugins.order import OrderingInlineFieldList

class ModelConverter(form.AdminModelConverter):
	pass
	'''def convert(self, model, mapper, prop, field_args, hidden_pk):
		res = super(ModelConverter, self).convert(model, mapper, prop, field_args, hidden_pk)
		if field_args and "is_order" in field_args:
			del field_args["is_order"]
			res.short_name = "_is_order"
			print res
		return res'''

class InlineModelConverter(form.InlineModelConverter):
    inline_field_list_type = OrderingInlineFieldList