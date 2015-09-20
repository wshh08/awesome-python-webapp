#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
logging.basicConfig(level=logging.INFO)
import time
import datetime
from transwarp import db
from transwarp.web import WSGIApplication, Jinja2TemplateEngine

from config import configs


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

db.create_engine(**configs.db)

wsgi = WSGIApplication(os.path.dirname(os.path.abspath(__file__)))

template_engine = Jinja2TemplateEngine(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
template_engine.add_filter('datetime', datetime_filter)
wsgi.template_engine = template_engine


import urls
wsgi.add_module(urls)


if __name__ == '__main__':
    wsgi.run(9000)
else:
    # if use "python wsgiapp.py" to start the app, run the "wsgiref.simple_server"
    # if gunicorn is used, transform the vari "application" to gunicorn to start the service,
    # via "command     = /usr/bin/gunicorn --bind 127.0.0.1:9000 --workers 1 --worker-class gevent ##wsgiapp:application##"
    # in the configure file of gunicorn: awesome.conf in /etc/supervisor/conf.d/
    application = wsgi.get_wsgi_application()

