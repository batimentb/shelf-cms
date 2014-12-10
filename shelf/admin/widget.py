from flask.ext.admin.form import RenderTemplateWidget

class ShelfInlineFieldListWidget(RenderTemplateWidget):
    def __init__(self):
        super(ShelfInlineFieldListWidget, self).__init__('shelf/model/inline-field-list.html')

class ShelfInlineFormWidget(RenderTemplateWidget):
    def __init__(self):
        super(ShelfInlineFormWidget, self).__init__('shelf/model/inline-form.html')

    def __call__(self, field, **kwargs):
        kwargs.setdefault('form_opts', getattr(field, 'form_opts', None))
        return super(ShelfInlineFormWidget, self).__call__(field, **kwargs)
