from oauth2client.client import SignedJwtAssertionCredentials
from apiclient.discovery import build
from oauth2client.file import Storage
from httplib2 import Http
from urllib import urlencode
import datetime
import calendar
from flask import current_app
from shelf.plugins.dashboard.provider import TextProvider, DonutProvider, BarProvider

class AddthisAnalytics:
    def init_app(self, app):
        self.email = app.config.get('ADDTHIS_EMAIL')
        self.password = app.config.get('ADDTHIS_PASSWORD')
        self.pubid = app.config.get('ADDTHIS_PUBID')

    def get_stats(self, metric, dimension=None, filters=None):
        h = Http('test-scripts/.cache')
        h.add_credentials(self.email, self.password)
        if dimension:
            url = "https://api.addthis.com/analytics/1.0/pub/%s/%s.json" % (metric, dimension)
        else:
            url = "https://api.addthis.com/analytics/1.0/pub/%s.json" % metric
        data = dict(("pubid", self.pubid) + filters.items()) if \
            filters else {"pubid": self.pubid}
        resp, content = h.request("%s?%s" % (url, urlencode(data)), "GET")
        return content

class GoogleAnalytics:
    DEFAULT_START = datetime.date.today() - datetime.timedelta(days=30)
    DEFAULT_END = datetime.date.today() 

    def __init__(self):
        self.profile = None
        self.analytics = None

    def init_app(self, app):
        self.app = app
        self.keyfile = app.config.get('GOOGLE_API_P12')
        self.email = app.config.get('GOOGLE_API_EMAIL')
        self.profile = app.config.get('GOOGLE_ANALYTICS_VIEW')
        self.property = app.config.get('GOOGLE_ANALYTICS_PROPERTY')

    def prepare(self):
        self.http = Http()

        with file(self.keyfile, "rb") as f:
            credentials = SignedJwtAssertionCredentials(
                self.email,
                f.read(),
                scope='https://www.googleapis.com/auth/analytics.readonly'
            )

        self.http = credentials.authorize(self.http)
        self.analytics = build('analytics', 'v3', http=self.http)

    def get_stats(self, metrics=None, dimensions=None, start=None, end=None):
        if not self.analytics:
            self.prepare()

        start = start if start else self.DEFAULT_START
        end = end if end else self.DEFAULT_END

        if not (metrics or dimensions):
            raise ValueError

        raw_res = self.analytics.data().ga().get(
            ids='ga:' + self.profile,
            start_date=str(start),
            end_date=str(end),
            metrics=','.join(['ga:%s' % m for m in metrics]) if metrics else None,
            dimensions=','.join(['ga:%s' % m for m in dimensions]) if dimensions else None).execute()

        results = {}

        for row in raw_res.get('rows'):
            ptr = results
            if dimensions:
                for i in range(len(dimensions)):
                    dim = dimensions[i]
                    if row[i] not in ptr:
                        ptr[row[i]] = {}
                    ptr = ptr[row[i]]
            
            for i in range(len(metrics)):
                met = metrics[i]
                ptr[met] = row[i+len(dimensions) if dimensions else i]

        return results


class GoogleAnalyticsTextProvider(TextProvider):
    def __init__(self, ga, data, metrics, legend=None, legend_metrics=None, dates=None):
        self.data = data
        self.legend = legend
        self.metrics = metrics
        self.legend_metrics = legend_metrics
        if dates:
            self.start, self.end, self.refstart, self.refend = dates
        else:
            now = datetime.date.today()
            self.start = datetime.date(year=now.year, month=now.month, day=1)
            self.end = datetime.date(year=now.year, month=now.month, day=now.day)
            print self.start, self.end

            prevmonth = now.month - 1 if now.month > 1 else 12
            lastdayofprevmonth = calendar.monthrange(now.year, prevmonth)[1]
            prevyear = now.year - 1 if prevmonth == 12 else now.year
            self.refstart = datetime.date(year=prevyear, month=prevmonth, day=1)
            self.refend = datetime.date(year=prevyear, month=prevmonth, day=lastdayofprevmonth)
            print "=>", self.refstart, self.refend
        self.ga = ga

    def format_data(self, **kwargs):
        if self.data:
            return self.data.format(**kwargs)
        else:
            return ""

    def get_data(self):
        if self.metrics:
            metrics = self.ga.get_stats(
                self.metrics,
                start=self.start,
                end=self.end
            )
        else:
            return None
        return self.format_data(**metrics)

    def format_legend(self, **kwargs):
        if self.legend:
            return self.legend.format(**kwargs)
        else:
            return ""

    def get_legend(self):
        if self.legend_metrics:
            metrics = self.ga.get_stats(
                self.legend_metrics,
                start=self.refstart,
                end=self.refend
            )
        else:
            return None
        return self.format_legend(**metrics)


class GoogleAnalyticsDonutProvider(DonutProvider):
    def __init__(self, ga, metric, dimension, dates=None):
        self.ga = ga
        if dates:
            self.start, self.end = dates
        else:
            self.start = None
            self.end = None
        self.metric = metric
        self.dimension = dimension

    def get_points(self):
        metrics = self.ga.get_stats(
            (self.metric,),
            (self.dimension,),
            start=self.start,
            end=self.end
        )
        tmp = []
        res = []
        total = 0
        for label in metrics.keys():
            value = int(metrics[label][self.metric])
            total += value
            tmp.append({"label": label, "value": value})
        for x in tmp:
            label = x['label']
            value = x['value']
            percent = int(value * 100.0 / float(total))
            if percent > 0:
                res.append({"label": label, "value": value, "percent": percent})
        res = sorted(res, key=lambda x: x['value'], reverse=True)
        return res

    def get_legend(self):
        return ""

class GoogleAnalyticsBarProvider(BarProvider):
    def __init__(self, ga, metric, dimension, dates=None):
        self.ga = ga
        if dates:
            self.start, self.end = dates
        else:
            self.start = None
            self.end = None
        self.metric = metric
        self.dimension = dimension
        self.max = None

    def get_points(self):
        metrics = self.ga.get_stats(
            (self.metric,),
            (self.dimension,),
            start=self.start,
            end=self.end
        )
        tmp = []
        res = []
        total = 0
        self.max = -1
        for label in metrics.keys():
            value = int(metrics[label][self.metric])
            total += value
            self.max = value if value > self.max else self.max
            tmp.append({"label": label, "value": value})
        self.total = total
        for x in tmp:
            label = x['label']
            value = x['value']
            percent = int(value * 100.0 / float(total))
            if percent > 0:
                res.append({"label": label, "value": value, "percent": percent})
        res = sorted(res, key=lambda x: x['value'], reverse=True)
        return res

    def get_max(self):
        if self.max is None:
            self.get_points()
        print "MAX", self.max
        return self.max

    def get_total(self):
        if self.total is None:
            self.get_points()

        print "TOTAL", self.total
        return self.total
