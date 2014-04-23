from ..contrib.analytics import Analytics
import datetime
from flask import render_template, url_for
from operator import itemgetter
import math

analytics = Analytics("")
analytics.prepare()

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
        print months
        print res

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
            self.data = self.todata(current_month)
        else:
            res = analytics.get_stats((self.metric,), ("month",), start=datetime.date.today() - 2 * self.step)
            current_month = res[curmonth][self.metric]
            last_month = res[lastmonth][self.metric]
            evolution = float(current_month) - float(last_month)

            self.data = self.todata(float(current_month))

        
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
