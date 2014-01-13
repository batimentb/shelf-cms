from flask_admin.contrib import sqla, fileadmin
from flask.ext.admin.base import expose

from shelf.admin.form.fields import LocalizedTextField, WysiwygTextField, LocalizedWysiwygTextField, RemoteFileField, PictureField
from shelf.model.base import shelf_computed_models

import os
import os.path as op
from operator import itemgetter

from flask import request, url_for
from sqlalchemy.types import Text

from base64 import b64decode

from jinja2 import contextfunction
from flask.ext.admin.contrib.sqla import form
from flask.ext.admin.contrib.fileadmin import UploadForm, NameForm
from flask.ext.admin.model.helpers import get_mdict_item_or_list
from flask.ext.admin.helpers import get_form_data, validate_form_on_submit
from flask.ext.admin.form import BaseForm, rules, get_form_opts
from flask.ext.admin.actions import action

from flask.ext.admin.contrib.sqla.tools import is_inherited_primary_key, get_column_for_current_model, get_query_for_ids

from wtforms.fields import HiddenField

from flask import redirect, flash
from flask.ext.admin import form, helpers

from flask.ext.admin.babel import gettext, lazy_gettext

from werkzeug import secure_filename

class ShelfModelView(sqla.ModelView):
    list_template = "shelf-admin/model/list.html"
    create_template = "shelf-admin/model/create.html"
    edit_template = "shelf-admin/model/edit.html"

    def after_model_change(self, form, model, is_created):
        if is_created:
            flash('{} was successfully created.'.format(model.__class__.__name__))
        else:
            flash('{} was successfully updated.'.format(model.__class__.__name__))

    def delete_model(self, model):
        if super(ShelfModelView, self).delete_model(model):
            flash('{} was successfully deleted.'.format(model.__class__.__name__))
            return True
        return False

    def get_preview_url(self, model):
        return None

    @contextfunction
    def get_list_value(self, context, model, name):
        if isinstance(getattr(model, name), shelf_computed_models()['LocalizedString']) \
              or isinstance(getattr(model, name), shelf_computed_models()['LocalizedText']):
            return getattr(model, name).value
        if isinstance(getattr(model, name), shelf_computed_models()['RemoteFile']) \
              or isinstance(getattr(model, name), shelf_computed_models()['Picture']):
            return getattr(model, name).path
        return super(ShelfModelView, self).get_list_value(context, model, name)

    @action('delete',
            lazy_gettext('Delete'),
            lazy_gettext('Are you sure you want to delete selected models?'))
    def action_delete(self, ids):
        try:
            query = get_query_for_ids(self.get_query(), self.model, ids)

            name = self.model.__name__

            if self.fast_mass_delete:
                count = query.delete(synchronize_session=False)
            else:
                count = 0

                for m in query.all():
                    self.session.delete(m)
                    count += 1

            self.session.commit()

            if count == 1:
                flash('{} was successfully deleted.'.format(name))
            else:
                flash('{} {}s were successfully deleted.'.format(count, name.lower()))
        except Exception as ex:
            if self._debug:
                raise

            flash(gettext('Failed to delete models. %(error)s', error=str(ex)), 'error')

    @expose('/new/', methods=('GET', 'POST'))
    def create_view(self):
        """
            Create model view
        """
        return_url = request.args.get('url') or url_for('.index_view')

        if not self.can_create:
            return redirect(return_url)

        form = self.create_form()

        if validate_form_on_submit(form):
            if self.create_model(form):
                if '_continue_editing' in request.form and len(request.form['_continue_editing']):
                    #self.after_model_change(form, None, True)
                    return redirect(url_for('.create_view', url=return_url))
                else:
                    return redirect(return_url)
        elif request.form:
            flash('Some fields were invalid.', "error")

        return self.render(self.create_template,
                           form=form,
                           form_opts=get_form_opts(self),
                           form_rules=self._form_create_rules,
                           return_url=return_url)

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        """
            Edit model view
        """
        return_url = request.args.get('url') or url_for('.index_view')

        if not self.can_edit:
            return redirect(return_url)

        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)

        model = self.get_one(id)

        if model is None:
            return redirect(return_url)

        form = self.edit_form(obj=model)

        if validate_form_on_submit(form):
            if self.update_model(form, model):
                if '_continue_editing' in request.form and len(request.form['_continue_editing']):
                    #self.after_model_change(form, model, False)
                    return redirect(request.full_path)
                else:
                    return redirect(return_url)
        elif request.form:
            flash('Some fields were invalid.', "error")

        return self.render(self.edit_template,
                           model=model,
                           form=form,
                           form_opts=get_form_opts(self),
                           form_rules=self._form_edit_rules,
                           return_url=return_url)

    def scaffold_form(self):
        cls = super(ShelfModelView, self).scaffold_form()

        for k, v in self.model.__dict__.items():
            if hasattr(v, "type") and isinstance(v.type, Text):
                setattr(cls, k, WysiwygTextField())

            if hasattr(v, "mapper"):
                if issubclass(v.mapper.class_, shelf_computed_models()['LocalizedString']) \
                    and not issubclass(self.model, shelf_computed_models()['LocalizedString']):
                        setattr(cls, k, LocalizedTextField())
                elif 'LocalizedText' in shelf_computed_models() \
                    and issubclass(v.mapper.class_, shelf_computed_models()['LocalizedText']) \
                    and not issubclass(self.model, shelf_computed_models()['LocalizedText']):
                        setattr(cls, k, LocalizedWysiwygTextField())
                elif 'RemoteFile' in shelf_computed_models() \
                    and issubclass(v.mapper.class_, shelf_computed_models()['RemoteFile']):
                        setattr(cls, k, RemoteFileField())
                elif 'Picture' in shelf_computed_models() \
                    and issubclass(v.mapper.class_, shelf_computed_models()['Picture']):
                        setattr(cls, k, PictureField())

        return cls

from flask.ext.admin.helpers import get_form_data

class ShelfPageView(ShelfModelView):
    can_create = False
    can_delete = False

    edit_template = "shelf-admin/page/edit.html"
    
    def edit_form(self, obj=None):
        """
            Instantiate model editing form and return it.

            Override to implement custom behavior.
        """
        converter = self.model_form_converter(self.session, self)
        cls = form.get_form(obj.__class__, converter,
                                   base_class=self.form_base_class,
                                   only=self.form_columns,
                                   exclude=self.form_excluded_columns,
                                   field_args=self.form_args,
                                   extra_fields=self.form_extra_fields)

        if self.inline_models:
            cls = self.scaffold_inline_form_models(form_class)

        del cls.name

        mapper = obj._sa_class_manager.mapper
        properties = ((p.key, p) for p in mapper.iterate_properties)

        for k, v in properties:
            if hasattr(v, "type") and isinstance(v.type, Text):
                setattr(cls, k, WysiwygTextField())

            if hasattr(v, "mapper"):
                if issubclass(v.mapper.class_, shelf_computed_models()['LocalizedString']) \
                    and not issubclass(obj.__class__, shelf_computed_models()['LocalizedString']):
                        setattr(cls, k, LocalizedTextField())
                elif issubclass(v.mapper.class_, shelf_computed_models()['LocalizedText']) \
                    and not issubclass(obj.__class__, shelf_computed_models()['LocalizedText']):
                        setattr(cls, k, LocalizedWysiwygTextField())

        return cls(get_form_data(), obj=obj)

    def update_model(self, form, model):
        return super(ShelfPageView, self).update_model(form, model)


class ShelfFileAdmin(fileadmin.FileAdmin):
    list_template = "shelf-admin/file/list.html"
    iconic_template = "shelf-admin/file/iconic.html"
    upload_template = "shelf-admin/file/upload.html"
    modal_list_template = "shelf-admin/file/modal-list.html"
    modal_iconic_template = "shelf-admin/file/modal-iconic.html"

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

    @action('delete',
            lazy_gettext('Delete'),
            lazy_gettext('Are you sure you want to delete these files?'))
    def action_delete(self, items):
        print "lololo"
        if not self.can_delete:
            flash(gettext('File deletion is disabled.'), 'error')
            return

        for path in items:
            base_path, full_path, path = self._normalize_path(path)

            if self.is_accessible_path(path):
                try:
                    os.remove(full_path)
                    flash(gettext('File "%(name)s" was successfully deleted.', name=path))
                except Exception as ex:
                    flash(gettext('Failed to delete file: %(name)s', name=ex), 'error')

    @expose('/mkdir/', methods=('GET', 'POST'))
    @expose('/mkdir/<path:path>', methods=('GET', 'POST'))
    def mkdir(self, path=None):
        """
            Directory creation view method

            :param path:
                Optional directory path. If not provided, will use the base directory
        """
        # Get path and verify if it is valid
        base_path, directory, path = self._normalize_path(path)

        dir_url = self._get_dir_url('.index', path)

        if not self.can_mkdir:
            flash(gettext('Directory creation is disabled.'), 'error')
            return redirect(dir_url)

        if not self.is_accessible_path(path):
            flash(gettext(gettext('Permission denied.')))
            return redirect(self._get_dir_url('.index'))

        form = NameForm(helpers.get_form_data())
        print form, helpers.validate_form_on_submit(form), form.data

        if helpers.validate_form_on_submit(form):
            try:
                os.mkdir(op.join(directory, form.name.data))
                self.on_mkdir(directory, form.name.data)
                flash('Directory '+form.name.data+' created.')
                return redirect(dir_url)
            except Exception as ex:
                flash(gettext('Failed to create directory: %(error)s', ex), 'error')

        return redirect(dir_url)

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
                    return redirect(self._get_dir_url('.index', path))
                except Exception as ex:
                    flash(gettext('Failed to save file: %(error)s', error=ex))

        return self.render(self.upload_template, form=form, dir_path=path)

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
                        'image': ('.png', '.jpg', '.jpeg'),
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

        return self.render(self.modal_iconic_template,
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
                        'image': ('.png', '.jpg', '.jpeg'),
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

        return self.render(self.modal_list_template,
                           dir_path=path,
                           breadcrumbs=breadcrumbs,
                           get_dir_url=self._get_dir_url,
                           get_file_url=self._get_file_url,
                           items=items,
                           mimes=mimes,
                           actions=actions,
                           actions_confirmation=actions_confirmation)

    @expose('/icons/')
    @expose('/icons/b/<path:path>')
    def iconic_index(self, path=None):
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
                        'image': ('.png', '.jpg', '.jpeg'),
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

        return self.render(self.iconic_template,
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
                        'image': ('.png', '.jpg', '.jpeg'),
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