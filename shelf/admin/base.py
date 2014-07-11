import flask_admin
from view import IndexView


class Admin(flask_admin.Admin):
    """ Custom admin class """

    def __init__(self, *args, **kwargs):
        """ Init class """

        if "base_template" not in kwargs:
            kwargs["base_template"] = "shelf/base.html"

        if "index_view" not in kwargs:
        	endpoint = kwargs['endpoint'] if 'endpoint' in kwargs else None
        	url = kwargs['url'] if 'url' in kwargs else None
        	kwargs["index_view"] = IndexView(endpoint=endpoint, url=url, template='shelf/index.html')

        super(Admin, self).__init__(*args, **kwargs)
