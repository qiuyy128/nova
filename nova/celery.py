# -*- coding:utf-8 -*-

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
import configmodule
from django.conf import settings

config_mode = configmodule.config_mode
if config_mode == 'Development':
    Configs = configmodule.DevelopmentConfig
if config_mode == 'Testing':
    Configs = configmodule.TestingConfig
if config_mode == 'Production':
    Configs = configmodule.ProductionConfig
Celery_backend = Configs.Celery_backend

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futhor.settings')

# app = Celery('learn', backend='redis', broker='redis://:password@localhost:6379/0')
app = Celery('nova', backend='%s' % Celery_backend)

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

#
app.conf.ONCE_REDIS_URL = Celery_backend
app.conf.ONCE_DEFAULT_TIMEOUT = 60 * 60


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
