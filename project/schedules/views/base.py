import logging
import calendar

from datetime import datetime, date, timedelta
from random import randint

from django.db.models import Q, Max
from django.core.cache import cache
from operator import ior, iand
from string import punctuation
from django.conf import settings
from django.shortcuts import get_object_or_404, get_list_or_404
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.views.generic import FormView, TemplateView

from libazpm.contrib.calendar.legacy.helpers import generate_calendars
from libazpm.contrib.chronologia.models import Service, Series, Season, Episode, EpisodeAir, Air
from libazpm.contrib.chronologia.forms import *

from libscampi.contrib.cms.views.base import Page
from libscampi.contrib.cms.communism.models import *

from .mixins import ChannelMixin

logger = logging.getLogger('project.schedules')

class SchedulesPage(Page):
    base_title = u"TV Schedules"
    cached_css_key = 'schedules:css'
    cached_js_key = 'schedules:js'

    #the static files gravity css for schedules
    schedules_css = {
        'url': "%sintensifier/css/schedules.css" % settings.STATIC_URL,
        'media': "screen",
        'for_ie': False
    }

    def get_static_styles(self):
        return [self.schedules_css]

    def get_theme(self):
        try:
            theme = Theme.objects.get(keyname="intensifier")
        except Theme.DoesNotExist:
            theme = Theme.objects.none()
            
        return theme

    def get_page_title(self):
        return self.base_title
        
class Index(SchedulesPage):
    template_name = 'schedules/index.html'
    
    def get_context_data(self, *args, **kwargs):
        context = super(Index, self).get_context_data(*args, **kwargs)
        
        try:
            year, month, day = self.kwargs['year'], self.kwargs['month'], self.kwargs['day']
        except (ValueError, KeyError):
            day = date.today()
        else:
            try:
                day = date(int(year), int(month), int(day))
            except (ValueError, TypeError):
                raise Http404
                
        future_date = day + timedelta(days=14) #get a date 14 days out
        services = Service.objects.filter(active = True, typing = "tv")
        calendars = generate_calendars(day, future_date)

        primetime = [{'service': service, 'day': day, 'airing': service.primetime_for_day(day)}
            for service in services]
        
        c = {
            'service': None,
            'services' : services,
            'calendars': calendars,
            'max_days': future_date,
            'idealised_day': day,
            'primetime': primetime,
            'today': date.today()
        }
        
        context.update(c)
        
        return context

class ChannelView(ChannelMixin, SchedulesPage):
    template_name = 'schedules/channel.html'
            
    def get_page_title(self):
        return u"%s | %s" % (self.channel.name, self.base_title)
    
    def get_context_data(self, *args, **kwargs):
        context = super(ChannelView, self).get_context_data(*args, **kwargs)
        
        try:
            year, month, day = self.kwargs['year'], self.kwargs['month'], self.kwargs['day']
        except (ValueError, KeyError):
            day = date.today()
        else:
            try:
                day = date(int(year), int(month), int(day))
            except (ValueError, TypeError):
                raise Http404
        
        today = date.today()
        services = Service.objects.filter(active = True, typing = "tv")

        airing = EpisodeAir.objects.select_related('service','episode','episode__season','episode__season__series').filter(service = self.channel).filter(date = day).order_by('date','time')
        if not airing.exists():
            raise Http404
        
        last_time = EpisodeAir.objects.filter(service = self.channel).aggregate(latest = Max('date'))
        if last_time['latest'] is None:
            latest = today + datetime.timedelta(14)
        else:
            latest = last_time['latest']
        
        calendars = generate_calendars(today, latest)
        
        c = {
            'service': self.channel,
            'services' : services,
            'calendars': calendars,
            'max_days': latest,
            'idealised_day': day,
            'airing': airing,
            'today': today,
        }
        
        context.update(c)
        
        return context     
        
class ChannelWeek(ChannelMixin, SchedulesPage):
    template_name = 'schedules/channel_week.html'
    
    def get_page_title(self):
        return u"Weekly Schedule for %s | %s" % (self.channel.name, self.base_title)
        
    def get_context_data(self, *args, **kwargs):
        context = super(ChannelWeek, self).get_context_data(*args, **kwargs)

        try:
            year, month, day = self.kwargs['year'], self.kwargs['month'], self.kwargs['day']
        except (ValueError, KeyError):
            raise Http404
        else:    
            try:
                basedate =  date(int(year), int(month), int(day))  
            except (TypeError, ValueError):
                raise Http404
            
        c = calendar.Calendar(6)
        cal = c.monthdatescalendar(basedate.year, basedate.month)
        
        #this bit of fucking sexy code gives me the week I want
        week = [i for i in cal if basedate in i][0]
            
        services = Service.objects.filter(active = True, typing = "tv")
        airing = EpisodeAir.objects.select_related().filter(service = self.channel).filter(date__range=[week[0],week[len(week)-1]]).order_by('date','time').values('date','time','episode__id','episode__short_description','episode__season__series__name')

        last_time = EpisodeAir.objects.filter(service = self.channel).aggregate(latest = Max('date'))
        if last_time['latest'] is None:
            latest = basedate + datetime.timedelta(14)
        else:
            latest = last_time['latest']
            
        calendars = generate_calendars(date.today(), latest)
            
        c = {
            'airing': airing,
            'service': self.channel,
            'services': services,
            'calendars': calendars,
            'idealised_day': basedate,
            'max_days': latest,
            'week': week,
        }
        
        context.update(c)
        
        return context       

class AllSeries(SchedulesPage):
    pass
    
class EpisodeDetail(SchedulesPage):
    template_name = 'schedules/episode_detail.html'
    episode = None
    
    def get_page_title(self):
        return u" Episode of %s | %s" % (self.episode.season.series.name.strip(), self.base_title)
        
    def get(self, request, *args, **kwargs):
        #keyname specified in url
        if 'episode' in kwargs:
            id = kwargs.pop('episode')
            self.episode = get_object_or_404(Episode.objects.select_related('season','season__series'), pk = id)
        else:
            raise Http404
            
        #finally return the parent get method
        return super(EpisodeDetail, self).get(request, *args, **kwargs)
        
    def get_context_data(self, *args, **kwargs):
        context = super(EpisodeDetail, self).get_context_data(*args, **kwargs)
        
        today = date.today()
        
        #future = EpisodeAir.objects.select_related('service').filter(episode = self.episode, date__gte=today).values('service__name','service__keyname','time','date').order_by('date','time')
        #past = EpisodeAir.objects.select_related('service').filter(episode = self.episode, date__lt=today).values('service__name','service__keyname','time','date').order_by('date','time')[:25]

        future = self.episode.airs.filter(date__gte=today).values('service__name','service__keyname','time','date').order_by('date','time')
        past = self.episode.airs.filter(date__lt=today).values('service__name','service__keyname','time','date').order_by('date','time')[:25]

        c = {
            'episode': self.episode,
            'future_airs': future,
            'past_airs': past,
        }
        
        context.update(c)
        
        return context
    
class SeriesAirs(SchedulesPage):
    template_name = 'schedules/series_detail.html'
    series = None
    
    def get_page_title(self):
        return u"%s | %s" % (self.series[0].name, self.base_title)
        
    def get(self, request, *args, **kwargs):
        #keyname specified in url
        if 'series' in kwargs:
            series_nola = kwargs.pop('series')
            self.series = get_list_or_404(Series, nola = series_nola)
        else:
            raise Http404
            
        #finally return the parent get method
        return super(SeriesAirs, self).get(request, *args, **kwargs)
        
    def get_context_data(self, *args, **kwargs):
        context = super(SeriesAirs, self).get_context_data(*args, **kwargs)
        
        today = date.today()
        date_future = today + timedelta(31)
        
        actuals = []
        
        for i in range(0, len(self.series)):
            try:
                airs = EpisodeAir.objects.select_related('service','episode','episode__season','episode__season__series').filter(episode__season__series=self.series[i], date__range=[today,date_future]).order_by('date','time')
            except:
                airs = EpisodeAir.objects.none()
            
            if airs:
                actuals.append({'series': self.series[i], 'airing': airs})
        
        c = {
            'items': actuals,
            'series': self.series,
            'base_series': self.series[0],
        }
        
        context.update(c)
        
        return context

    
class Search(SchedulesPage, FormView):
    template_name = 'schedules/search_results.html'
    form_class = SearchSchedulesForm
    
    def get(self, request, *args, **kwargs):
        return super(Search, self).get(request, *args, **kwargs)
        
    def post(self, request, *args, **kwargs):
        return super(Search, self).post(request, *args, **kwargs)

    def get_page_title(self):
        return u"Search | %s" % self.base_title
    
    def get_context_data(self, **kwargs):
        context = super(Search, self).get_context_data(**kwargs)

        form = kwargs.get('form', None)
        query = kwargs.get('query', None)
        results = kwargs.get('results', None)

        c = {
            'form': form,
            'query': query,
            'results': results
        }
        
        context.update(c)
        return context
    
    def get_form_kwargs(self):
        kwargs = super(Search, self).get_form_kwargs()
        kwargs.update({"prefix": "searchcc"})
        
        return kwargs
        
    def form_valid(self, form):
        service = form.cleaned_data['service']
        query = form.cleaned_data['keywords']
        start_date = form.cleaned_data['start_date'] or date.today()
        end_date = form.cleaned_data['end_date'] or start_date + timedelta(days=14)

        date_range = [start_date,end_date]

        # Remove extra spaces, put modifiers inside quoted terms.
        terms = " ".join(query.split()).replace("+ ", "+").replace('+"', '"+'
        ).replace("- ", "-").replace('-"', '"-').split('"')
        # Strip punctuation other than modifiers from terms and create term
        # list first from quoted terms, and then remaining words.
        terms = [("" if t[0] not in "+-" else t[0]) + t.strip(punctuation)
                 for t in terms[1::2] + "".join(terms[::2]).split()]

        series_search_fields = {
            'name': 40,
            'episode__name': 5,
            'episode__short_description': 1
        }
        ep_search_fields = {
            'name': 5,
            'short_description': 1
        }

        def build_filters(fields):
            # Create the queryset combining each set of terms.
            excluded = [reduce(iand, [~Q(**{"%s__icontains" % f: t[1:]})
                                      for f in fields]) for t in terms if t[0] == "-"]
            required = [reduce(ior, [Q(**{"%s__icontains" % f: t[1:]})
                                     for f in fields]) for t in terms if t[0] == "+"]
            optional = [reduce(ior, [Q(**{"%s__icontains" % f: t})
                                     for f in fields]) for t in terms if t[0] not in "+-"]

            return excluded, required, optional

        if service:
            queryset = Series.objects.filter(episode__airs__date__range=date_range, episode__airs__service__typing="tv", episode__airs__service=service)
        else:
            queryset = Series.objects.filter(episode__airs__date__range=date_range, episode__airs__service__typing="tv")
        queryset = queryset.distinct().order_by()

        series_excluded, series_required, series_optional = build_filters(series_search_fields)
        if series_excluded:
            queryset = queryset.filter(reduce(iand, series_excluded))
        if series_required:
            queryset = queryset.filter(reduce(iand, series_required))
        # Optional terms aren't relevant to the filter if there are terms
        # that are explicitly required
        elif series_optional:
            queryset = queryset.filter(reduce(ior, series_optional))

        results = []
        for series in queryset:
            if service:
                check = EpisodeAir.objects.filter(episode__series=series, date__range=date_range, service = service)
            else:
                check = EpisodeAir.objects.filter(episode__series=series, date__range=date_range)

            if not check.exists():
                continue

            setattr(series, 'score', 0)
            base_score = 0
            for (field, weight) in series_search_fields.items():
                for term in terms:
                    field_value = getattr(series, field, None)
                    if field_value:
                        base_score += field_value.lower().count(term.lower()) * weight


            if service:
                episodes = Episode.objects.filter(airs__date__range=date_range, series=series, airs__service=service).distinct()
            else:
                episodes = Episode.objects.filter(airs__date__range=date_range, series=series).distinct()

            if not base_score:
                ep_exclude, ep_required, ep_optional = build_filters(ep_search_fields)
                if ep_exclude:
                    episodes = episodes.filter(reduce(iand, ep_exclude))
                if ep_required:
                    episodes = episodes.filter(reduce(iand, ep_required))
                elif ep_optional:
                    episodes = episodes.filter(reduce(ior, ep_optional))
            check = episodes.exists()
            if not check:
                continue

            episodes = episodes[:24]
            ep_score = 0
            for episode in episodes:
                for (field, weight) in {'name': 5, 'short_description': 4}.items():
                    for term in terms:
                        field_value = getattr(episode, field, None)
                        if field_value:
                            ep_score += field_value.lower().count(term.lower()) * weight
            series.score = ep_score+base_score

            if not series.score >= 10:
                continue
            results.append({'series': series, 'episodes': episodes})

        results = sorted(results, key=lambda k: k['series'].score, reverse=True) # actually orders for results, reverse because big #s == higher score

        c = {
            'form': form,
            'query': query,
            'results': results,
            'service': service or None,
            'start': start_date,
            'end': end_date,
        }

        return self.render_to_response(self.get_context_data(**c))



    def form_invalid(self, form):
        query = None
        
        c = {
            'form': form,
            'query': query,
            'results': None
        }

        return self.render_to_response(self.get_context_data(**c))
    
class PrintCenter(SchedulesPage, FormView):
    template_name = 'schedules/print.channel.html'
    form_class = PrintSchedulesForm

    def get(self, request, *args, **kwargs):
        return super(PrintCenter, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return super(PrintCenter, self).post(request, *args, **kwargs)

    def get_page_title(self):
        return u"Print | %s" % self.base_title

    def get_context_data(self, **kwargs):
        context = super(PrintCenter, self).get_context_data(**kwargs)

        results = kwargs.get('results', None)

        if "form" not in kwargs:
            form_class = self.get_form_class()
            form = self.get_form(form_class)
        else:
            form = kwargs.get('form')

        c = {
            'form': form,
            'results': results
        }

        context.update(c)
        return context

    def get_form_kwargs(self):
        kwargs = super(PrintCenter, self).get_form_kwargs()
        kwargs.update({"prefix": "printcc"})

        return kwargs

    def form_valid(self, form):
        start_date = form.cleaned_data['start_date'] or date.today()
        end_date = form.cleaned_data['end_date'] or start_date + timedelta(days=1)
        service = form.cleaned_data['service']

        date_range = [start_date,end_date]

        airs = EpisodeAir.objects.filter(service = service, date__range = date_range)
        if form.cleaned_data['primetime_toggle']:
            airs = airs.filter(time__range=[service.primetime_start,service.primetime_end])

        results = {
            'service': service,
            'start_date': start_date,
            'end_date': end_date,
            'airing': airs.order_by('start'),
            'primetime': form.cleaned_data['primetime_toggle'],
        }

        c = {
            'form': form,
            'results': results
        }

        return self.render_to_response(self.get_context_data(**c))


    def form_invalid(self, form):
        c = {
            'form': form,
            'results': None,
        }

        return self.render_to_response(self.get_context_data(**c))

class API(TemplateView):
    """
    Stub for motion templates API
    """
    action = None
    tpl = None
    the_date = None
    the_time = None

    def get(self, request, *args, **kwargs):
        self.action = request.GET.get('action', None)
        get_datetime = request.GET.get('dt', None)
        self.tpl = request.GET.get('tpl', 'motnbase') # use default mothnbase if no other template specified

        try:
            self.the_date = datetime.strptime(get_datetime, u"%Y-%m-%d_%H.%M.%S")
        except (ValueError, TypeError):
            raise Http404("datetime in wrong format (dt=%Y-%m-%d_%H.%M.%S)")

        if not self.action or not self.the_date:
            raise Http404("API call wrong-- usage: /schedules/api/?action=billboard&dt=2010-05-01_21.00.00&tpl=base.htm")

        self.the_time = self.the_date.time()

        return super(API, self).get(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        if self.tpl == "base.htm":
            response_kwargs.update({'mimetype': 'text/plain'})
        else:
            response_kwargs.update({'mimetype': 'text/xml'})
        return super(API, self).render_to_response(context, **response_kwargs)

    def get_context_data(self, **kwargs):
        c = {}
        data = {}

        desired_channels = ['kuat6','pbsworld','readytv','uachannel','vme','kuatkids','kuaz']
        #desired_channels = ['kuaz']

        services = get_list_or_404(Service, active=True, keyname__in=desired_channels)

        if self.action == "billboard":

            for service in services:

                this_service = []

                # get airs for this service
                airs = Air.objects.filter(service = service).distinct()

                # get all possible airs for both the today and tomorrow billboards, including rollover past 2400
                today_airs = airs.filter(date__range=(self.the_date, self.the_date + timedelta(days=1)))
                tomorrow_airs = airs.filter(date__range=(self.the_date + timedelta(days=1), self.the_date + timedelta(days=2)))

                #queries to get what's "on now"
                try:
                    airing_now = airs.filter(time__lte=self.the_time, date=self.the_date)
                    airing_tomorrow = airs.filter(time__lte=self.the_time, date=self.the_date + timedelta(days=1))
                except:
                    raise Http404("Can't Find What's On")

                #if there is nothing on right now, assume last thing from yesterday is still on-air
                if not airing_now:
                    airing_now = airs.filter(date=self.the_date + timedelta(days=-1)).order_by('-time')

                if not airing_tomorrow:
                    airing_tomorrow = airs.filter(date=self.the_date).order_by('-time')

                #queries to build our list of airs for the 'now'
                try:
                    today_1 = today_airs.filter(date=self.the_date, time__gte= airing_now.latest('time').time).order_by('date','time')
                    today_2 = today_airs.filter(date=self.the_date + timedelta(days=1)).order_by('date','time')
                    today = today_1 | today_2
                    today = today[:4]

                    if today[0]:
                        this_service.append({'entry':{'episode':{'season':{'series':{'name':today[0].airing.series.name}}}},'title_object':[ord(today[0].airing.series.name[i].decode('U8')) for i in range(0, len(today[0].airing.series.name))],'time_object':[ord(today[0].time.strftime("%l:%M %p").lstrip()[i].decode('U8')) for i in range(0, len(today[0].time.strftime("%l:%M %p").lstrip()))],'time_string':today[0].time.strftime("%l:%M %p").lstrip()})
                    else:
                        this_service.append({'entry':{'episode':{'season':{'series':{'name':"See website"}}}},"title_object":[ord('See website'[i].decode('U8')) for i in range(0, len('See website'))],'time_object':[ord(self.the_time.strftime("%l:%M %p").lstrip()[i].decode('U8')) for i in range(0, len(self.the_time.strftime("%l:%M %p").lstrip()))],'time_string':self.the_time.strftime("%l:%M %p").lstrip()})

                    if today[1]:
                        this_service.append({'entry':{'episode':{'season':{'series':{'name':today[1].airing.series.name}}}},'title_object':[ord(today[1].airing.series.name[i].decode('U8')) for i in range(0, len(today[1].airing.series.name))],'time_object':[ord(today[1].time.strftime("%l:%M %p").lstrip()[i].decode('U8')) for i in range(0, len(today[1].time.strftime("%l:%M %p").lstrip()))],'time_string':today[1].time.strftime("%l:%M %p").lstrip()})
                    else:
                        this_service.append({'entry':{'episode':{'season':{'series':{'name':"See website"}}}},"title_object":[ord('See website'[i].decode('U8')) for i in range(0, len('See website'))],'time_object':[ord(self.the_time.strftime("%l:%M %p").lstrip()[i].decode('U8')) for i in range(0, len(self.the_time.strftime("%l:%M %p").lstrip()))],'time_string':self.the_time.strftime("%l:%M %p").lstrip()})

                    if today[2]:
                        this_service.append({'entry':{'episode':{'season':{'series':{'name':today[2].airing.series.name}}}},'title_object':[ord(today[2].airing.series.name[i].decode('U8')) for i in range(0, len(today[2].airing.series.name))],'time_object':[ord(today[2].time.strftime("%l:%M %p").lstrip()[i].decode('U8')) for i in range(0, len(today[2].time.strftime("%l:%M %p").lstrip()))],'time_string':today[2].time.strftime("%l:%M %p").lstrip()})
                    else:
                        this_service.append({'entry':{'episode':{'season':{'series':{'name':"See website"}}}},"title_object":[ord('See website'[i].decode('U8')) for i in range(0, len('See website'))],'time_object':[ord(self.the_time.strftime("%l:%M %p").lstrip()[i].decode('U8')) for i in range(0, len(self.the_time.strftime("%l:%M %p").lstrip()))],'time_string':self.the_time.strftime("%l:%M %p").lstrip()})

                    if today[3]:
                        this_service.append({'entry':{'episode':{'season':{'series':{'name':today[3].airing.series.name}}}},'title_object':[ord(today[3].airing.series.name[i].decode('U8')) for i in range(0, len(today[3].airing.series.name))],'time_object':[ord(today[3].time.strftime("%l:%M %p").lstrip()[i].decode('U8')) for i in range(0, len(today[3].time.strftime("%l:%M %p").lstrip()))],'time_string':today[3].time.strftime("%l:%M %p").lstrip()})
                    else:
                        if len(this_service) < 4:
                            this_service.append({'filler' : "filler"})

                except Exception:

                    this_service.append({'entry':{'episode':{'season':{'series':{'name':"See website"}}}},"title_object":[ord('See website'[i].decode('U8')) for i in range(0, len('See website'))],'time_object':[ord(self.the_time.strftime("%l:%M %p").lstrip()[i].decode('U8')) for i in range(0, len(self.the_time.strftime("%l:%M %p").lstrip()))],'time_string':self.the_time.strftime("%l:%M %p").lstrip()})
                    this_service.append({'filler' : "filler"})


            #queries to build our list of airs for the 'tomorrow'
                try:
                    tomorrow_1 = tomorrow_airs.filter(date=self.the_date + timedelta(days=1), time__gte= airing_tomorrow.latest('time').time).order_by('date','time')
                    tomorrow_2 = tomorrow_airs.filter(date=self.the_date + timedelta(days=2)).order_by('date','time')
                    tomorrow = tomorrow_1 | tomorrow_2
                    tomorrow = tomorrow[:2]

                    if tomorrow[0]:
                        this_service.append({'entry':{'episode':{'season':{'series':{'name':tomorrow[0].airing.series.name}}}},'title_object':[ord(tomorrow[0].airing.series.name[i].decode('U8')) for i in range(0, len(tomorrow[0].airing.series.name))],'time_object':[ord(tomorrow[0].time.strftime("%l:%M %p").lstrip()[i].decode('U8')) for i in range(0, len(tomorrow[0].time.strftime("%l:%M %p").lstrip()))],'time_string':tomorrow[0].time.strftime("%l:%M %p").lstrip()})
                    else:
                        this_service.append({'entry':{'episode':{'season':{'series':{'name':"See website"}}}},"title_object":[ord('See website'[i].decode('U8')) for i in range(0, len('See website'))],'time_object':[ord(self.the_time.strftime("%l:%M %p").lstrip()[i].decode('U8')) for i in range(0, len(self.the_time.strftime("%l:%M %p").lstrip()))],'time_string':self.the_time.strftime("%l:%M %p").lstrip()})

                    if tomorrow[1]:
                        this_service.append({'entry':{'episode':{'season':{'series':{'name':tomorrow[1].airing.series.name}}}},'title_object':[ord(tomorrow[1].airing.series.name[i].decode('U8')) for i in range(0, len(tomorrow[1].airing.series.name))],'time_object':[ord(tomorrow[1].time.strftime("%l:%M %p").lstrip()[i].decode('U8')) for i in range(0, len(tomorrow[1].time.strftime("%l:%M %p").lstrip()))],'time_string':tomorrow[1].time.strftime("%l:%M %p").lstrip()})
                    else:
                        if len(this_service) < 2:
                            this_service.append({'filler' : "filler"})

                except Exception:

                    this_service.append({'entry':{'episode':{'season':{'series':{'name':"See website"}}}},"title_object":[ord('See website'[i].decode('U8')) for i in range(0, len('See website'))],'time_object':[ord(self.the_time.strftime("%l:%M %p").lstrip()[i].decode('U8')) for i in range(0, len(self.the_time.strftime("%l:%M %p").lstrip()))],'time_string':self.the_time.strftime("%l:%M %p").lstrip()})
                    this_service.append({'filler' : "filler"})


                #dirty hack for readytv
                if service.keyname == 'readytv':
                    data['kuatcreate'] = this_service
                else:
                    data[service.keyname] = this_service

        template_name = self.get_template_names()

        c.update({"data": data})
        return c

    def get_template_names(self):
        if self.tpl == "base.htm":
            return "schedules/api/%s" % self.tpl

        tpl_arg = self.tpl
        tpl_arg += str(randint(1,6))
        tpl_arg += '.motn'
        return "schedules/api/%s" % tpl_arg