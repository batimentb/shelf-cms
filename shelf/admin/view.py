from flask_admin.base import AdminIndexView, expose
from flask import render_template, redirect, request, url_for, json
from flask_admin.contrib import sqla, fileadmin

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

from flask.ext.admin.contrib.sqla.tools import is_inherited_primary_key, get_column_for_current_model, get_query_for_ids

from wtforms.fields import HiddenField

from flask import redirect, flash
from flask.ext.admin import form, helpers

from flask.ext.admin.babel import gettext, lazy_gettext

from werkzeug import secure_filename

from flask_login import login_required, current_user, logout_user

from flask.ext.admin import tools
from flask.ext.admin._compat import text_type

from field import *

import shutil

import shelf.model
db = shelf.model.db

from ..user.base import shelf_login_required

from model import LocalizedString, RemoteFile, LocalizedText, Picture, WorkflowMixin, OrderableMixin

def action(name, text, confirmation=None, icon=None):
    """
        Use this decorator to expose actions that span more than one
        entity (model, file, etc)

        :param name:
            Action name
        :param text:
            Action text.
        :param confirmation:
            Confirmation text. If not provided, action will be executed
            unconditionally.
    """
    def wrap(f):
        f._action = (name, text, confirmation)
        f._icon = (name, icon)
        return f

    return wrap

def issubmodel(cls, name):
    if not cls:
        return False
    if not name:
        return False
    if cls.__name__ == name:
        return True
    return False

from ..user.form import *

class DashboardView(AdminIndexView):
    widgets = []

    def add_widget(self, view):
        if not self.widgets:
            self.widgets = []
        self.widgets.append(view)

    @expose('/signin/', methods=("GET", "POST"))
    def signin(self):
    	if validate_login_on_submit(request.form):
    		return redirect(request.args.get("next") or url_for("admin.index"))
    	else:
    		return render_template("shelf/login/login.html", form=LoginForm(request.form))

    @expose('/signup/', methods=("GET", "POST"))
    def signup(self):
        if validate_register_on_submit(request.form):
            return redirect(request.args.get("next") or url_for("admin.signin"))
        else:
    	   return render_template("shelf/login/signup.html", form=RegisterForm(request.form))

    @expose('/recover/', methods=("GET", "POST"))
    def recover(self):
        if validate_recover_on_submit(request.form):
            return redirect(request.args.get("next") or url_for("admin.signin"))
        else:
    	   return render_template("shelf/login/recover.html", form=RecoverForm(request.form))

    @expose('/logout/', methods=("GET",))
    @shelf_login_required
    def logout(self):
        logout_user()
        return redirect(request.args.get("next") or url_for("admin.signin"))

    @expose()
    @shelf_login_required
    def index(self):
        return self.render(self._template, user=current_user, widgets=[w.render() for w in self.widgets])

class ShelfModelView(sqla.ModelView):
    list_template = "shelf/model/list.html"
    create_template = "shelf/model/create.html"
    edit_template = "shelf/model/edit.html"

    def _get_default_order(self):
        """
            Return default sort order
        """
        if self.column_default_sort:
            if isinstance(self.column_default_sort, tuple):
                return self.column_default_sort
            else:
                return self.column_default_sort, False
        elif issubclass(self.model, OrderableMixin):
            return self.model.shelf_order, True

        return None

    def create_blueprint(self, admin):
        bp = super(ShelfModelView, self).create_blueprint(admin)
        @bp.context_processor
        def add_user():
            return dict(user=current_user)
        return bp

    def scaffold_list_columns(self):
        columns = super(ShelfModelView, self).scaffold_list_columns()
        res = []
        for c in columns:
            if not c.startswith("shelf_"):
                res.append(c)
        if "shelf_state" in columns:
            res.append("shelf_state")
        return res

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
        if not hasattr(sort_field, "mapper"):
            pass
        elif issubmodel(sort_field.mapper.class_, 'LocalizedString'):
            table = sort_field.mapper.tables[0]

            query = query.outerjoin(str(sort_field).split('.')[1])
            joins.add(table.name)

            if sort_desc:
                query = query.order_by(desc(LocalizedString.value))
            else:
                query = query.order_by(LocalizedString.value)

            return query, joins

        elif issubmodel(sort_field.mapper.class_, 'RemoteFile'):
            table = sort_field.mapper.tables[0]

            query = query.outerjoin(str(sort_field).split('.')[1])
            joins.add(table.name)

            if sort_desc:
                query = query.order_by(desc(RemoteFile.path))
            else:
                query = query.order_by(RemoteFile.path)

            return query, joins

        elif issubmodel(sort_field.mapper.class_, 'Picture'):
            table = sort_field.mapper.tables[0]

            query = query.outerjoin(str(sort_field).split('.')[1])
            joins.add(table.name)

            if sort_desc:
                query = query.order_by(desc(Picture.path))
            else:
                query = query.order_by(Picture.path)

            return query, joins

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
                if issubmodel(v.mapper.class_, 'LocalizedString') or \
                        issubmodel(v.mapper.class_, 'Picture') or \
                        issubmodel(v.mapper.class_, 'RemoteFile'):
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
        if issubmodel(getattr(model, name).__class__, 'LocalizedString') or \
                issubmodel(getattr(model, name).__class__, 'LocalizedText'):
            return getattr(model, name).value
        elif issubmodel(getattr(model, name).__class__, 'Picture') or \
                issubmodel(getattr(model, name).__class__, 'RemoteFile'):
            return getattr(model, name).path

        return super(ShelfModelView, self).get_list_value(context, model, name)

    def icon_from_action(self, name):
        for curname, icon in self._icons:
            if name == curname:
                return icon
        return None

    def get_actions_list(self):
        """
            Return a list and a dictionary of allowed actions.
        """
        actions = []
        actions_confirmation = {}

        for act in self._actions:
            name, text = act

            if self.is_action_allowed(name):
                actions.append((name, text_type(text), self.icon_from_action(name)))

                confirmation = self._actions_data[name][2]
                if confirmation:
                    actions_confirmation[name] = text_type(confirmation)

        return actions, actions_confirmation

    def init_actions(self):
        """
            Initialize list of actions for the current administrative view.
        """
        self._actions = []
        self._icons = []
        self._actions_data = {}

        for p in dir(self):
            attr = tools.get_dict_attr(self, p)

            if hasattr(attr, '_action'):
                name, text, desc = attr._action
                name, icon = attr._icon

                if name == "reorder":
                    if not issubclass(self.model, OrderableMixin):
                        continue
                elif name == "publish" or name == "review" or name == "draft":
                    if not issubclass(self.model, WorkflowMixin):
                        continue

                self._actions.append((name, text))
                self._icons.append((name, icon))

                # TODO: Use namedtuple
                # Reason why we need getattr here - what's in attr is not
                # bound to the object.
                self._actions_data[name] = (getattr(self, p), text, desc)

    @action('publish',
            lazy_gettext('Publish'),
            lazy_gettext('Are you sure you want to publish selected models?'),
            "thumbs-up")
    def action_publish(self, ids):
        try:
            query = get_query_for_ids(self.get_query(), self.model, ids)

            name = self.model.__name__

            count = 0

            for m in query.all():
                m.shelf_state = "public"
                count += 1

            self.session.commit()

            if count == 1:
                flash('{} was successfully published.'.format(name))
            else:
                flash('{} {}s were successfully published.'.format(count, name.lower()))
        except Exception as ex:
            if self._debug:
                raise

            flash(gettext('Failed to publish models. %(error)s', error=str(ex)), 'error')

    @action('review',
            lazy_gettext('Review'),
            lazy_gettext('Are you sure you want to put selected models for review?'),
            "search")
    def action_review(self, ids):
        try:
            query = get_query_for_ids(self.get_query(), self.model, ids)

            name = self.model.__name__

            count = 0

            for m in query.all():
                m.shelf_state = "private"
                count += 1

            self.session.commit()

            if count == 1:
                flash('{} was successfully put for review.'.format(name))
            else:
                flash('{} {}s were successfully put for review.'.format(count, name.lower()))
        except Exception as ex:
            if self._debug:
                raise

            flash(gettext('Failed to put models for review. %(error)s', error=str(ex)), 'error')

    @action('draft',
            lazy_gettext('Draft'),
            lazy_gettext('Are you sure you want to unpublish selected models?'),
            'file-text-o')
    def action_draft(self, ids):
        try:
            query = get_query_for_ids(self.get_query(), self.model, ids)

            name = self.model.__name__

            count = 0

            for m in query.all():
                m.shelf_state = "draft"
                count += 1

            self.session.commit()

            if count == 1:
                flash('{} was successfully unpublished.'.format(name))
            else:
                flash('{} {}s were successfully unpublished.'.format(count, name.lower()))
        except Exception as ex:
            if self._debug:
                raise

            flash(gettext('Failed to unpublish models. %(error)s', error=str(ex)), 'error')

    @action('reorder',
            lazy_gettext('Change order'),
            lazy_gettext('Are you sure you want to reorder selected models?'),
            'list-ol')
    def action_reorder(self, ids):
        try:
            count = 0
            name = self.model.__name__
            models = []
            priorities = []

            for i in range(len(ids)):
                m = db.session.query(self.model).get(ids[i])
                models.append(m)
                priorities.append(m.shelf_order)
                count += 1

            priorities = sorted(priorities, reverse=True)

            for i in range(len(ids)):
                m = models[i]
                m.shelf_order = priorities[i]

            db.session.commit()

            if count == 1:
                flash('{} was successfully reordered.'.format(name))
            else:
                flash('{} {}s were successfully reordered.'.format(count, name.lower()))
        except Exception, ex:
            flash(gettext('Failed to sort models. %(error)s', error=str(ex)), 'error')

    @action('delete',
            lazy_gettext('Delete'),
            lazy_gettext('Are you sure you want to delete selected models?'),
            "trash-o")
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
    @shelf_login_required
    def index_view(self):
        """
            List view
        """
        # Grab parameters from URL
        page, sort_idx, sort_desc, search, filters = self._get_extra_args()

        # Map column index to column name
        sort_column = self._get_column_by_idx(sort_idx)
        if sort_column is not None:
            sort_column = sort_column[0]

        # Get count and data
        count, data = self.get_list(page, sort_column, sort_desc,
                                    search, filters)

        # Calculate number of pages
        num_pages = count // self.page_size
        if count % self.page_size != 0:
            num_pages += 1

        # Pregenerate filters
        if self._filters:
            filters_data = dict()

            for idx, f in enumerate(self._filters):
                flt_data = f.get_options(self)

                if flt_data:
                    filters_data[idx] = flt_data
        else:
            filters_data = None

        # Various URL generation helpers
        def pager_url(p):
            # Do not add page number if it is first page
            if p == 0:
                p = None

            return self._get_url('.index_view', p, sort_idx, sort_desc,
                                 search, filters)

        def sort_url(column, invert=False):
            desc = None

            if invert and not sort_desc:
                desc = 1

            return self._get_url('.index_view', page, column, desc,
                                 search, filters)

        # Actions
        actions, actions_confirmation = self.get_actions_list()

        return self.render(self.list_template,
                               data=data,
                               # List
                               list_columns=self._list_columns,
                               sortable_columns=self._sortable_columns,
                               # Stuff
                               enumerate=enumerate,
                               get_pk_value=self.get_pk_value,
                               get_value=self.get_list_value,
                               return_url=self._get_url('.index_view',
                                                        page,
                                                        sort_idx,
                                                        sort_desc,
                                                        search,
                                                        filters),
                               # Pagination
                               count=count,
                               pager_url=pager_url,
                               num_pages=num_pages,
                               page=page,
                               # Sorting
                               sort_column=sort_idx,
                               sort_desc=sort_desc,
                               sort_url=sort_url,
                               # Search
                               search_supported=self._search_supported,
                               clear_search_url=self._get_url('.index_view',
                                                              None,
                                                              sort_idx,
                                                              sort_desc),
                               search=search,
                               # Filters
                               filters=self._filters,
                               filter_groups=self._filter_groups,
                               filter_types=self._filter_types,
                               filter_data=filters_data,
                               active_filters=filters,

                               has_workflow=issubclass(self.model, WorkflowMixin),
                               has_order=issubclass(self.model, OrderableMixin),

                               # Actions
                               actions=actions,
                               actions_confirmation=actions_confirmation)

    @expose('/new/', methods=('GET', 'POST'))
    @shelf_login_required
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
                           has_workflow=issubclass(self.model, WorkflowMixin),
                           has_order=issubclass(self.model, OrderableMixin),
                           return_url=return_url)

    
    @expose('/edit/', methods=('GET', 'POST'))
    @shelf_login_required
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
                           has_workflow=issubclass(self.model, WorkflowMixin),
                           has_order=issubclass(self.model, OrderableMixin),
                           return_url=return_url)

    def scaffold_form(self):
        cls = super(ShelfModelView, self).scaffold_form()

        for k, v in self.model.__dict__.items():
            if hasattr(v, "type") and isinstance(v.type, Text):
                setattr(cls, k, WysiwygTextField())

            if hasattr(v, "mapper"):
                if issubmodel(v.mapper.class_, 'LocalizedString') \
                        and not issubmodel(self.model, 'LocalizedString'):
                    setattr(cls, k, LocalizedTextField())
                elif issubmodel(v.mapper.class_, 'LocalizedText') \
                        and not issubmodel(self.model, 'LocalizedText'):
                    setattr(cls, k, LocalizedWysiwygTextField())
                elif issubmodel(v.mapper.class_, 'RemoteFile') \
                        and not issubmodel(self.model, 'RemoteFile'):
                    setattr(cls, k, RemoteFileField())
                elif issubmodel(v.mapper.class_, 'Picture') \
                        and not issubmodel(self.model, 'Picture'):
                    setattr(cls, k, PictureField())

        if issubclass(self.model, WorkflowMixin):
            cls.shelf_state = wtforms.HiddenField(default="draft")
        if issubclass(self.model, OrderableMixin):
            cls.shelf_order = wtforms.HiddenField()

        return cls

class Library(fileadmin.FileAdmin):
    list_template = "shelf/library/list.html"
    iconic_template = "shelf/library/iconic.html"
    upload_template = "shelf/library/upload.html"
    modal_list_template = "shelf/library/modal-list.html"
    modal_iconic_template = "shelf/library/modal-iconic.html"

    def create_blueprint(self, admin):
        bp = super(Library, self).create_blueprint(admin)
        @bp.context_processor
        def add_user():
            return dict(user=current_user)
        return bp

    @expose('/asyncupload', methods=("POST",))
    @shelf_login_required
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
    @shelf_login_required
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
    @shelf_login_required
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
    @shelf_login_required
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
    @shelf_login_required
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
    @shelf_login_required
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
    @shelf_login_required
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
    @shelf_login_required
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
    @shelf_login_required
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


from flask.ext.admin.helpers import get_form_data

class ShelfPageView(ShelfModelView):
    can_create = False
    can_delete = False

    edit_template = "shelf/model/edit-page.html"

    pages_form = {}

    column_list = ("name", "title", "description")

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
                if issubmodel(v.mapper.class_, 'LocalizedString') \
                        and not issubmodel(self.model, 'LocalizedString'):
                    setattr(cls, k, LocalizedTextField())
                elif issubmodel(v.mapper.class_, 'LocalizedText') \
                        and not issubmodel(self.model, 'LocalizedText'):
                    setattr(cls, k, LocalizedWysiwygTextField())
                elif issubmodel(v.mapper.class_, 'RemoteFile') \
                        and not issubmodel(self.model, 'RemoteFile'):
                    setattr(cls, k, RemoteFileField())
                elif issubmodel(v.mapper.class_, 'Picture') \
                        and not issubmodel(self.model, 'Picture'):
                    setattr(cls, k, PictureField())

        return cls(get_form_data(), obj=obj)

    def update_model(self, form, model):
        return super(ShelfPageView, self).update_model(form, model)
