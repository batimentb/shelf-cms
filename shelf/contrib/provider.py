from ..admin.widget import DonutProvider, TextProvider, BarProvider
from analytics import Analytics
from operator import itemgetter
import calendar
import datetime

analytics = Analytics("")
analytics.prepare()

class AnalyticsDonutProvider(DonutProvider):
    cache = None

    def __init__(self, metric, dimension, start=None, end=None):
        self.metric = metric
        self.dimension = dimension
        self.start = start
        self.end = end
        self.cache = None

    def get_cache(self):
        if self.cache is None:
            raw = analytics.get_stats((self.metric,), (self.dimension,), start=self.start, end=self.end)
            raw = [(dimension.split('-')[0].split('_')[0], int(raw[dimension][self.metric])) for dimension in raw]
            unsorted_metrics = {'others': 0}       
            total = sum([l[1] for l in raw]) 
            threshold = total / 50
            for dimension, metric in raw:
                if metric < threshold:
                    unsorted_metrics['others'] = unsorted_metrics['others'] + metric
                else:
                    if dimension not in unsorted_metrics:
                        unsorted_metrics[dimension] = 0
                    unsorted_metrics[dimension] = unsorted_metrics[dimension] + metric                    
            if unsorted_metrics['others'] == 0:
                del unsorted_metrics['others']
            self.cache = sorted([(x, unsorted_metrics[x]) for x in unsorted_metrics], key=itemgetter(1), reverse=True)
        return self.cache

    def get_legend(self):
        metrics = self.get_cache()
        best = metrics[0]
        total = sum([metric for dimension, metric in metrics]) 
        return "<b>%d%%</b> %s" % (round(best[1] * 100 / float(total), 0), best[0])

    def get_points(self):
        metrics = self.get_cache()
        total = sum([metric for dimension, metric in metrics]) 
        return [{"label": dimension, "value": metric, "percent": int(round(metric * 100 / float(total), 0))} for dimension, metric in metrics]

class AnalyticsTextProvider(TextProvider):
    def __init__(self, metric, normalize=None, step=None):
        self.metric = metric
        self.normalize = normalize
        self.step = step if step else datetime.timedelta(days=30)

    def get_cache(self):
        curmonth = u"%02d" % datetime.date.today().month
        curday = datetime.date.today().day
        lastmonth = u"12" if datetime.date.today().month == 1 else u"%02d" % (datetime.date.today().month - 1)
        lastmonthdays = calendar.mdays[int(lastmonth)]

        if self.normalize:            
            res = analytics.get_stats((self.metric, self.normalize), ("month",), start=datetime.date.today() - 2 * self.step)
            current_month = res[curmonth]
            last_month = res[lastmonth]
            current_month = float(current_month[self.metric]) / float(current_month[self.normalize])
            last_month = float(last_month[self.metric]) / float(last_month[self.normalize])
        else:
            res = analytics.get_stats((self.metric,), ("month",), start=datetime.date.today() - 2 * self.step)
            current_month = res[curmonth][self.metric]
            last_month = res[lastmonth][self.metric]
        return {
            "last": (float(last_month) / float(lastmonthdays)) * (curday - 1),
            "current": float(current_month)
        }

    def get_data(self):
        cache = self.get_cache()
        return "%d" % int(cache["current"])

    def get_legend(self):
        cache = self.get_cache()
        evolution = cache["current"] - cache["last"]
        if evolution > 0:
            return "<span class='value'>+{0} ({1}%)</span> since last month".format(int(evolution), int(round(100 * (abs(evolution) / float(cache["current"])))))
        elif evolution < 0:
            return "<span class='value-bad'>{0} (-{1}%)</span> since last month".format(int(evolution), int(round(100 * (abs(evolution) / float(cache["current"])))))
        return "Same than last month"

class AnalyticsBarProvider(BarProvider):
    cache = None

    def __init__(self, metric, dimension, start=None, end=None):
        self.metric = metric
        self.dimension = dimension
        self.start = start
        self.end = end
        self.cache = None

    def get_cache(self):
        if self.cache is None:
            raw = analytics.get_stats((self.metric,), (self.dimension,), start=self.start, end=self.end)
            raw = [(dimension.split('-')[0].split('_')[0], int(raw[dimension][self.metric])) for dimension in raw]
            unsorted_metrics = {'others': 0}       
            total = sum([l[1] for l in raw]) 
            threshold = total / 50
            for dimension, metric in raw:
                if metric < threshold:
                    unsorted_metrics['others'] = unsorted_metrics['others'] + metric
                else:
                    if dimension not in unsorted_metrics:
                        unsorted_metrics[dimension] = 0
                    unsorted_metrics[dimension] = unsorted_metrics[dimension] + metric 
            if unsorted_metrics['others'] == 0:
                del unsorted_metrics['others']
            self.cache = sorted([(x, unsorted_metrics[x]) for x in unsorted_metrics], key=itemgetter(1), reverse=True)
        return self.cache

    def get_max(self):
        metrics = self.get_cache()
        return max([metric for dimension, metric in metrics])

    def get_total(self):
        metrics = self.get_cache()
        return sum([metric for dimension, metric in metrics])

    def get_points(self):
        metrics = self.get_cache()
        return [{"label": dimension, "value": metric} for dimension, metric in metrics]