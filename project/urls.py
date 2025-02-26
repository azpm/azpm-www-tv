from django.conf.urls import *
from django.contrib import admin
from libscampi.contrib import cms

from project.schedules.views.sitemap import ChannelMap, SeriesMap

sitemaps = {"channel": ChannelMap, "series": SeriesMap}

admin.autodiscover()

urlpatterns = patterns(
    "",
    (r"^comments/", include("django.contrib.comments.urls")),
    (
        r"^schedules/map\.xml$",
        "django.contrib.sitemaps.views.sitemap",
        {"sitemaps": sitemaps},
    ),
    (r"^schedules/", include("project.schedules.urls"), {"keyname": "schedules"}),
    (r"^admin/doc/", include("django.contrib.admindocs.urls")),
    (r"^admin/", include(admin.site.urls)),
    (r"", include(cms.site.urls)),
)
