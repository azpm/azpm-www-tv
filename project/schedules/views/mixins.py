from django.http import   Http404
from django.shortcuts import get_object_or_404

from libazpm.contrib.chronologia.models import Service

class ChannelMixin(object):
    channel = None
    
    def get(self, request, *args, **kwargs):
        #keyname specified in url
        if 'channel' in kwargs:
            keyname = kwargs.pop('channel')
            self.channel = get_object_or_404(Service, keyname=keyname, active=True)
        else:
            raise Http404
            
        #finally return the parent get method
        return super(ChannelMixin, self).get(request, *args, **kwargs)