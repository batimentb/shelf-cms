import datetime
from flask import render_template, url_for
from operator import itemgetter
import math


class DashboardWidget:
    shouldUpdate = False
    template = None
    title = None

    def __init__(self, title):
        self.shouldUpdate = True
        self.template = None
        self.title = title

    def update(self):
        raise NotImplementedError

    def render(self):
        if self.shouldUpdate:
            self.update()
        if not self.template:
            raise NotImplementedError
        else:
            return render_template(self.template)


class BaseWidget:
    template = None
    title = None
    style = None
    provider = None

    def __init__(self, title, provider=None, classes=[],
                icon=None, icon_color=None, 
                background_color="#ffffff",
                title_color=None, title_size=None,
                columns=2, rows=1, **kwargs):
        self.title = title

        self.style = { "classes": classes }
        if icon:
            self.style["icon"] = icon
        if icon_color:
            self.style["icon_color"] = icon_color
        if background_color:
            self.style["background_color"] = background_color
        if title_color:
            self.style["title_color"] = title_color
        if title_size:
            self.style["title_size"] = title_size
        if columns:
            self.style["columns"] = columns
        if rows:
            self.style["rows"] = rows

        if provider:
            self.provider = provider

    def render(self):
        if not self.provider:
            raise ValueError
        if not self.template:
            raise NotImplementedError      
        return render_template(self.template, 
                                title=self.title,
                                style=self.style,
                                **self.provider.compute())


class TextWidget(BaseWidget):
    template = "simple-text.html"

    def __init__(self, *args, **kwargs):
        BaseWidget.__init__(self, *args, **kwargs)
        if "legend_size" in kwargs:
            self.style["legend_size"] = kwargs["legend_size"]
        if "legend_color" in kwargs:
            self.style["legend_color"] = kwargs["legend_color"]
        if "data_size" in kwargs:
            self.style["data_size"] = kwargs["data_size"]
        if "data_color" in kwargs:
            self.style["data_color"] = kwargs["data_color"]


class PictureWidget(TextWidget):
    template = "picture-text.html"


class EvolutionWidget(TextWidget):
    template = "evolution.html"


class DonutWidget(TextWidget):
    template = "donut.html"

    def __init__(self, *args, **kwargs):
        TextWidget.__init__(self, *args, **kwargs)
        self.style["rows"] = kwargs["rows"] if "rows" in kwargs else 2
        grays = [
            '#696969', '#707070', '#787878', '#808080', '#828282', '#8A8A8A', 
            '#919191', '#999999', '#A1A1A1', '#A9A9A9', '#ABABAB', '#B0B0B0',
            '#B8B8B8', '#C0C0C0', '#C2C2C2', '#C9C9C9', '#CFCFCF', '#D3D3D3', 
            '#D9D9D9', '#DEDEDE', '#E5E5E5', '#DEDEDE', '#F5F5F5', '#FCFCFC'
        ]
        self.style["donut_colors"] = kwargs["donut_colors"] if "donut_colors" in kwargs else ['#ff9d98',] + grays
        self.style["label_color"] = kwargs["label_color"] if "label_color" in kwargs else "#4c4c4c"


class BarWidget(TextWidget):
    template = "bar.html"

    def __init__(self, *args, **kwargs):
        TextWidget.__init__(self, *args, **kwargs)
        self.style["rows"] = kwargs["rows"] if "rows" in kwargs else 2
        self.style["bar_colors"] = kwargs["bar_colors"] if "bar_colors" in kwargs else ['#ff9d98', '#a7a7a7', '#bebebe', '#dddddd', '#f8f8f8']

