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

class BaseProvider:
    def compute():
        raise NotImplementedError

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

class TextProvider(BaseProvider):
    def get_data(self):
        raise NotImplementedError

    def get_legend(self):
        raise NotImplementedError

    def compute(self):
        return {
            "data": self.get_data(),
            "legend": self.get_legend()
        }

class TextWidget(BaseWidget):
    template = "shelf/dashboard/text.html"

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
       
class DonutProvider(BaseProvider):
    def get_legend(self):
        raise NotImplementedError

    def get_points(self):
        raise NotImplementedError

    def compute(self):
        return {
            "legend": self.get_legend(),
            "points": self.get_points()
        }

class DonutWidget(TextWidget):
    template = "shelf/dashboard/donut.html"

    def __init__(self, *args, **kwargs):
        TextWidget.__init__(self, *args, **kwargs)
        self.style["rows"] = kwargs["rows"] if "rows" in kwargs else 2
        self.style["donut_colors"] = kwargs["donut_colors"] if "donut_colors" in kwargs else ['#224397', '#4d639c', '#7b8dbb', '#b9c2db', '#dde0e9']
        self.style["label_color"] = kwargs["label_color"] if "label_color" in kwargs else "#4c4c4c"

class BarProvider(BaseProvider):
    def get_points(self):
        raise NotImplementedError

    def get_max(self):
        raise NotImplementedError

    def get_total(self):
        raise NotImplementedError

    def compute(self):
        return {
            "points": self.get_points(),
            "max": self.get_max(),
            "total": self.get_total()
        }

class BarWidget(TextWidget):
    template = "shelf/dashboard/bar.html"

    def __init__(self, *args, **kwargs):
        TextWidget.__init__(self, *args, **kwargs)
        self.style["rows"] = kwargs["rows"] if "rows" in kwargs else 2
        self.style["bar_colors"] = kwargs["bar_colors"] if "donut_colors" in kwargs else ['#224397', '#4d639c', '#7b8dbb', '#b9c2db', '#dde0e9']

class EvolutionDashboardWidget(DashboardWidget):
    def __init__(self, title, metric, start=None, end=None, step=None, nb=12, icon=None):
        DashboardWidget.__init__(self, title)
        self.template = "shelf/dashboard/evolution.html"
        self.metric = metric
        self.nb = nb
        self.step = step if step else datetime.timedelta(days=30)
        self.start = start if start else datetime.date.today() - nb * self.step
        self.end = end if end else datetime.date.today()
        if icon:
            self.icon = icon

    def update(self):
        '''d = self.start
        stats = []
        while d < self.end:
            stat = analytics.get_stats((self.metric,), start=d, end=d + self.step)[self.metric]
            stats.append(int(stat))
            d = d + self.step
        self.data = stats'''
        res = analytics.get_stats((self.metric,), ("month",), start=datetime.date.today() - datetime.timedelta(days=365), end=datetime.date.today())
        monthnames = [None, 'Jan', 'Fev', 'Mar', 'Apr', 'May', 
            'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        startmonth = datetime.date.today().month
        months = []
        for i in range(1, 12):
            month = startmonth + i
            if month > 12:
                month = month % 12
            months.append(month)

        self.legend = ([monthnames[month] for month in months])
        self.data = [float(res['%02d' % month][self.metric]) for month in months]

        self.shouldUpdate = False

    def render(self):
        if self.shouldUpdate:
            self.update()
        return render_template(self.template, title=self.title, data=self.data, legend=self.legend, icon=self.icon)

class RepartitionDashboardWidget(DashboardWidget):
    def __init__(self, title, metric, dimension, icon=None):
        DashboardWidget.__init__(self, title)
        self.template = "shelf/dashboard/repartition.html"
        self.dimension = dimension
        self.metric = metric
        if icon:
            self.icon = icon

    def compute(self, data):
        tmp = [(lang.split('-')[0].split('_')[0], int(data[lang][self.metric])) for lang in data]
        res = {'others': 0}       
        total = sum([l[1] for l in tmp]) 
        threshold = total / 50
        for lang, tot in tmp:
            if lang not in res:
                res[lang] = 0
            if tot >= threshold:
                res[lang] = res[lang] + tot
            else:
                res['others'] = res['others'] + tot
        langs = sorted([(x, res[x]) for x in res], key=itemgetter(1), reverse=True)

        return langs

    def update(self):
        #current_month = analytics.get_stats((self.metric,), start=datetime.date.today() - datetime.timedelta(days=30))[self.metric]
        #last_month = analytics.get_stats((self.metric,), start=datetime.date.today() - datetime.timedelta(days=60), end=datetime.date.today() - datetime.timedelta(days=30))[self.metric]

        self.data = self.compute(analytics.get_stats((self.metric,), (self.dimension,), start=datetime.date.today() - datetime.timedelta(days=30)))

        self.shouldUpdate = False

    def render(self):
        if self.shouldUpdate:
            self.update()
        return render_template(self.template, title=self.title, datas=self.data, icon=self.icon)

class TextDashboardWidget(DashboardWidget):
    def __init__(self, title, metric, step=None, icon=None, normalize=None, todata=None):
        DashboardWidget.__init__(self, title)
        self.template = "shelf/dashboard/simple-text.html"
        self.metric = metric
        self.step = step if step else datetime.timedelta(days=30)
        self.normalize = normalize if normalize else None
        if icon:
            self.icon = icon
        self.todata = todata if todata else lambda x: int(x)

    def update(self):
        curmonth = u"%02d" % datetime.date.today().month
        lastmonth = u"12" if datetime.date.today().month == 1 else u"%02d" % (datetime.date.today().month - 1)

        if self.normalize:            
            res = analytics.get_stats((self.metric, self.normalize), ("month",), start=datetime.date.today() - 2 * self.step)
            current_month = res[curmonth]
            last_month = res[lastmonth]

            current_month = float(current_month[self.metric]) / float(current_month[self.normalize])
            last_month = float(last_month[self.metric]) / float(last_month[self.normalize])
            evolution = current_month - last_month
        else:
            res = analytics.get_stats((self.metric,), ("month",), start=datetime.date.today() - 2 * self.step)
            current_month = res[curmonth][self.metric]
            last_month = res[lastmonth][self.metric]
            evolution = float(current_month) - float(last_month)
        
        if evolution > 0:
            self.legend = "<span class='value'>+{0} ({1}%)</span> since last month".format(int(evolution), int(round(100 * (abs(evolution) / float(current_month)))))
        elif evolution < 0:
            self.legend = "<span class='value-bad'>{0} (-{1}%)</span> since last month".format(int(evolution), int(round(100 * (abs(evolution) / float(current_month)))))
        else:
            self.legend = "Same than last month"

        self.shouldUpdate = False

    def render(self):
        if self.shouldUpdate:
            self.update()
        return render_template(self.template, title=self.title, legend=self.legend, data=self.data, icon=self.icon)
