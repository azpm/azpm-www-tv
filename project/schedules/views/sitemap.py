from django.contrib.sitemaps import Sitemap
from django.core.urlresolvers import reverse
from django.core.exceptions import ViewDoesNotExist
from libazpm.contrib.chronologia.models import *


class ChannelMap(Sitemap):
    changefreq = "never"
    priority = 0.5

    def items(self):
        return Service.objects.filter(active=True, typing="tv")

    def location(self, obj):
        return "/schedules/{0:>s}".format(obj.keyname)


class SeriesMap(Sitemap):
    changefreq = "daily"
    priority = 0.5

    def items(self):
        return Series.objects.all()

    def location(self, obj):
        try:
            r = reverse("series-by-nola", kwargs={"series": obj.nola})
        except ViewDoesNotExist:
            r = ""

        return r
