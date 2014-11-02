from flask_admin.contrib import fileadmin
from flask import Blueprint, flash, url_for, request, json, redirect, render_template
from flask.ext.admin.babel import gettext, lazy_gettext
from flask_admin.base import expose
import os
from operator import itemgetter
import os.path as op
from flask.ext.admin.contrib.fileadmin import UploadForm, NameForm
from flask.ext.admin import helpers
from werkzeug import secure_filename
from base64 import b64decode
from wtforms.fields import TextField
from flask.ext.admin.form import RenderTemplateWidget
from shelf.security.mixin import LoginMixin

_unset_value = object()


class RemoteFileModelMixin:
    def get_path(self):
        return self.path

    def set_path(self, path):
        if path and len(path) == 0:
            path = None
        self.path = path

    def __unicode__(self):
        return self.path


class PictureModelMixin:
    def get_path(self, format="source"):
        paths = {}
        if hasattr(self, "format"):
            if self.format == format:
                return self.path
            else:
                for picformat in self.formats:
                    if picformat.format not in paths:
                        paths[picformat.format] = picformat.path
                if format in paths:
                    return paths[format]
        else:
            return self.path

    def set_path(self, path, format="source"):
        paths = {}
        if path and len(path) == 0:
            path = None
        if hasattr(self, "format"):
            if self.format == format:
                self.path = path
            else:
                for picformat in self.formats:
                    if picformat.format not in paths:
                        paths[ficformat.format] = picformat
                if format in picformat:
                    picformat[format].path = path
                else:
                    cls = self.__class__(path=path, format=format)
                    self.formats.append(cls)
        else:
            self.path = path

    def __unicode__(self):
        return self.path


class LibraryViewMixin:
    pass


config = {
    "name": "Library",
    "description": "Manage your website files and medias",
    "admin": {
        "view_subclass": LibraryViewMixin,
        "template": {
            "modelview.edit_view": {
                "tail_js":"shelf-library-field-tail.html"
            },
            "modelview.create_view": {
                "tail_js": "shelf-library-field-tail.html"
            }
        }
    }
}
'''"extend": {
    "admin": {
        "auto_join": "auto_joins",
        "form": "form",
        "list_column": "list_column"
    },
    "security": {
        "roles": ["librarian"]
    },
    "script": {
        "compute_thumbs": "compute_thumbs"
    }
},'''


class RemoteFileWidget(RenderTemplateWidget):
    def __init__(self):
        RenderTemplateWidget.__init__(self, "shelf-field-file.html")


class RemoteFileField(TextField):
    widget = RemoteFileWidget()

    def __init__(self, *args, **kwargs):
        if "allow_blank" in kwargs:
            del kwargs["allow_blank"]
        super(RemoteFileField, self).__init__(*args, **kwargs)

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = valuelist[0]

    def process_data(self, value):
        TextField.process_data(self, value)

    def populate_obj(self, obj, name):
        if getattr(obj, name) is None:
            newfile = getattr(obj.__class__, name).mapper.class_()
            setattr(obj, name, newfile)
            if self.raw_data and len(self.raw_data):
                getattr(obj, name).set_path(self.raw_data[0])


class PictureWidget(RenderTemplateWidget):
    def __init__(self):
        RenderTemplateWidget.__init__(self, "shelf-field-picture.html")


class PictureField(TextField):
    widget = PictureWidget()

    def __init__(self, label='', validators=None, ratio=None, formats=None, **kwargs):
        if "allow_blank" in kwargs:
            del kwargs["allow_blank"]
        super(PictureField, self).__init__(label, validators, **kwargs)
        #self.picture_formats = formats
        #self.ratio = ratio

    def populate_obj(self, obj, name):
        if getattr(obj, name) is None:
            newfile = getattr(obj.__class__, name).mapper.class_()
            setattr(obj, name, newfile)
            if self.raw_data and len(self.raw_data):
                getattr(obj, name).set_path(self.raw_data[0])

    def process_formdata(self, valuelist):
        if self.data:
            self.data.set_path(valuelist[0])


class FileAdmin(LoginMixin, fileadmin.FileAdmin):
    list_template = "shelf-library-list.html"
    icon_list_template = "shelf-library-icon-list.html"
    upload_template = "shelf-library-upload.html"
    modal_template = "shelf-library-modal-list.html"  
    icon_modal_template = "shelf-library-modal-icon-list.html"

    @expose('/modal-icons/')
    @expose('/modal-icons/b/<path:path>')
    def modal_iconic_index(self, path=None):
        """
            Index view method

            :param path:
                Optional directory path. If not provided, will use the base directory
        """
        # Get path and verify if it is valid
        base_path, directory, path = self._normalize_path(path)

        if not self.is_accessible_path(path):
            flash(gettext(gettext('Permission denied.')))
            return redirect(self._get_dir_url('.index'))

        # Get directory listing
        items = []
        mimes = {}
        mime_by_ext = {'text': ('.pdf', '.txt', '.doc', '.html', '.xml', '.css'),
                        'archive': ('.zip',),
                        'image': ('.png', '.jpg', '.jpeg', '.gif'),
                        'video': ('.mpg', '.mpeg', '.wmv', '.mp4', '.flv', '.mov')
                        }

        # Parent directory
        if directory != base_path:
            parent_path = op.normpath(op.join(path, '..'))
            if parent_path == '.':
                parent_path = None

            items.append(('..', parent_path, True, 0))

        for f in os.listdir(directory):
            fp = op.join(directory, f)
            rel_path = op.join(path, f)

            if self.is_accessible_path(rel_path) and not f.startswith('.'):
                items.append((f, rel_path, op.isdir(fp), op.getsize(fp)))
                mimes[rel_path] = 'other'
                for mime in mime_by_ext:
                    if op.splitext(rel_path)[1] in mime_by_ext[mime]:
                        mimes[rel_path] = mime


        # Sort by name
        items.sort(key=itemgetter(0))

        # Sort by type
        items.sort(key=itemgetter(2), reverse=True)

        # Generate breadcrumbs
        accumulator = []
        breadcrumbs = []
        for n in path.split(os.sep):
            accumulator.append(n)
            breadcrumbs.append((n, op.join(*accumulator)))

        # Actions
        actions, actions_confirmation = self.get_actions_list()

        return self.render(self.icon_modal_template,
                           dir_path=path,
                           breadcrumbs=breadcrumbs,
                           get_dir_url=self._get_dir_url,
                           get_file_url=self._get_file_url,
                           items=items,
                           mimes=mimes,
                           actions=actions,
                           actions_confirmation=actions_confirmation)

    @expose('/modal/')
    @expose('/modal/b/<path:path>')
    def modal_index(self, path=None):
        """
            Index view method

            :param path:
                Optional directory path. If not provided, will use the base directory
        """
        # Get path and verify if it is valid
        base_path, directory, path = self._normalize_path(path)

        if not self.is_accessible_path(path):
            flash(gettext(gettext('Permission denied.')))
            return redirect(self._get_dir_url('.index'))

        # Get directory listing
        items = []
        mimes = {}
        mime_by_ext = {'text': ('.pdf', '.txt', '.doc', '.html', '.xml', '.css'),
                        'archive': ('.zip',),
                        'image': ('.png', '.jpg', '.jpeg', '.gif'),
                        'video': ('.mpg', '.mpeg', '.wmv', '.mp4', '.flv', '.mov')
                        }

        # Parent directory
        if directory != base_path:
            parent_path = op.normpath(op.join(path, '..'))
            if parent_path == '.':
                parent_path = None

            items.append(('..', parent_path, True, 0))

        for f in os.listdir(directory):
            fp = op.join(directory, f)
            rel_path = op.join(path, f)

            if self.is_accessible_path(rel_path) and not f.startswith('.'):
                items.append((f, rel_path, op.isdir(fp), op.getsize(fp)))
                mimes[rel_path] = 'other'
                for mime in mime_by_ext:
                    if op.splitext(rel_path)[1] in mime_by_ext[mime]:
                        mimes[rel_path] = mime


        # Sort by name
        items.sort(key=itemgetter(0))

        # Sort by type
        items.sort(key=itemgetter(2), reverse=True)

        # Generate breadcrumbs
        accumulator = []
        breadcrumbs = []
        for n in path.split(os.sep):
            accumulator.append(n)
            breadcrumbs.append((n, op.join(*accumulator)))

        # Actions
        actions, actions_confirmation = self.get_actions_list()

        return self.render(self.modal_template,
                           dir_path=path,
                           breadcrumbs=breadcrumbs,
                           get_dir_url=self._get_dir_url,
                           get_file_url=self._get_file_url,
                           items=items,
                           mimes=mimes,
                           actions=actions,
                           actions_confirmation=actions_confirmation)


    @expose('/asyncupload', methods=("POST",))
    def async_upload(self):
        mfile = request.form['file']
        mname = request.form['name']
        mpath = request.form['path']
        ffile = op.join(self._normalize_path(mpath)[1], mname)
        encoded = mfile.replace(' ', '+')
        decoded = b64decode(encoded)
        with open(ffile, 'w') as f:
            f.write(decoded)
        return "True"

    @expose('/upload/', methods=('GET', 'POST'))
    @expose('/upload/<path:path>', methods=('GET', 'POST'))
    def upload(self, path=None):
        """
            Upload view method

            :param path:
                Optional directory path. If not provided, will use the base directory
        """
        # Get path and verify if it is valid
        base_path, directory, path = self._normalize_path(path)

        if not self.can_upload:
            flash(gettext('File uploading is disabled.'), 'error')
            return redirect(self._get_dir_url('.index', path))

        if not self.is_accessible_path(path):
            flash(gettext(gettext('Permission denied.')))
            return redirect(self._get_dir_url('.index'))

        form = UploadForm(self)

        #print form, helpers.validate_form_on_submit(form), form.data
        if helpers.validate_form_on_submit(form):
            filename = op.join(directory,
                               secure_filename(form.upload.data.filename))

            if op.exists(filename):
                flash(gettext('File "%(name)s" already exists.', name=filename),
                      'error')
            else:
                try:
                    self.save_file(filename, form.upload.data)
                    self.on_file_upload(directory, path, filename)
                    flash('%s was correctly uploaded' % form.upload.data.filename)
                    return redirect(self._get_dir_url('.index', path))
                except Exception as ex:
                    flash(gettext('Failed to save file: %(error)s', error=ex))
        elif request.form and 'async' in request.form:
            total_uploaded = 0
            for tmp_filename in json.loads(request.form['async']):
                filename = op.join(directory,
                               secure_filename(form.upload.data.filename))
                if op.exists(filename):
                    total_uploaded = total_uploaded + 1

            if total_uploaded == 0:
                flash('Nothing was uploaded', 'error')
            elif total_uploaded == 1:
                flash('%s was correctly uploaded' % tmp_filename)
                return redirect(self._get_dir_url('.index', path))
            else:
                flash('%d files were correctly uploaded' % total_uploaded)
                return redirect(self._get_dir_url('.index', path))

        return self.render(self.upload_template, form=form, dir_path=path)

    @expose('/icons/')
    @expose('/icons/b/<path:path>')
    def icon_index(self, path=None):
        # Get path and verify if it is valid
        base_path, directory, path = self._normalize_path(path)

        if not self.is_accessible_path(path):
            flash(gettext(gettext('Permission denied.')))
            return redirect(self._get_dir_url('.index'))

        # Get directory listing
        items = []
        mimes = {}
        mime_by_ext = {'text': ('.pdf', '.txt', '.doc', '.html', '.xml', '.css'),
                        'archive': ('.zip',),
                        'image': ('.png', '.jpg', '.jpeg', '.gif'),
                        'video': ('.mpg', '.mpeg', '.wmv', '.mp4', '.flv', '.mov')
                        }

        # Parent directory
        if directory != base_path:
            parent_path = op.normpath(op.join(path, '..'))
            if parent_path == '.':
                parent_path = None

            items.append(('..', parent_path, True, 0))

        for f in os.listdir(directory):
            fp = op.join(directory, f)
            rel_path = op.join(path, f)

            if self.is_accessible_path(rel_path) and not f.startswith('.'):
                items.append((f, rel_path, op.isdir(fp), op.getsize(fp)))
                mimes[rel_path] = 'other'
                for mime in mime_by_ext:
                    if op.splitext(rel_path)[1] in mime_by_ext[mime]:
                        mimes[rel_path] = mime


        # Sort by name
        items.sort(key=itemgetter(0))

        # Sort by type
        items.sort(key=itemgetter(2), reverse=True)

        # Generate breadcrumbs
        accumulator = []
        breadcrumbs = []
        for n in path.split(os.sep):
            accumulator.append(n)
            breadcrumbs.append((n, op.join(*accumulator)))

        # Actions
        actions, actions_confirmation = self.get_actions_list()

        return self.render(self.icon_list_template,
                           dir_path=path,
                           breadcrumbs=breadcrumbs,
                           get_dir_url=self._get_dir_url,
                           get_file_url=self._get_file_url,
                           items=items,
                           mimes=mimes,
                           actions=actions,
                           actions_confirmation=actions_confirmation)

    @expose('/')
    @expose('/b/<path:path>')
    def index(self, path=None):
        """
            Index view method

            :param path:
                Optional directory path. If not provided, will use the base directory
        """
        # Get path and verify if it is valid
        base_path, directory, path = self._normalize_path(path)

        if not self.is_accessible_path(path):
            flash(gettext(gettext('Permission denied.')))
            return redirect(self._get_dir_url('.index'))

        # Get directory listing
        items = []
        mimes = {}
        mime_by_ext = {'text': ('.pdf', '.txt', '.doc', '.html', '.xml', '.css'),
                        'archive': ('.zip',),
                        'image': ('.png', '.jpg', '.jpeg', '.gif'),
                        'video': ('.mpg', '.mpeg', '.wmv', '.mp4', '.flv', '.mov')
                        }

        # Parent directory
        if directory != base_path:
            parent_path = op.normpath(op.join(path, '..'))
            if parent_path == '.':
                parent_path = None

            items.append(('..', parent_path, True, 0))

        for f in os.listdir(directory):
            fp = op.join(directory, f)
            rel_path = op.join(path, f)

            if self.is_accessible_path(rel_path) and not f.startswith('.'):
                items.append((f, rel_path, op.isdir(fp), op.getsize(fp)))
                mimes[rel_path] = 'other'
                for mime in mime_by_ext:
                    if op.splitext(rel_path)[1] in mime_by_ext[mime]:
                        mimes[rel_path] = mime


        # Sort by name
        items.sort(key=itemgetter(0))

        # Sort by type
        items.sort(key=itemgetter(2), reverse=True)

        # Generate breadcrumbs
        accumulator = []
        breadcrumbs = []
        for n in path.split(os.sep):
            accumulator.append(n)
            breadcrumbs.append((n, op.join(*accumulator)))

        # Actions
        actions, actions_confirmation = self.get_actions_list()

        return self.render(self.list_template,
                           dir_path=path,
                           breadcrumbs=breadcrumbs,
                           get_dir_url=self._get_dir_url,
                           get_file_url=self._get_file_url,
                           items=items,
                           mimes=mimes,
                           actions=actions,
                           actions_confirmation=actions_confirmation)


class Library:
    def __init__(self):
        self.config = config

    def init_app(self, app):
        self.bp = Blueprint("library", __name__, url_prefix="/library",
            static_folder="static", template_folder="templates")
        app.register_blueprint(self.bp)

