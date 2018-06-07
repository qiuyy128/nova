# -*- coding:utf-8 -*-
# config_default.py

import os

# config_mode = 'Development'
config_mode = os.getenv('NOVA_ENV')


class Config(object):
    DEBUG = False
    TESTING = False
    DATABASES = 'sqlite://:memory:'
    PASSWORD = ''
    STARTUP_APP_SLEEP = 60
    SVN_CHECKOUT_NAME = 'svn'
    CONFIG_FILE_PATH = 'config_file'
    ATTACHMENT_PATH = 'attachment'
    TOMCAT_7_NAME = 'tomcat-app.7053.tar.gz'
    TOMCAT_6_NAME = 'tomcat-app.6041.tar.gz'
    TOMCAT_8_NAME = 'tomcat-app.8052.tar.gz'
    JDK_7_NAME = 'jdk1.7.0_80.tar.gz'
    JDK_6_NAME = 'jdk1.6.0_45.tar.gz'
    JDK_8_NAME = 'jdk1.8.0_77.tar.gz'
    JDK_7_BASENAME = 'jdk1.7.0_80'
    JDK_6_BASENAME = 'jdk1.6.0_45'
    JDK_8_BASENAME = 'jdk1.8.0_77'
    NODE_NAME = 'node.tar.gz'
    FDP_RECEIVE_NAME = 'fdp-receiver.tar.gz'
    FDP_RECEIVE_BASENAME = 'fdp-receiver'
    BROKER_TRANSPORT = 'redis'
    NODE_APP_NUMBER = 2
    NODE_ENV = 'test'
    JVM_MEMSize = 500
    JVM_XmnSize = ''
    PermSize = 64
    NODE_SOURCE_STAGING_SERVER = '10.47.209.203'
    SQL_LOGS = 'sql_log'
    ENDPOINT = 'http://oss-cn-beijing.aliyuncs.com'
    LOG_FILE_NAME = 'django.log'
    HTTP_PROXY = '10.126.3.112:3128'
    ENABLE_PROXY = False


class DevelopmentConfig(Config):
    DEBUG = True
    PASSWORD = ''
    BROKER_URL = 'redis://10.126.3.13:6379/0'
    ALLOWED_HOSTS = ['10.0.7.168', '127.0.0.1']
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'dev',
            'USER': 'dev',
            'PASSWORD': 'dev',
            'HOST': '10.126.3.13',
            'PORT': '3306',
        }
    }
    BROKER_URL = 'redis://10.126.3.13:6379/0'
    CELERY_RESULT_BACKEND = 'redis://10.126.3.13:6379/2'
    # celery.py
    Celery_backend = 'redis://10.126.3.13:6379/2'
    # tasks.py
    svn_username = ''
    svn_password = ''
    NODE_SOURCE_SERVER = '10.126.3.19'
    ssh_key_password = 'password'
    # views.py
    GATEONE_SERVER = 'https://10.126.3.13:443'
    GATEONE_API_KEY = "GATEONE_API_KEY"
    GATEONE_SECRET = "GATEONE_SECRET"


class TestingConfig(Config):
    DEBUG = True
    PASSWORD = ''
    BROKER_URL = 'redis://10.126.3.13:6379/0'
    ALLOWED_HOSTS = ['10.126.3.13']
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'dev',
            'USER': 'dev',
            'PASSWORD': 'dev',
            'HOST': '10.126.3.13',
            'PORT': '3306',
        }
    }
    BROKER_URL = 'redis://10.126.3.13:6379/0'
    CELERY_RESULT_BACKEND = 'redis://10.126.3.13:6379/2'
    # celery.py
    Celery_backend = 'redis://10.126.3.13:6379/2'
    # tasks.py
    svn_username = ''
    svn_password = ''
    NODE_SOURCE_SERVER = '10.126.3.19'
    ssh_key_password = 'password'
    # views.py
    GATEONE_SERVER = 'https://10.126.3.13:443'
    GATEONE_API_KEY = "GATEONE_API_KEY"
    GATEONE_SECRET = "GATEONE_SECRET"
    # proxy
    HTTP_PROXY = '10.0.0.10:3128'
    ENABLE_PROXY = True


class ProductionConfig(Config):
    PASSWORD = ''
    NODE_APP_NUMBER = 4
    NODE_ENV = 'production'
    JVM_MEMSize = 2048
    JVM_XmnSize = '-Xmn400M'
    PermSize = 256
    ALLOWED_HOSTS = ['10.0.0.10']
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'nova',
            'USER': 'nova',
            'PASSWORD': 'password',
            'HOST': '10.0.0.10',
            'PORT': '3306',
        }
    }
    BROKER_URL = 'redis://:password@10.0.0.10:6379/0'
    CELERY_RESULT_BACKEND = 'redis://:password@10.0.0.10:6379/2'

    # celery.py
    Celery_backend = 'redis://:password@10.0.0.10:6379/2'
    # tasks.py
    svn_username = ''
    svn_password = ''
    NODE_SOURCE_SERVER = '10.0.0.10'
    ssh_key_password = 'private_key'
    # views.py
    GATEONE_SERVER = 'https://domain:443'
    GATEONE_API_KEY = ""
    GATEONE_SECRET = ""

