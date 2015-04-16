from flask import Blueprint
from os.path import basename
from wtforms.fields import TextField
from flask.ext.admin.form import RenderTemplateWidget
from shelf.admin.view import SQLAModelView
try:
    from wtforms.utils import unset_value
except:
    unset_value = object()

config = {
    "name": "Slider"
}

class SlideModelMixin:
    def get_picture(self):
        return self.picture

    def get_title(self):
        try:
            return basename(self.get_picture().get_path())
        except:
            return ""

class SliderModelMixin:
    def get_slides(self):
        return self.slides

    def get_slides_length(self):
        return len(self.slides)

    def get_slide(self, position):
        return self.slides[position]

    def thumbnail(self):
        return self.get_slide(0).get_picture()

    def __unicode__(self):
        if self.get_slides_length() < 2:
            return "%d slide" % self.get_slides_length()
        return "%d slides" % self.get_slides_length()

class SliderWidget(RenderTemplateWidget):
    def __init__(self):
        RenderTemplateWidget.__init__(self, "slider-field.html")

class SliderField(TextField):
    widget = SliderWidget()

    def populate_obj(self, obj, name):
        model = getattr(obj, name)
        if model is None:
            model = getattr(obj.__class__, name).mapper.class_()
            setattr(obj, name, model)

    def __init__(self, *args, **kwargs):
        if "allow_blank" in kwargs:
            del kwargs["allow_blank"]
        if "slider_view_endpoint" in kwargs:
            self.slider_view_endpoint = kwargs["slider_view_endpoint"]
            del kwargs["slider_view_endpoint"]
        TextField.__init__(self, *args, **kwargs)

class Slider:
    def __init__(self):
        self.config = config

    def init_app(self, app):
        self.bp = Blueprint("slider", __name__, url_prefix="/slider",
            static_folder="static", template_folder="templates")
        app.register_blueprint(self.bp)