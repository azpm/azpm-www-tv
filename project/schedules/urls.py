from django.conf.urls import *

urlpatterns = patterns(
    "project.schedules.views",
    url(r"^api/$", "api_handler", name="tv-schedules-api-handler"),
    url(r"^search/$", "search", name="schedules-search"),
    url(r"^printcenter/$", "print_center", name="printable-protrack-schedules"),
    url(r"^series/(?P<series>.*)/$", "series_air_list", name="series-by-nola"),
    url(r"^episode/(?P<episode>\d+)/$", "episode_detail", name="episode-detail"),
    url(
        r"^week/(?P<channel>\w+)/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d+)/$",
        "channel_week",
        name="channel-week-glance",
    ),
    url(
        r"^(?P<channel>\w+)/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d+)/$",
        "channel",
        name="channel-date",
    ),
    url(r"^(?P<channel>\w+)/$", "channel", name="channel-today"),
    url(
        r"^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d+)/$",
        "schedules_main",
        name="schedules-date",
    ),
    url(r"^$", "schedules_main", name="schedules-index"),
)
