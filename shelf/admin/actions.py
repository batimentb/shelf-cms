from flask.ext.admin import actions
from flask.ext.admin.contrib.sqla.tools import get_query_for_ids
from flask import request, url_for, redirect, flash


class ActionsMixin(actions.ActionsMixin):
    def _get_action_filter_args(self):
        if self._filters and request.form.get('filters', None):
            filters = []

            for n in request.form.get('filters', None).split(','):
                if not n.startswith('flt'):
                    continue

                if "_" not in n:
                    continue

                if "=" not in n:
                    continue

                arg, val = n[3:].split("=", 1)
                pos, key = arg.split("_", 1)

                if key in self._filter_args:
                    idx, flt = self._filter_args[key]

                    value = val

                    if flt.validate(value):
                        filters.append((pos, (idx, flt.clean(value))))

            return [v[1] for v in sorted(filters, key=lambda n: n[0])]

        return None

    def _get_action_extra_args(self):
        page = request.form.get('page')
        sort = request.form.get('sort')
        desc = request.form.get('desc', None, type=int)
        search = request.form.get('search', None)
        filters = self._get_action_filter_args()

        return page, sort, desc, search, filters

    def handle_action(self, return_view=None):
        action = request.form.get('action')
        ids = request.form.getlist('rowid')
        page, sort, sort_desc, search, filters = self._get_action_extra_args()
        select_all = request.form.get('select-all', 0, type=int)
        select_page = request.form.get('select-page', 0, type=int)

        if select_all:
            count, query = self.get_list(None, sort, sort_desc, search, filters, False, nolimit=True)
        elif select_page:
            count, query = self.get_list(page, sort, sort_desc, search, filters, False)
        else:
            query = get_query_for_ids(self.get_query(), self.model, ids)

        handler = self._actions_data.get(action)

        if handler and self.is_action_allowed(action):
            response = handler[0](ids, query)

            if response is not None:
                return response

        if not return_view:
            url = url_for('.' + self._default_view)
        else:
            url = url_for('.' + return_view)

        return redirect(url)
