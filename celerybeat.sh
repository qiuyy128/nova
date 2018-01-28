#!/bin/bash
nohup python manage.py celerybeat > celerybeat.log 2>&1 &
