from .base import (
    Index,
    ChannelView,
    ChannelWeek,
    AllSeries,
    SeriesAirs,
    EpisodeDetail,
    Search,
    PrintCenter,
    API,
)

# alaises the class based views so we don't have to change url conf
__all__ = [
    "schedules_main",
    "channel",
    "channel_week",
    "episode_detail",
    "series_air_list",
    "all_series",
    "search",
    "api_handler",
    "print_center",
]


schedules_main = Index.as_view()
channel = ChannelView.as_view()
channel_week = ChannelWeek.as_view()
episode_detail = EpisodeDetail.as_view()
series_air_list = SeriesAirs.as_view()
all_series = AllSeries.as_view()
search = Search.as_view()
api_handler = API.as_view()
print_center = PrintCenter.as_view()
