from shelf.admin.view import SQLAModelView

from shelf.plugins.library import PictureField, LibraryViewMixin
from shelf.plugins.workflow import WorkflowViewMixin, StateField
from shelf.plugins.wysiwyg import ClassicWysiwygField, WysiwygViewMixin

class PostModelView(SQLAModelView, LibraryViewMixin, 
			   WysiwygViewMixin, WorkflowViewMixin):
	column_list = ('title', 'state')
	form_columns = (
        "title", "content", "picture", "state"
    )
	form_overrides = {
        "content": ClassicWysiwygField,
        "picture": PictureField,
        "state": StateField
    }