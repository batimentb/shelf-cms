# -*- coding: utf-8 -*-

from wtforms.fields import TextField, TextAreaField
from wtforms.widgets import TextInput, TextArea
from flask.ext.admin.model.form import converts
from shelf.model.base import shelf_computed_models, db

import os.path as op
import os

from flask import render_template

class RemoteFileWidget(TextInput):
    def __call__(self, *args, **kwargs):
        return render_template("shelf-admin/field/remote-file.html", args=args[0])

class RemoteFileField(TextField):
    widget = RemoteFileWidget()

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = valuelist[0]

    def process_data(self, value):
        if value:
            self.data = value.path

    def populate_obj(self, obj, name):
        if getattr(obj, name) is None:
            setattr(obj, name, getattr(obj.__class__, name).mapper.class_(path=self.data))
            db.session.add(getattr(obj, name))
        else:
            getattr(obj, name).path = self.data

class PictureWidget(object):
    def __call__(self, *args, **kwargs):
        #for arg in args:
        #   print arg
        return render_template("shelf-admin/field/picture.html", args=args[0])

class PictureField(TextField):
    widget = PictureWidget()

    def __init__(self, label='', validators=None, ratio=None, formats=None, **kwargs):
        super(PictureField, self).__init__(label, validators, **kwargs)
        #self.picture_formats = formats
        #self.ratio = ratio

    def populate_obj(self, obj, name):
        if getattr(obj, name) is None:
            setattr(obj, name, getattr(obj.__class__, name).mapper.class_(path=self.data['path']))
            db.session.add(getattr(obj, name))
        else:
            getattr(obj, name).path = self.data['path']
        '''if len(self.data["source"]) == 0:
            return

        if getattr(obj, name) is not None:
            pic = getattr(obj, name)
            global_render = self.data["source"] != pic.source
        else:
            pic = Picture()
            db.session.add(pic)
            setattr(obj, name, pic)
            global_render = True
            
        for param in self.data:
            setattr(pic, param, self.data[param])
        
        if self.picture_formats:
            for idx, (name, max_height) in enumerate(self.picture_formats):
                size = (int(max_height * self.ratio), max_height)
                
                try:
                    format = pic.formats[idx]
                    format_render = format.width != size[0] or format.height != size[1]
                except IndexError:
                    format = PictureFormat()
                    pic.formats.append(format)
                    format_render = True
                format.name = name
                format.height = size[1]
                format.width = size[0]
                
                if global_render or format_render:
                    #im = Image.open(urllib.unquote(url_for('static', filename=pic.source)[1:]))
                    #im = im.convert('RGB').resize(size, Image.ANTIALIAS)
                    npath = 'elitis/thumbs/' + ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10)) + ".jpg"
                    if format.path and op.exists(op.join('static', format.path)):
                        os.remove(op.join('static', format.path))
                    #im.save(op.join('static', npath), 'JPEG', quality=95)
                    format.path = npath

            if len(self.picture_formats) < len(pic.formats):
                for idx in range(len(self.picture_formats), len(pic.formats)):
                    format = pic.formats.pop()
                    del format'''
            

    def process_formdata(self, valuelist):
        print valuelist
        if valuelist and valuelist[0] is not None:
            self.data = {"path": valuelist[0]}
        else:
            self.data = {"path": None}
        print self.data

    def process_data(self, value):
        if value:
            self.data = {"path": value.path}
        else:
            self.data = {"path": None}

class WysiwygTextWidget(TextArea):
    def __call__(self, *args, **kwargs):
        c = kwargs.pop('class', '') or kwargs.pop('class_', '')
        kwargs['class'] = u'%s %s' % ('wysiwyg', c)
        return super(WysiwygTextWidget, self).__call__(*args, **kwargs)

class WysiwygTextField(TextAreaField):
    widget = WysiwygTextWidget()

class LocalizedTextWidget(TextInput):
    def __call__(self, *args, **kwargs):
        return render_template("shelf-admin/field/localized-string.html", id=args[0].id, data=args[0].data)

_unset_value = object()

class LocalizedTextField(TextField):
    widget = LocalizedTextWidget()
    langs = ("en", "fr")

    def process(self, formdata, data=_unset_value):
        """
        Process incoming data, calling process_data, process_formdata as needed,
        and run filters.

        If `data` is not provided, process_data will be called on the field's
        default.

        Field subclasses usually won't override this, instead overriding the
        process_formdata and process_data methods. Only override this for
        special advanced processing, such as when a field encapsulates many
        inputs.
        """
        self.process_errors = []
        if data is _unset_value:
            try:
                data = self.default()
            except TypeError:
                data = self.default

        self.object_data = data

        try:
            self.process_data(data)
        except ValueError as e:
            self.process_errors.append(e.args[0])

        if formdata:
            try:
                self.raw_data = []
                for lang in self.langs:
                    if self.name+"-"+lang in formdata:
                        self.raw_data.append(formdata.getlist(self.name+"-"+lang)[0])
                    
                self.process_formdata(self.raw_data)
            except ValueError as e:
                self.process_errors.append(e.args[0])

        for filter in self.filters:
            try:
                self.data = filter(self.data)
            except ValueError as e:
                self.process_errors.append(e.args[0])

    def process_formdata(self, valuelist):
        self.data = {}
        for i in range(len(valuelist)):
            self.data[self.langs[i]] = valuelist[i]

    def process_data(self, value):
        self.data = {}
        if value:
            self.data[value.lang] = value.value
            for translation in value.trad:
                self.data[translation.lang] = translation.value

    def populate_obj(self, obj, name):
        if getattr(obj, name) is None:
            setattr(obj, name, getattr(obj.__class__, name).mapper.class_(lang="en", value=self.data["en"]))
            db.session.add(getattr(obj, name))
        else:
            getattr(obj, name).value = self.data["en"]

        lstring = getattr(obj, name)
        for lang in self.data:
            if lang == "en":
                continue
            
            res = None
            for t in lstring.trad:
                if t.lang == lang:
                    res = t
                    break

            if res is None:
                lstring.trad.append(getattr(obj.__class__, name).mapper.class_(lang=lang, value=self.data[lang]))
            else:
                res.value = self.data[lang]

        #super(LocalizedTextField, self).populate_obj(obj, name)

class LocalizedWysiwygTextWidget(TextArea):
    def __call__(self, *args, **kwargs):
        return render_template("shelf-admin/field/localized-wysiwyg-text.html", id=args[0].id, data=args[0].data)

class LocalizedWysiwygTextField(LocalizedTextField):
    widget = LocalizedWysiwygTextWidget()

    def populate_obj(self, obj, name):
        if getattr(obj, name) is None:
            setattr(obj, name, getattr(obj.__class__, name).mapper.class_(lang="en", value=self.data["en"]))
            db.session.add(getattr(obj, name))
        else:
            getattr(obj, name).value = self.data["en"]

        lstring = getattr(obj, name)
        for lang in self.data:
            if lang == "en":
                continue
            
            res = None
            for t in lstring.trad:
                if t.lang == lang:
                    res = t
                    break

            if res is None:
                lstring.trad.append(getattr(obj.__class__, name).mapper.class_(lang=lang, value=self.data[lang]))
            else:
                res.value = self.data[lang]