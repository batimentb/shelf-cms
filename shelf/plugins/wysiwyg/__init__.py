from flask import flash, Blueprint, render_template, render_template_string, current_app
from wtforms.widgets import TextArea
from wtforms.fields import TextAreaField

class WysiwygViewMixin:
    pass

config = {
    "name": "Wysiwyg",
    "description": "TinyMCE based fields for the administration.",
    "admin": {
        "view_subclass": WysiwygViewMixin,
        "template": {
            "modelview.edit_view": {
                "tail_js": "wysiwyg_tail.html"
            },
            "modelview.create_view": {
                "tail_js": "wysiwyg_tail.html"
            }
        }
    }
}


class BaseWysiwygTextArea(TextArea):
    class_name = None

    def __call__(self, *args, **kwargs):
        c = kwargs.pop('class', '') or kwargs.pop('class_', '')
        kwargs['class_'] = u'%s %s' % (self.class_name, c)
        return super(BaseWysiwygTextArea, self).__call__(*args, **kwargs)


class ClassicWysiwygTextArea(BaseWysiwygTextArea):
    class_name = "wysiwyg-classic"


class FullWysiwygTextArea(BaseWysiwygTextArea):
    class_name = "wysiwyg-full"


class LightWysiwygField(TextAreaField):
    pass


class ClassicWysiwygField(TextAreaField):
    widget = ClassicWysiwygTextArea()


class FullWysiwygField(TextAreaField):
    widget = FullWysiwygTextArea()


class Wysiwyg:
    def __init__(self):
        self.config = config

    def init_app(self, app):
        self.bp = Blueprint("wysiwyg", __name__, url_prefix="/wysiwyg", 
                static_folder="static", template_folder="templates")
        app.register_blueprint(self.bp)
