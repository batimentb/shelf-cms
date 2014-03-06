from flask_admin.contrib import sqla, fileadmin
from flask.ext.admin.base import expose

from shelf.admin.form.fields import LocalizedTextField, WysiwygTextField, LocalizedWysiwygTextField, RemoteFileField, PictureField
from shelf.model.base import shelf_computed_models

import os
import os.path as op
from operator import itemgetter

from flask import request, url_for, json
from sqlalchemy.types import Text

from sqlalchemy.sql.expression import desc

from base64 import b64decode

from jinja2 import contextfunction
from flask.ext.admin.contrib.sqla import form as contribform
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

from flask_login import login_required

import shutil

class ShelfModelView(sqla.ModelView):
    list_template = "shelf-admin/model/list.html"
    create_template = "shelf-admin/model/create.html"
    edit_template = "shelf-admin/model/edit.html"

    def _order_by(self, query, joins, sort_field, sort_desc):
        """
            Apply order_by to the query

            :param query:
                Query
            :param joins:
                Joins set
            :param sort_field:
                Sort field
            :param sort_desc:
                Ascending or descending
        """

        try:
            if issubclass(sort_field.mapper.class_, shelf_computed_models()['LocalizedString']):
                table = sort_field.mapper.tables[0]

                query = query.outerjoin(str(sort_field).split('.')[1])
                joins.add(table.name)

                if sort_desc:
                    query = query.order_by(desc(shelf_computed_models()['LocalizedString'].value))
                else:
                    query = query.order_by(shelf_computed_models()['LocalizedString'].value)

                return query, joins
        except:
            pass

        try:
            if issubclass(sort_field.mapper.class_, shelf_computed_models()['RemoteFile']):
                table = sort_field.mapper.tables[0]

                query = query.outerjoin(str(sort_field).split('.')[1])
                joins.add(table.name)

                if sort_desc:
                    query = query.order_by(desc(shelf_computed_models()['RemoteFile'].path))
                else:
                    query = query.order_by(shelf_computed_models()['RemoteFile'].path)

                return query, joins
        except:
            pass

        try:
            if issubclass(sort_field.mapper.class_, shelf_computed_models()['Picture']):
                table = sort_field.mapper.tables[0]

                query = query.outerjoin(str(sort_field).split('.')[1])
                joins.add(table.name)

                if sort_desc:
                    query = query.order_by(desc(shelf_computed_models()['Picture'].path))
                else:
                    query = query.order_by(shelf_computed_models()['Picture'].path)

                return query, joins
        except:
            pass

        query, joins = super(ShelfModelView, self)._order_by(query, joins, sort_field, sort_desc)
        return query, joins

    def scaffold_sortable_columns(self):
        """
            Return a dictionary of sortable columns.
            Key is column name, value is sort column/field.
        """
        columns = super(ShelfModelView, self).scaffold_sortable_columns()

        for k, v in self.model.__dict__.items():
            if hasattr(v, "mapper"):
                if 'LocalizedString' in shelf_computed_models() and issubclass(v.mapper.class_, shelf_computed_models()['LocalizedString']):
                   columns[k] = v
                if 'Picture' in shelf_computed_models() and issubclass(v.mapper.class_, shelf_computed_models()['Picture']):
                   columns[k] = v
                if 'RemoteFile' in shelf_computed_models() and issubclass(v.mapper.class_, shelf_computed_models()['RemoteFile']):
                   columns[k] = v

        return columns

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
        if ('LocalizedString' in shelf_computed_models() and isinstance(getattr(model, name), shelf_computed_models()['LocalizedString'])) \
              or ('LocalizedText' in shelf_computed_models() and isinstance(getattr(model, name), shelf_computed_models()['LocalizedText'])):
            return getattr(model, name).value
        if ('RemoteFile' in shelf_computed_models() and isinstance(getattr(model, name), shelf_computed_models()['RemoteFile'])) \
              or ('Picture' in shelf_computed_models() and isinstance(getattr(model, name), shelf_computed_models()['Picture'])):
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

    @expose('/')
    @login_required
    def index_view(self):
        return super(ShelfModelView, self).index_view()

    @expose('/new/', methods=('GET', 'POST'))
    @login_required
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
    @login_required
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

    pages_form = {}

    column_list = ("name",)

    def register_form(self, cls, form):
        self.pages_form[cls] = form
    
    def edit_form(self, obj=None):
        """
            Instantiate model editing form and return it.

            Override to implement custom behavior.
        """
        if not obj:
            raise ValueError

        if obj.__class__ in self.pages_form:
            return self.pages_form[obj.__class__](get_form_data(), obj=obj)

        converter = self.model_form_converter(self.session, self)
        cls = contribform.get_form(obj.__class__, converter,
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
    @login_required
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
        return_url = request.args.get('urls')

        if not self.can_delete:
            flash(gettext('File deletion is disabled.'), 'error')
            if return_url:
                return redirect(return_url) 
            else:
                return

        for path in items:
            base_path, full_path, path = self._normalize_path(path)

            if self.is_accessible_path(path):
                try:
                    os.remove(full_path)
                    flash(gettext('File "%(name)s" was successfully deleted.', name=path))
                except Exception as ex:
                    flash(gettext('Failed to delete file: %(name)s', name=ex), 'error')
                if return_url:
                    return redirect(return_url) 
                else:
                    return


    @expose('/delete/', methods=('POST',))
    @login_required
    def delete(self):
        """
            Delete view method
        """
        path = request.form.get('path')

        if not path:
            return redirect(url_for('.index'))

        # Get path and verify if it is valid
        base_path, full_path, path = self._normalize_path(path)

        return_url = request.args.get('url') or self._get_dir_url('.index', op.dirname(path))

        if not self.can_delete:
            flash(gettext('Deletion is disabled.'))
            return redirect(return_url)

        if not self.is_accessible_path(path):
            flash(gettext(gettext('Permission denied.')))
            return redirect(self._get_dir_url('.index'))

        if op.isdir(full_path):
            if not self.can_delete_dirs:
                flash(gettext('Directory deletion is disabled.'))
                return redirect(return_url)

            try:
                shutil.rmtree(full_path)
                self.on_directory_delete(full_path, path)
                flash(gettext('Directory "%s" was successfully deleted.' % path))
            except Exception as ex:
                flash(gettext('Failed to delete directory: %(error)s', error=ex), 'error')
        else:
            try:
                os.remove(full_path)
                self.on_file_delete(full_path, path)
                flash(gettext('File "%(name)s" was successfully deleted.', name=path))
            except Exception as ex:
                flash(gettext('Failed to delete file: %(name)s', name=ex), 'error')

        return redirect(return_url)

    @expose('/mkdir/', methods=('GET', 'POST'))
    @expose('/mkdir/<path:path>', methods=('GET', 'POST'))
    @login_required
    def mkdir(self, path=None):
        """
            Directory creation view method

            :param path:
                Optional directory path. If not provided, will use the base directory
        """
        # Get path and verify if it is valid
        base_path, directory, path = self._normalize_path(path)

        dir_url = request.args.get('url') or self._get_dir_url('.index', path)

        if not self.can_mkdir:
            flash(gettext('Directory creation is disabled.'), 'error')
            return redirect(dir_url)

        if not self.is_accessible_path(path):
            flash(gettext(gettext('Permission denied.')))
            return redirect(self._get_dir_url('.index'))

        form = NameForm(helpers.get_form_data())

        if helpers.validate_form_on_submit(form):
            try:
                os.mkdir(op.join(directory, form.name.data))
                self.on_mkdir(directory, form.name.data)
                flash('Directory '+form.name.data+' created.')
                return redirect(dir_url)
            except Exception as ex:
                flash(gettext('Failed to create directory: %(error)s', ex), 'error')

        return redirect(dir_url)


    @expose('/rename/', methods=('GET', 'POST'))
    @login_required
    def rename(self):
        """
            Rename view method
        """
        path = request.args.get('path')

        if not path:
            return redirect(url_for('.index'))

        base_path, full_path, path = self._normalize_path(path)

        return_url = request.args.get('url') or self._get_dir_url('.index', op.dirname(path))
        
        if not self.can_rename:
            flash(gettext('Renaming is disabled.'))
            return redirect(return_url)

        if not self.is_accessible_path(path):
            flash(gettext(gettext('Permission denied.')))
            return redirect(self._get_dir_url('.index'))

        if not op.exists(full_path):
            flash(gettext('Path does not exist.'))
            return redirect(return_url)

        form = NameForm(helpers.get_form_data(), name=op.basename(path))
        if helpers.validate_form_on_submit(form):
            try:
                dir_base = op.dirname(full_path)
                filename = secure_filename(form.name.data)

                os.rename(full_path, op.join(dir_base, filename))
                self.on_rename(full_path, dir_base, filename)
                flash(gettext('Successfully renamed "%(src)s" to "%(dst)s"',
                      src=op.basename(path),
                      dst=filename))
            except Exception as ex:
                flash(gettext('Failed to rename: %(error)s', error=ex), 'error')

            return redirect(return_url)

        return self.render(self.rename_template,
                           form=form,
                           path=op.dirname(path),
                           name=op.basename(path),
                           dir_url=return_url)


    @expose('/upload/', methods=('GET', 'POST'))
    @expose('/upload/<path:path>', methods=('GET', 'POST'))
    @login_required
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

    @expose('/modal-icons/')
    @expose('/modal-icons/b/<path:path>')
    @login_required
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
    @login_required
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
    @login_required
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
    @login_required
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