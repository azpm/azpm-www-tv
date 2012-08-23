import os, sys, site

#activate the virtual environment	
activate_this = '/usr/local/share/environments/scampi4/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

#in order, the paths we need for this to work
project_pathing = ['/srv/vhosts/tv/']

for path in project_pathing:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'project.settings'

from django.core.handlers.wsgi import WSGIHandler

application = WSGIHandler()