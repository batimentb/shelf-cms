from flask_security import url_for_security, current_user
from shelf.admin.view import SQLAModelView
from flask import render_template, request, redirect, url_for

class UserModelView(SQLAModelView):
    default_forbidden_columns = ("password", "confirmed_at")
    can_edit = True
    can_create = False
    can_delete = False

    def __init__(self, *args, **kwargs):
        self.forbidden_columns = self.default_forbidden_columns
        super(UserModelView, self).__init__(*args, **kwargs)

    def edit_form(self, obj):
        form = super(SQLAModelView, self).edit_form(obj)
        if not current_user.has_role('superadmin'):
            delattr(form, "roles")
            delattr(form, "active")
        return form

    def scaffold_list_columns(self):
        columns = super(SQLAModelView, self).scaffold_list_columns()
        for column in self.forbidden_columns:
            columns.remove(column)
        return columns

    def scaffold_form(self):
        form = super(SQLAModelView, self).scaffold_form()
        for column in self.forbidden_columns:
            delattr(form, column)
        delattr(form, "email")
        return form

    def is_accessible(self):
        if request.endpoint == "userview.edit_view" and \
                int(request.args['id']) == current_user.id:
            return current_user.is_authenticated() and \
                    (current_user.has_role('admin') or \
                    current_user.has_role('superadmin'))
        return current_user.is_authenticated() and \
                current_user.has_role('superadmin')
