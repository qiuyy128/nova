# -*- coding:utf-8 -*-
from __future__ import absolute_import

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render

# Create your views here.
from nova.models import Asset, AssetGroup, App, AppHost, AppGroup, Task, AppConfig, Sql, Database, UploadFile, \
    OssBucketApp, HttpStep, HttpTest, History, Config, ServiceStep, ServiceTest, OperationLog
from django.contrib.auth.models import User, Group, Permission
from .forms import UserForm, AssetForm, UploadFileForm, AppConfigForm

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, InvalidPage, PageNotAnInteger
from django.db.models import Avg, Max, Min, Count
from django.core import serializers
from django.core.urlresolvers import reverse
import logging

import time, hmac, hashlib, json, subprocess, os
import datetime
from django.utils import timezone
from celery.result import AsyncResult
import urllib
from django.db.models import Q
import re
import oss2
from script.conn_mysql import Mysql
from script.conn_mssql import MsSQL
from script.conn_mongodb import Mongodb
from django.contrib.auth.hashers import make_password, check_password

from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
import base64
import urllib2, json
from bson import json_util
import string
import decimal
from .run_script import RunCmd
from django.http import StreamingHttpResponse
from django.http import FileResponse
import zipfile
import shutil
# from ansible.runner import Runner

import sys
import configmodule
reload(sys)
sys.setdefaultencoding('utf-8')

base_path = os.path.dirname(os.path.abspath(__name__))

config_mode = configmodule.config_mode

# Get an instance of a logger
logger = logging.getLogger("django")

logger.info(config_mode)
if config_mode == 'Development':
    Configs = configmodule.DevelopmentConfig
if config_mode == 'Testing':
    Configs = configmodule.TestingConfig
if config_mode == 'Production':
    Configs = configmodule.ProductionConfig

GATEONE_SERVER = Configs.GATEONE_SERVER
GATEONE_API_KEY = Configs.GATEONE_API_KEY
GATEONE_SECRET = Configs.GATEONE_SECRET
CONFIG_FILE_PATH = Configs.CONFIG_FILE_PATH
SQL_LOGS = Configs.SQL_LOGS
ENDPOINT = Configs.ENDPOINT

config_files_path = os.path.join(base_path, '%s') % CONFIG_FILE_PATH
sql_logs_path = os.path.join(base_path, '%s') % SQL_LOGS
rsa_pub = os.path.join(base_path, 'script', 'rsa.pub')
rsa_key = os.path.join(base_path, 'script', 'rsa.key')

# 是否使用代理
enable_proxy = Configs.ENABLE_PROXY
http_proxy = {"http": Configs.HTTP_PROXY}
https_proxy = {"https": Configs.HTTP_PROXY}


@login_required
def index(request):
    return render(request, 'index.html')


@login_required
def home(request):
    return render(request, 'base.html')


def help(request):
    return render(request, 'help.html')


@csrf_exempt
def Login(request):
    if request.method == 'POST':
        forms = UserForm(request.POST)
        next_url = request.POST.get('next')
        logger.info('login next url is:%s' % next_url)
        if forms.is_valid():
            form_data = forms.clean()
            user = authenticate(username=form_data['username'], password=form_data['password'])
            if user is not None and user.is_active:
                login(request, user)
                logger.info(u'用户名%s登陆成功.' % user)
                return HttpResponseRedirect(next_url)
            else:
                logger.info(u'用户名%s或密码%s错误' % (form_data['username'], form_data['password']))
                return HttpResponseRedirect(reverse('login'))
    else:
        form = UserForm()
        full_url = request.get_full_path()
        if full_url.find('?next=') != -1:
            next = full_url.split('?next=')[1].replace('%3F', '?').replace('%3D', '=').replace('%26', '&')
            logger.info(next)
        else:
            next = '/nova/'
        return render(request, 'login.html', {'form': form, 'next': next})


@login_required
def Logout(request):
    logger.info(u'用户名%s登出.' % request.user.username)
    logout(request)
    return HttpResponseRedirect(reverse('index'))


def get_object(model, **kwargs):
    """
    use this function for query
    使用改封装函数查询数据库
    """
    for value in kwargs.values():
        if not value:
            return None
    the_object = model.objects.filter(**kwargs)
    if len(the_object) == 1:
        the_object = the_object[0]
    else:
        the_object = None
    return the_object


def _dec_(data=''):
    with open(rsa_key, 'r') as f:
        private_key = f.read()
        rsa_key_obj = RSA.importKey(private_key)
        cipher_obj = Cipher_PKCS1_v1_5.new(rsa_key_obj)
        random_generator = Random.new().read
        plain_text = cipher_obj.decrypt(base64.b64decode(data), random_generator)
        return plain_text


@csrf_exempt
def get_user_group(request):
    username = request.user.username
    user_groups = get_object(User, username=username).groups.all()
    return user_groups


@login_required()
@csrf_exempt
def get_user_asset(request):
    username = request.user.username
    user_groups = get_object(User, username=username).groups.all()
    assets_all = Asset.objects.none()
    for ug in user_groups:
        # 获取asset_group名称
        asset_group_name = Group.objects.get(name=ug.name).assetgroup_set.all()
        try:
            assets_all = assets_all | AssetGroup.objects.get(name=asset_group_name.values('name')).asset_set.all()
        except AssetGroup.DoesNotExist:
            pass
            # logger.info("user_group %s has not asset_group!" % ug)
    # 去重
    assets = assets_all.distinct()
    return assets


@login_required
def get_user_asset_id(request):
    user_assets = get_user_asset(request)
    asset_id = []
    for aid in user_assets:
        asset_id.append(aid.id)
    return asset_id


@login_required()
# @permission_required('nova.access_asset')
def console(request):
    # 获取访问请求用户的所有权限
    perms = User.get_all_permissions(request.user)
    assets_count = get_user_asset(request).count()
    apps_count = get_user_apps(request).count()
    context = {'perms': perms, 'assets_count': assets_count, 'apps_count': apps_count}
    logger.info(context)
    return render(request, 'console.html', context)


@login_required()
@permission_required('nova.access_asset', raise_exception=True)
def asset_group(request):
    username = request.user.username
    asset_groups = AssetGroup.objects.all()
    context = {'username': username, 'asset_groups': asset_groups}
    return render(request, 'asset_group.html', context)


@login_required()
@permission_required('nova.access_asset', raise_exception=True)
def asset(request):
    username = request.user.username
    assets = get_user_asset(request)
    context = {'username': username, 'assets': assets}
    return render(request, 'asset.html', context)


@login_required()
def asset_add(request):
    if request.method == 'POST':
        asset_group_form = AssetForm(request.POST)
        if asset_group_form.is_valid():
            try:
                asset_group_form.save()
                msg = "添加成功"
            except Exception as e:
                logger.info(e)
                msg = "添加失败"
            logger.info(msg)
            return HttpResponseRedirect(reverse('asset'))
        else:
            data = {'msg': '添加失败！'}
            return render(request, 'message.html', data)
    else:
        form = AssetForm()
        return render(request, 'asset_add.html', {'form': form})


@login_required()
def asset_change(request, asset_id):
    asset = Asset.objects.get(id=asset_id)
    form = AssetForm(instance=asset)
    if request.method == 'POST':
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            form.save()
            msg = "修改成功"
            assets = get_user_asset(request)
            context = {'msg': msg, 'assets': assets}
            return HttpResponseRedirect(reverse('asset'))
    else:
        msg = "修改失败"
        return render(request, 'asset_change.html', {'asset_id': asset_id, 'form': form})


@login_required()
@csrf_exempt
def asset_delete(request, asset_id):
    if request.user.username == 'admin':
        try:
            asset = Asset.objects.get(id=asset_id)
            if asset:
                if request.is_ajax():
                    asset.delete()
                    msg = "删除成功"
                    data = json.dumps({'rtn': "00", 'msg': '服务器' + asset_id + '成功删除!'})
                    return HttpResponse(data)
                else:
                    msg = "删除失败"
                    data = json.dumps({'rtn': "97", 'msg': '服务器' + asset_id + '删除失败!'})
                    return HttpResponse(data)
        except Asset.DoesNotExist as e:
            logger.info(e)
            data = json.dumps({'rtn': "98", 'msg': "服务器未添加"})
            return HttpResponse(data)
    else:
        # data = json.dumps({'rtn': "99", 'msg': "请联系管理员操作"})
        data = {'msg': '请联系管理员操作！'}
        return render(request, 'message.html', data)


@login_required
def get_free_asset(request):
    configs = request.GET['type']
    asset_ip = request.GET.get('asset_ip')
    # asset = get_object_or_404(Asset, configs=configs)
    if asset_ip:
        assets = Asset.objects.filter(configs__icontains=configs, ip__icontains=asset_ip)
    else:
        assets = Asset.objects.filter(configs__icontains=configs)
    try:
        data = serializers.serialize('json', assets, fields='ip')
    except Exception as e:
        print e
    # logger.info(data)
    return HttpResponse(data, content_type='application/json')


@login_required
def get_max_port(request):
    type = request.GET['type']
    if type == 'nodejs':
        app_type = 'fdp'
    if type == 'tomcat':
        app_type = type
    app_host = AppHost.objects.filter(name__icontains=app_type).aggregate(max_port=Max('port'))
    app_host['max_port'] = int(app_host['max_port']) + 1
    return HttpResponse(json.dumps(app_host), content_type='application/json')


@login_required
def get_asset(request):
    env = request.GET['env']
    asset_ip = request.GET.get('asset_ip')
    # asset = get_object_or_404(Asset, configs=configs)
    if asset_ip:
        assets = Asset.objects.filter(env__icontains=env, ip__icontains=asset_ip)
    else:
        assets = Asset.objects.filter(env__icontains=env)
    try:
        data = serializers.serialize('json', assets, fields='ip')
    except Exception as e:
        print e
    # logger.info(data)
    return HttpResponse(data, content_type='application/json')


@csrf_exempt
@login_required
def app_deploy(request):
    logger.info("User is:%s;Request is:deploy app!" % request.user.username)
    if User.has_perm(request.user, 'nova.access_app'):
        if request.method == 'POST':
            app_type = json.loads(request.body)['app_type']
            app_env = json.loads(request.body)['app_env']
            tomcat_version = json.loads(request.body)['tomcat_version']
            app_name = json.loads(request.body)['app_name']
            svn_url = json.loads(request.body)['svn_url']
            app_port = json.loads(request.body)['app_port']
            deploy_path = json.loads(request.body)['deploy_path']
            app_assets = json.loads(request.body)['app_assets']
            logger.info(app_assets)
            app_asset = ''
            for i in app_assets:
                app_asset = app_asset + i + '&'
            app_asset = app_asset[:-1]
            logger.info(u"开始部署:" + app_name + " on %s:%s" % (app_asset, deploy_path))
            from .tasks import do_deploy_app
            result = do_deploy_app.delay(app_name, app_env, tomcat_version, app_port, deploy_path, svn_url, app_assets)
            logger.info('Task:%s' % result)
            logger.info('Task Status:%s' % result.status)
            task_name = u'部署%s:' % app_env + app_name
            task_detail = u'部署app_name:' + app_name + ',server:' + app_asset + ',port:' + app_port + ',app_env:' + app_env + ',deploy_path:' + deploy_path
            Task.objects.create(task_id=result.task_id, name=task_name, status=result.status,
                                # start_time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                start_time=timezone.now(), result=result.result, svn_url=svn_url, detail=task_detail,
                                execute_user=request.user.username)
            msg = u'服务' + app_name + u'已在后台进行部署，请稍后......地址为 http://' + app_asset + ':' + app_port
            data = {'ret': '00', 'msg': msg}
            # return HttpResponse(json.dumps(data, encoding='utf-8', ensure_ascii=False))
            return HttpResponse(json.dumps(data))

        if request.method == 'GET':
            app_host = AppHost.objects.aggregate(max_port=Max('port'))
            app_host['max_port'] = int(app_host['max_port']) + 1
            assets = Asset.objects.all().values('ip')
            return render(request, 'app_deploy.html', locals())
    else:
        data = {'rtn': '99', 'msg': '没有操作权限，请联系管理员!'}
    # return HttpResponse(json.dumps(data))
    return render(request, 'deny.html')


@login_required()
def get_task_status(request):
    res = request.GET
    if 'task_id' in res:
        task_id = request.GET['task_id']
        task_status = AsyncResult(id=task_id).status
        data = {'task_id': task_id, 'task_status': task_status}
        return HttpResponse(json.dumps(data))


@login_required
def task_list(request):
    res = request.GET
    if 'page' in res:
        page = int(request.GET.get('page'))
    else:
        page = 1
    if request.GET.get('limit'):
        limit = int(request.GET.get('limit'))
    else:
        limit = 10
    if 'task_id' in res:
        task_id = request.GET['task_id']
        tasks = Task.objects.filter(task_id=task_id)
        status = AsyncResult(id=task_id).status
        result = AsyncResult(id=task_id).result
        if tasks.values('status') != status:
            tasks.update(status=status, result=result)
    else:
        tasks = Task.objects.order_by('-start_time').all()
    # 实例化一个分页对象
    paginator = Paginator(tasks, limit)
    all_counts = paginator.count
    try:
        tasks = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        tasks = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        tasks = paginator.page(paginator.num_pages)

    # 根据参数配置导航显示范围
    temp_range = paginator.page_range
    after_range_num = 5
    before_range_num = 4
    # 如果页面很小
    if (page - before_range_num) <= 0:
        # 如果总页面比after_range_num大，那么显示到after_range_num
        if temp_range[-1] > after_range_num:
            page_range = xrange(1, after_range_num + 1)
        # 否则显示当前页
        else:
            page_range = xrange(1, temp_range[-1] + 1)
    # 如果页面比较大
    elif (page + after_range_num) > temp_range[-1]:
        # 显示到最大页
        page_range = xrange(page - before_range_num, temp_range[-1] + 1)
    # 否则在before_range_num和after_range_num之间显示
    else:
        page_range = xrange(page - before_range_num + 1, page + after_range_num)
    limit_option = [10, 20, 50, 100]
    data = {'tasks': tasks, 'all_count': all_counts, 'all_pages': paginator.num_pages,
            'page_range': page_range, 'limit': limit, 'limit_option': limit_option}
    return render(request, 'task.html', context=data)


@login_required()
def get_user_apps(request):
    username = request.user.username
    user_groups = get_object(User, username=username).groups.all()
    apps_all = App.objects.none()
    for ug in user_groups:
        # 获取app_group名称
        app_group_name = Group.objects.get(name=ug.name).appgroup_set.all()
        # 取app
        try:
            apps_all = apps_all | AppGroup.objects.get(name=app_group_name.values('name')).app_set.all()
        except AppGroup.DoesNotExist:
            pass
            # logger.info("user_group %s has not app_group!" % ug)
    # 去重
    apps = apps_all.distinct()
    return apps


@login_required
def get_user_apps_id(request):
    user_apps = get_user_apps(request)
    app_id = []
    for aid in user_apps:
        app_id.append(aid.id)
    return app_id


@csrf_exempt
@login_required
@permission_required('nova.access_app', raise_exception=True)
def apps(request):
    username = request.user.username
    if request.method == 'GET':
        res = request.GET
        if 'app_name' in res:
            app_name = request.GET['app_name']
        else:
            app_name = ''
        if 'keyword' in res:
            keyword = request.GET['keyword']
        else:
            keyword = ''
        if 'page' in res:
            page = request.GET['page']
        else:
            page = 1
        if 'id' in res:
            page = request.GET.getlist('id')
    apps = App.objects.none()
    if app_name:
        for i in get_user_apps_id(request):
            apps_search = App.objects.filter(Q(name=app_name) & Q(id=i))
            apps = apps | apps_search
        if apps.count() == 0:
            return render(request, 'deny.html')
    elif keyword:
        for i in get_user_apps_id(request):
            apps_search = App.objects.filter(Q(name__contains=keyword) & Q(id=i))
            apps = apps | apps_search
        if apps.count() == 0:
            return render(request, 'deny.html')
    else:
        # 取当前用户所拥有权限的应用
        apps = get_user_apps(request)
    # # 实例化一个分页对象
    # limit = 10
    # paginator = Paginator(apps, limit)
    # try:
    #     apps = paginator.page(page)
    # except PageNotAnInteger:
    #     # If page is not an integer, deliver first page.
    #     apps = paginator.page(1)
    # except EmptyPage:
    #     # If page is out of range (e.g. 9999), deliver last page of results.
    #     apps = paginator.page(paginator.num_pages)
    data = {'apps': apps, 'app_name': app_name}
    return render(request, 'apps.html', context=data)


def exec_cmd(command):
    output = ''
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
        output = output + line
    # logger.info('execute command %s :' % command + output)
    return output


@login_required()
@csrf_exempt
def start_app(request):
    logger.info("User is:%s;Request is:start app!" % request.user.username)
    if User.has_perm(request.user, 'nova.access_app'):
        if request.body:
            app_id = json.loads(request.body)['app_id']
            app_env = json.loads(request.body)['app_env']
            logger.info('User is:%s;Request is:start app id: %s' % (request.user.username, app_id))
        else:
            data = {'rtn': '98', 'msg': u'未提交必要参数!'}
            return HttpResponse(json.dumps(data))
        logger.info('Start app %s:,env:%s' % (app_id, app_env))
        if 'product' in app_env and not User.has_perm(request.user, 'nova.operate_product'):
            data = {'rtn': '98', 'msg': '没有生产环境操作权限，请联系管理员!'}
            return HttpResponse(json.dumps(data))
        logger.info(u'启动应用：')
        logger.info(AppHost.objects.filter(id__in=app_id))
        from .tasks import do_start_app
        result = do_start_app.delay(app_id)
        logger.info(result)
        logger.info(result.status)
        app_ids = ','.join(app_id).encode('utf-8')
        app_env = ','.join(app_env).encode('utf-8')
        task_name = u'启动%s:%s' % (app_env, app_ids)
        Task.objects.create(task_id=result.task_id, name=task_name, status=result.status,
                            # start_time=timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                            start_time=timezone.now(), result=result.result, app_id=app_ids,
                            execute_user=request.user.username)
        data = {'rtn': '00', 'msg': '启动成功!'}
    else:
        data = {'rtn': '99', 'msg': '没有操作权限，请联系管理员!'}
    return HttpResponse(json.dumps(data))


@login_required()
@csrf_exempt
def stop_app(request):
    logger.info("User is:%s;Request is:stop app!" % request.user.username)
    if User.has_perm(request.user, 'nova.access_app'):
        if request.body:
            app_id = json.loads(request.body)['app_id']
            app_env = json.loads(request.body)['app_env']
            logger.info('User is:%s;Request is:stop app id: %s' % (request.user.username, app_id))
        else:
            data = {'rtn': '98', 'msg': u'未提交必要参数!'}
            return HttpResponse(json.dumps(data))
        logger.info('Stop app %s:,env:%s' % (app_id, app_env))
        if 'product' in app_env and not User.has_perm(request.user, 'nova.operate_product'):
            data = {'rtn': '98', 'msg': '没有生产环境操作权限，请联系管理员!'}
            return HttpResponse(json.dumps(data))
        logger.info(u'停止应用：')
        logger.info(AppHost.objects.filter(id__in=app_id))
        from .tasks import do_stop_app
        result = do_stop_app.delay(app_id)
        # logger.info(result, result.status)
        app_ids = ','.join(app_id).encode('utf-8')
        app_env = ','.join(app_env).encode('utf-8')
        task_name = u'停止%s:%s' % (app_env, app_ids)
        Task.objects.create(task_id=result.task_id, name=task_name, status=result.status,
                            # start_time=timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                            start_time=timezone.now(), result=result.result, app_id=app_ids,
                            execute_user=request.user.username)
        data = {'rtn': '00', 'msg': '停止成功！'}
        return HttpResponse(json.dumps(data))
    else:
        data = {'rtn': '99', 'msg': '没有操作权限，请联系管理员!'}
    return HttpResponse(json.dumps(data))


@login_required()
@csrf_exempt
def reload_app(request):
    logger.info("User is:%s;Request is:reload app!" % request.user.username)
    if User.has_perm(request.user, 'nova.access_app'):
        if request.body:
            app_id = json.loads(request.body)['app_id']
            app_env = json.loads(request.body)['app_env']
            print 'app_env is:', app_env
            logger.info('User is:%s;Request is:reload app id: %s' % (request.user.username, app_id))
        else:
            data = {'rtn': '98', 'msg': u'未提交必要参数!'}
            return HttpResponse(json.dumps(data))
        logger.info('Reload app %s:,env:%s' % (app_id, app_env))
        if 'product' in app_env and not User.has_perm(request.user, 'nova.operate_product'):
            data = {'rtn': '98', 'msg': '没有生产环境操作权限，请联系管理员!'}
            return HttpResponse(json.dumps(data))
        logger.info(u'重启应用：')
        logger.info(AppHost.objects.filter(id__in=app_id))
        app_ids = ','.join(app_id).encode('utf-8')
        app_env = ','.join(app_env).encode('utf-8')
        from .tasks import do_reload_app
        result = do_reload_app.delay(app_id)
        task_name = u'重启%s:%s' % (app_env, app_ids)
        Task.objects.create(task_id=result.task_id, name=task_name, status=result.status,
                            start_time=timezone.now(), result=result.result, app_id=app_ids,
                            execute_user=request.user.username)
        data = {'rtn': '00', 'msg': '重启成功！'}
    else:
        data = {'rtn': '99', 'msg': '没有操作权限，请联系管理员!'}
    return HttpResponse(json.dumps(data))


@login_required()
@csrf_exempt
def rollback_app(request):
    logger.info("User is:%s;Request is:rollback app!" % request.user.username)
    if User.has_perm(request.user, 'nova.access_app'):
        logger.info(request.body)
        if request.body:
            app_name = json.loads(request.body)['app_name']
            app_env = json.loads(request.body)['app_env']
            app_id = json.loads(request.body)['app_id']
            logger.info(app_name)
        else:
            data = {'rtn': '98', 'msg': u'未提交必要参数!'}
            return HttpResponse(json.dumps(data))
        logger.info('User is:%s;Rollback app %s:,env:%s' % (request.user.username, app_name, app_env))
        if 'product' in app_env and not User.has_perm(request.user, 'nova.operate_product'):
            data = {'rtn': '98', 'msg': '没有生产环境操作权限，请联系管理员!'}
            return HttpResponse(json.dumps(data))
        logger.info(u'回滚应用：')
        logger.info(AppHost.objects.filter(name=app_name, env=app_env))
        app_ids = ','.join(app_id).encode('utf-8')
        from .tasks import do_rollback_app
        result = do_rollback_app.delay(app_name, app_env)
        task_name = u'回滚%s:%s' % (app_env, app_ids)
        Task.objects.create(task_id=result.task_id, name=task_name, status=result.status,
                            start_time=timezone.now(), result=result.result, app_id=app_ids,
                            execute_user=request.user.username)
        data = {'rtn': '00', 'msg': '正在后台进行回滚操作！'}
    else:
        data = {'rtn': '99', 'msg': '没有操作权限，请联系管理员!'}
    return HttpResponse(json.dumps(data))


@login_required()
@csrf_exempt
def update_app(request):
    # POST 请求
    logger.info("User is:%s;Request is:update app!" % request.user.username)
    if User.has_perm(request.user, 'nova.access_app'):
        if request.body:
            app_name = json.loads(request.body)['app_name']
            app_id = json.loads(request.body)['app_id']
            app_env = json.loads(request.body)['app_env']
            logger.info('User is:%s;Request upload app: %s,env: %s' % (request.user.username, app_name, app_env))
        else:
            data = {'rtn': '98', 'msg': u'未提交必要参数!'}
            return HttpResponse(json.dumps(data))
        logger.info('Upload app %s:,env:%s' % (app_name, app_env))
        if app_env == 'product' and not User.has_perm(request.user, 'nova.operate_product'):
            data = {'rtn': '98', 'msg': '没有生产环境操作权限，请联系管理员!'}
            return HttpResponse(json.dumps(data))
        logger.info(u'更新应用：')
        logger.info(AppHost.objects.filter(name=app_name, env=app_env))
        app_ids = ','.join(app_id).encode('utf-8')
        from .tasks import do_update_app
        result = do_update_app.delay(app_name, app_env)
        task_name = u'更新%s:' % app_env + app_name
        Task.objects.create(task_id=result.task_id, name=task_name, status=result.status,
                            start_time=timezone.now(), result=result.result, app_id=app_ids,
                            execute_user=request.user.username)
        data = {'rtn': '00', 'msg': '更新成功！'}
    else:
        # logger.info(u'没有操作权限，请联系管理员!')
        data = {'rtn': '99', 'msg': '没有操作权限，请联系管理员!'}
    return HttpResponse(json.dumps(data))


@csrf_exempt
@login_required
@permission_required('nova.access_file', raise_exception=True)
def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            file_name = request.POST.get('title') + '.' + f.name.split('.')[-1]
            app = request.POST.get('app')
            env = request.POST.get('env')
            fjlx = request.POST.get('fjlx')
            upload_path = os.path.join(base_path, 'upload')
            # 修改文件名
            file_path = os.path.join(upload_path, file_name)
            with open(file_path, 'wb+') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)
                destination.close()
            UploadFile.objects.create(file_name=file_name, file_type=fjlx, file_path=file_path, env=env, app_name=app,
                                      upload_time=timezone.now(), result='待上传至OSS')
            data = {'msg': '上传成功！'}
            return render(request, 'message.html', data)
    else:
        form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})


@login_required()
def config_file_add(request):
    if request.method == 'POST':
        config_file_form = AppConfigForm(request.POST)
        if config_file_form.is_valid():
            form_data = config_file_form.clean()
            env = form_data['env']
            app_name = form_data['name']
            svn_url = form_data['svn_url']
            if app_name.find('tomcat-') == 0:
                config_file_path = os.path.join(config_files_path, env, app_name.split('tomcat-')[-1],
                                                urllib.url2pathname(svn_url))
            if app_name.find('fdp_') == 0:
                config_file_path = os.path.join(config_files_path, env, app_name, urllib.url2pathname(svn_url))
            config_file_form.save()
            # 自动在服务器上创建文件夹
            logger.info(u'自动在服务器上创建应用配置文件路径:%s' % config_file_path)
            if not os.path.exists(config_file_path):
                os.makedirs(config_file_path)
            msg = u"添加应用配置文件路径成功"
            logger.info(msg)
            return HttpResponseRedirect(reverse('config_file'))
        else:
            data = {'msg': '添加应用配置文件路径失败！'}
            return render(request, 'message.html', data)
    else:
        form = AppConfigForm()
        return render(request, 'config_file_add.html', {'form': form})


@login_required
def config_file(request):
    current_url = request.get_full_path()
    res = request.GET
    if 'app_name' in res and 'env' in res:
        app_name = request.GET.get('app_name')
        env = request.GET.get('env')
        try:
            app_configs = AppConfig.objects.filter(name=app_name, env=env)
        except AppConfig.DoesNotExist:
            data = json.dumps({'rtn': "99", 'msg': "未查询到配置文件!"})
            return HttpResponse(data)
    else:
        # app_configs = AppConfig.objects.order_by('id').all()
        app_configs = AppConfig.objects.none()
        for i in get_user_apps_id(request):
            app_config = AppConfig.objects.filter(name=App.objects.get(id=i).name, env=App.objects.get(id=i).env)
            app_configs = app_configs | app_config
        if app_configs.count() == 0:
            return render(request, 'deny.html')
    # 改为从数据库查询
    app_config_list = []
    for app_config in app_configs:
        files = app_config.files.split(',')
        app_config_dic = {'name': app_config.name,
                          'env': app_config.env,
                          'svn_url': app_config.svn_url,
                          'files': files
                          }
        app_config_list.append(app_config_dic)
    # logger.info(app_config_list)
    data = {'app_config_list': app_config_list, 'current_url': current_url}
    return render(request, 'config_file.html', context=data)


@login_required
@permission_required('nova.access_file', raise_exception=True)
def config_file_editor(request, app_name, env, file_path, file_name):
    logger.info('User is:%s; Request env is:%s' % (request.user.username, env.upper()))
    if 'product' == env and not User.has_perm(request.user, 'nova.operate_product'):
        return render(request, 'deny.html')
    else:
        file_name = file_name.encode('utf-8')
        if app_name.find('tomcat-') == 0:
            app_config_files_path = os.path.join(config_files_path, env, '%s') % app_name.split('tomcat-')[-1]
        if app_name.find('fdp_') == 0:
            app_config_files_path = os.path.join(config_files_path, env, '%s') % app_name
        if file_name == 'adp-ieds.jar':
            # data = {'msg': '该配置为jar包，暂无法打开，请返回 ！'}
            # return render(request, 'message.html', data)
            # 提供adp-ieds.jar配置文件查看功能
            file_name = 'spring-config-ieds.xml'
        app_config_file = os.path.join(app_config_files_path, urllib.url2pathname(file_path), file_name)
        logger.info("Edit app_config_file:%s" % app_config_file)
        if (file_name == 'config-oss.properties' or file_name == 'config-mysql.properties'
            or file_name == 'quartz.properties' or file_name == 'config-sqlserver.properties'
            or file_name == 'config-ocr.properties' or file_name == 'config-sms.properties') \
                and env == 'product' and not User.has_perm(request.user, 'nova.access_secret_file'):
            data = {'msg': '没有权限查看涉密配置文件，请联系管理员查看！'}
            return render(request, 'message.html', data)
        else:
            try:
                fo = open(app_config_file, "rb")
                data = {'file': app_config_file, 'env': env, 'file_content': fo.read()}
            except IOError:
                msg = '该配置文件%s在服务器上不存在，请先在服务器上配置！' % file_name
                data = {'msg': msg}
                return render(request, 'message.html', data)
        return render(request, 'config_file_editor.html', data)


@csrf_exempt
@login_required()
def save_config_file(request):
    if request.method == 'POST':
        if User.has_perm(request.user, 'nova.access_app'):
            filename = json.loads(request.body)['filename']
            orig_content = json.loads(request.body)['orig_content']
            content = json.loads(request.body)['content']
            env = json.loads(request.body)['env']
            filename_bak = filename + '.bak'
            if 'product' == env and not User.has_perm(request.user, 'nova.operate_product'):
                data = {'rtn': '98', 'msg': '没有生产环境修改权限，请联系管理员!'}
                return HttpResponse(json.dumps(data))
            log_info = u'修改' + env + ':' + filename
            try:
                # 备份
                with open(filename_bak, 'wb') as f:
                    f.write(orig_content)
                # 保存
                with open(filename, 'wb') as f:
                    f.write(content)
                rtn = '00'
                msg = u'保存成功'
            except Exception as e:
                rtn = '99'
                msg = str(e)
                logger.info(e)
            data = {'rtn': rtn, 'msg': msg}
            OperationLog.objects.create(username=request.user.username, log_info=log_info, result=msg,
                                        operation_time=timezone.now())
        else:
            data = {'rtn': '98', 'msg': u'无权限执行，请联系管理员！'}
        return HttpResponse(json.dumps(data))


@login_required
def file_editor(request):
    return render(request, 'file_editor.html')


@login_required
def deny(request):
    return render(request, 'deny.html')


@login_required
def message(request):
    return render(request, 'message.html', {'message': message})


@login_required
def get_database(request):
    env = request.GET['env']
    db_name = request.GET.get('db_name')
    # asset = get_object_or_404(Asset, configs=configs)
    if db_name:
        databases = Database.objects.filter(env__icontains=env, db_name__icontains=db_name)
    else:
        databases = Database.objects.filter(env__icontains=env)
    try:
        data = serializers.serialize('json', databases, fields=('comment', 'db_name'))
    except Exception as e:
        logger.info(e)
    return HttpResponse(data, content_type='application/json')


@csrf_exempt
@login_required
@permission_required('nova.access_database', raise_exception=True)
def sql_submit(request):
    # POST 请求
    logger.info('User is:%s;Request is: submit sql.' % request.user.username)
    if User.has_perm(request.user, 'nova.access_database'):
        if request.method == 'POST':
            database_env = json.loads(request.body)['database_env']
            sql = json.loads(request.body)['sql']
            database_name = json.loads(request.body)['database_name']
            database_name = ','.join(database_name).encode('utf-8')
            logger.info("开始提交执行sql:%s on %s of %s" % (sql, database_name, database_env))
            Sql.objects.create(db_name=database_name, env=database_env, sql=sql,
                               start_time=timezone.now(), result=u'已提交',
                               submit_user=request.user.username)
            msg = u'环境:%s,数据库:%s,sql:%s' % (database_env, database_name, sql)
            data = {'ret': '00', 'msg': msg}
            # return HttpResponseRedirect(reverse('sql_list'))
            return HttpResponse(json.dumps(data))

        if request.method == 'GET':
            return render(request, 'sql_submit.html')
    else:
        data = {'rtn': '99', 'msg': '没有操作权限，请联系管理员!'}
        return render(request, 'deny.html')


@login_required
@permission_required('nova.access_database', raise_exception=True)
def sql_list(request):
    res = request.GET
    if 'page' in res:
        page = int(request.GET.get('page'))
    else:
        page = 1
    if request.GET.get('limit'):
        limit = int(request.GET.get('limit'))
    else:
        limit = 10
    # sql = Sql.objects.none()
    if 'sql_id' in res:
        sql_id = request.GET.get('sql_id')
        sql_lists = Sql.objects.filter(id=sql_id)
    else:
        sql_lists = Sql.objects.order_by('-start_time').all()
    # 实例化一个分页对象
    paginator = Paginator(sql_lists, limit)
    all_counts = paginator.count
    try:
        sql_commands = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        sql_commands = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        sql_commands = paginator.page(paginator.num_pages)

    # 根据参数配置导航显示范围
    temp_range = paginator.page_range
    after_range_num = 5
    before_range_num = 4
    # 如果页面很小
    if (page - before_range_num) <= 0:
        # 如果总页面比after_range_num大，那么显示到after_range_num
        if temp_range[-1] > after_range_num:
            page_range = xrange(1, after_range_num + 1)
        # 否则显示当前页
        else:
            page_range = xrange(1, temp_range[-1] + 1)
    # 如果页面比较大
    elif (page + after_range_num) > temp_range[-1]:
        # 显示到最大页
        page_range = xrange(page - before_range_num, temp_range[-1] + 1)
    # 否则在before_range_num和after_range_num之间显示
    else:
        page_range = xrange(page - before_range_num + 1, page + after_range_num)

    limit_option = [10, 20, 50, 100]
    data = {'sql_commands': sql_commands, 'all_count': all_counts, 'all_pages': paginator.num_pages,
            'page_range': page_range, 'limit': limit, 'limit_option': limit_option}
    return render(request, 'sql_list.html', context=data)


@csrf_exempt
@login_required
@permission_required('nova.access_database', raise_exception=True)
def sql_exec(request):
    logger.info('User is:%s;Request is: exec sql.' % request.user.username)
    # 判断用户是否有执行SQL权限
    if User.has_perm(request.user, 'nova.exec_sql'):
        if request.body:
            db_name = json.loads(request.body)['db_name']
            db_env = json.loads(request.body)['db_env']
            sql_id = json.loads(request.body)['sql_id']
        else:
            data = {'rtn': '98', 'msg': u'未提交必要参数!'}
            return HttpResponse(json.dumps(data))
        if db_name == 'ksbm' and not User.has_perm(request.user, 'nova.exec_tax_agent_sql'):
            data = {'rtn': '98', 'msg': '没有考试报名数据库权限，请联系管理员!'}
            return HttpResponse(json.dumps(data))
        if db_env == 'product' and not User.has_perm(request.user, 'nova.operate_product'):
            data = {'rtn': '98', 'msg': '没有生产数据库权限，请联系管理员!'}
            return HttpResponse(json.dumps(data))
        try:
            db_info = Database.objects.get(db_name=db_name, env=db_env)
        except Database.DoesNotExist:
            data = {'rtn': '99', 'msg': u'未找到该数据库配置！'}
        logger.info(db_info)
        # 取SQL语句
        sql_commands = Sql.objects.get(id=sql_id).sql
        logger.info('sql_commands is:%s' % sql_commands)
        # 连接数据库
        try:
            if db_info.type == 'sqlserver':
                conn = MsSQL(host=db_info.ip, port=db_info.port, db=db_info.db_name, user=db_info.username,
                             password=db_info.password)
            if db_info.type == 'mysql':
                conn = Mysql(host=db_info.ip, port=int(db_info.port), db=db_info.db_name, user=db_info.username,
                             password=db_info.password, charset="utf8")
        except Exception as e:
            data = {'rtn': '99', 'msg': '连接数据库错误:' + str(e)}
            return HttpResponse(json.dumps(data))
        # 分号分割预处理SQL
        logger.info(u'分号分割sql为:')
        logger.info(sql_commands.split(';'))
        # 处理一次提交多条SQL
        sql_recovery = ""
        for sql_command in sql_commands.split(';'):
            # logger.info(u'原sql为:%s' % repr(sql_command))
            if re.findall(r'-- (.+?)\n', sql_command, re.S):
                sql_command = re.sub(r'-- (.+?)\n', '', sql_command, re.S)
                # logger.info(u'sql去掉注释:%s' % repr(sql_command))
            # 去掉'\r\n'
            sql_command = sql_command.strip()
            # logger.info(u'sql去掉回车换行:%s' % repr(sql_command))
            if sql_command != '' and sql_command != '\n' and sql_command != '\r\n':
                logger.info(u'sql处理并非空、回车、换行:%s' % sql_command)
                # 不能包含UNION非法字符
                if len(re.findall(r'( |\n)(?i)union( |\n)', sql_command, re.S)) > 0:
                    logger.info(u'该SQL包含UNION关键字.')
                    data = {'rtn': '98', 'msg': u'该SQL有包含UNION非法字符，无法执行，请联系管理员!'}
                    return HttpResponse(json.dumps(data))
                # 新增操作不限制
                if len(re.findall(r'(| |\n|\r\n)(?i)insert( |\n|\r\n)', sql_command, re.S)) > 0:
                    logger.info(u'该SQL为INSERT语句.')
                    sql_recovery_tmp = "-- 该SQL为原SQL,不是回滚SQL,请注意！\r\n%s" % sql_command
                    sql_recovery = sql_recovery + sql_recovery_tmp + ";\n"
                elif len(re.findall(r'( |\n|\r\n)(?i)where( |\n|\r\n)', sql_command, re.S)) == 0:
                    logger.info(u'该SQL存在未包含WHERE的过滤条件!')
                    data = {'rtn': '98', 'msg': u'该SQL存在未包含WHERE的过滤条件，无法执行，请联系管理员!'}
                    return HttpResponse(json.dumps(data))
                # 删除与更新必须有where条件
                else:
                    # update语句进行回滚备份
                    if len(re.findall(r'[| |\n|\r\n]?(?i)update( |\n|\r\n)', sql_command, re.S)) > 0:
                        if sql_command != '' and sql_command != '\n' and sql_command != '\r\n':
                            try:
                                tab_name = ''
                                for i in re.findall(r"(?i)update[ |\n|\r\n]+(.+?)[ |\n|\r\n]+(?i)set.+?", sql_command,
                                                    re.S):
                                    tab_name = ''.join(i)
                                # WHERE条件
                                sql_condition = re.sub(
                                    r"(?i)update[ |\n|\r\n]+(.+?)[ |\n|\r\n]+(?i)set(.+?)[ |\n|\r\n]+(?i)where[ |\n|\r\n]+(.+?)",
                                    '\g<3>', sql_command, flags=re.S)
                                # logger.info('sql_condition is:%s' % sql_condition)
                                # SET值
                                sql_set = re.search(
                                    r"[ |\n|\r\n]+(?i)set[ |\n|\r\n]+(.+?)[ |\n|\r\n]+(?i)where[ |\n|\r\n]+",
                                    sql_command, flags=re.S).group(0)
                                # logger.info('sql_set is:%s' % sql_set)
                                # SET值去掉SET关键字
                                sql_set_col = re.sub(r"([ |\n|\r\n]+)(?i)set([ |\n|\r\n]+)", '', sql_set, flags=re.S)
                                # logger.info('sql_set_col is:%s' % sql_set_col)
                                # # SET字段名称
                                # select_col_where = re.sub(r"(.+?)=(.+?)(?i)(,|WHERE)", '\g<1> \g<3>', sql_set_col,
                                #                           flags=re.S)
                                # logger.info('select_col_where is:%s' % select_col_where)
                                # # select字段名称
                                # select_col = re.sub(r"(.+?)([ |\n|\r\n]+)(?i)where([ |\n|\r\n]+)", '\g<1>\g<2>',
                                #                     select_col_where, flags=re.S)
                                # re.sub(r"(.+?)=[ |\r|\r\n]+.*?(,|WHERE)", '\g<1> \g<2>', s, flags=re.S)
                                # logger.info('select_col is:%s' % select_col)
                                # 考虑set值中包含逗号情况
                                select_col_where1 = re.sub(r"=([ |\n|\r\n]*)'(.+?)'([ |\n|\r\n]*)(?i)(,|where)",
                                                           '\g<1>\g<3>\g<4>', sql_set_col, flags=re.S)
                                select_col_where = re.sub(r"=([ |\n|\r\n]*)(.+?)([ |\n|\r\n]*)(?i)(,|where)",
                                                          '\g<1>\g<3>\g<4>', select_col_where1, flags=re.S)
                                # logger.info('select_col_where is:%s' % select_col_where)
                                select_col = re.sub(r"([ |\r|\r\n]+)(?i)(WHERE)", '\g<1>', select_col_where, flags=re.S)
                                logger.info('select_col is:%s' % select_col)
                                # select语句
                                sql_select = re.sub(
                                    r"(?i)update([ |\r|\r\n]+)(.+?)[ |\r|\r\n]+(?i)set[ |\r|\r\n]+(.+?)[ |\r|\r\n]+(?i)where[ |\r|\r\n]+",
                                    "SELECT %s FROM \g<2> WHERE " % select_col, sql_command, flags=re.S)
                                logger.info('sql_select of update is:%s' % sql_select)
                            except Exception as e:
                                logger.info(u"产生异常的sql id为:%s，sql语句为:%s" % (sql_id, repr(sql_command)))
                                data = {'rtn': '99', 'msg': '生成回滚sql前的查询语句错误:' + str(e)}
                                return HttpResponse(json.dumps(data))
                            # 生成回滚sql
                            try:
                                try:
                                    cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(sql_select, args=())
                                    logger.info(u'查询%d条记录.' % cur_rows)
                                    columns = [x[0] for x in cur_desc]
                                    logger.info('cul_list is:')
                                    logger.info(cur_list)
                                    logger.info('columns is:')
                                    logger.info(columns)
                                except Exception as e:
                                    logger.info(u'更新前查询错误;id:' + sql_id + ',sql:' + sql_command + 'ERROR:' + str(e))
                                    data = {'rtn': '99', 'msg': '查询原值错误:' + str(e)}
                                    return HttpResponse(json.dumps(data))
                                sql_find_list = re.findall(r'=(.+?)(?i)(,|where)', sql_set, re.S)
                                sql_find_list_temp = []
                                for i in sql_find_list:
                                    sql_find_str = ''
                                    for j in i:
                                        sql_find_str += j
                                    sql_find_list_temp.append(sql_find_str)
                                # logger.info('sql_update_list_temp is%s' % sql_find_list_temp)
                                for i in cur_list:
                                    sql_recovery_tmp = ""
                                    for j in range(len(i)):
                                        if re.findall(r"'(.+?)'", sql_find_list_temp[j], re.S):
                                            if i[j] is None:
                                                col_value = 'NULL'
                                            elif i[j] == '':
                                                col_value = "''"
                                            else:
                                                col_value = "'%s'" % i[j]
                                            col_old_value = re.sub(r"'(.+?)'(.*?)(?i)(,|where)",
                                                                   "%s\g<2>\g<3>" % col_value, sql_find_list_temp[j],
                                                                   flags=re.S)
                                        else:
                                            if i[j] is None:
                                                col_value = 'NULL'
                                            elif i[j] == '':
                                                col_value = "''"
                                            else:
                                                col_value = "%s" % i[j]
                                            col_old_value = re.sub(r"(.+?)(?i)(,|where)",
                                                                   "%s \g<2>" % col_value, sql_find_list_temp[j],
                                                                   flags=re.S)
                                        sql_recovery_tmp += "%s=%s " % (columns[j], col_old_value)
                                    logger.info('sql_recovery_tmp is:%s' % sql_recovery_tmp)
                                    sql_recovery_line = "UPDATE %s SET %s %s ;\n" % (
                                        tab_name, sql_recovery_tmp, sql_condition)
                                    if sql_recovery_line in sql_recovery:
                                        pass
                                    else:
                                        sql_recovery += sql_recovery_line
                            except Exception as e:
                                logger.info(u'生成回滚SQL错误;id:' + sql_id + ',sql:' + sql_command + ',ERROR:' + str(e))
                                data = {'rtn': '99', 'msg': '生成回滚SQL错误:' + str(e)}
                                return HttpResponse(json.dumps(data))
                    elif len(re.findall(r'[ |\n|\r\n]?(?i)delete[ |\n|\r\n]+', sql_command, re.S)) > 0:
                        if sql_command != '' and sql_command != '\n' and sql_command != '\r\n':
                            try:
                                sql_select = re.sub(r'[ |\n|\r\n]?(?i)(delete)[ |\n|\r\n]+', 'SELECT * ', sql_command,
                                                    flags=re.S)
                                logger.info('sql_select of delete is:%s' % sql_select)
                                del_tab_name = re.match(
                                    r'(.+?)[ |\n|\r\n]+(?i)from[ |\n|\r\n]+(.+?)[ |\n|\r\n]+(?i)where[ |\n|\r\n]+',
                                    sql_command, re.S).group(2)
                            except Exception as e:
                                logger.info(u"产生异常的sql语句为：%s,sql长度为%d!" % (repr(sql_command), len(sql_command)))
                                data = {'rtn': '99', 'msg': '生成回滚sql前的查询语句错误:' + str(e)}
                                return HttpResponse(json.dumps(data))
                            # 生产回滚sql
                            try:
                                cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(sql_select, args=())
                                logger.info(u'查询%d条记录.' % cur_rows)
                                columns = [x[0] for x in cur_desc]
                                for i in cur_list:
                                    sql_recovery_part = "INSERT INTO %s (%s) VALUES (" % (
                                        del_tab_name, ', '.join(columns))
                                    for j in range(len(i)):
                                        if j == len(i) - 1:
                                            if i[j] is None:
                                                sql_recovery_line_tmp = sql_recovery_part + "NULL"
                                            else:
                                                sql_recovery_line_tmp = sql_recovery_part + "'%s'" % i[j]
                                        else:
                                            if i[j] is None:
                                                sql_recovery_line_tmp = sql_recovery_part + "NULL, "
                                            else:
                                                sql_recovery_line_tmp = sql_recovery_part + "'%s', " % i[j]
                                        sql_recovery_part = sql_recovery_line_tmp
                                    sql_recovery_line = sql_recovery_part + ");\n"
                                    sql_recovery_tmp = sql_recovery + sql_recovery_line
                                    sql_recovery = sql_recovery_tmp
                            except Exception as e:
                                logger.info(u'生成回滚SQL错误;id:' + sql_id + ',sql:' + sql_command + ',ERROR:' + str(e))
                                data = {'rtn': '99', 'msg': '生成回滚SQL错误:' + str(e)}
                                return HttpResponse(json.dumps(data))
                    else:
                        data = {'rtn': '99', 'msg': u'该SQL不是DML:%s' % sql_command}
                        return HttpResponse(json.dumps(data))
        logger.info('sql_recovery is:%s' % sql_recovery)
        if not os.path.exists(sql_logs_path):
            os.makedirs(sql_logs_path)
        current_day_log_path = os.path.join(sql_logs_path, db_env, db_name,
                                            datetime.datetime.now().strftime('%Y-%m-%d'))
        if not os.path.exists(current_day_log_path):
            os.makedirs(current_day_log_path)
        sql_recovery_file = os.path.join(current_day_log_path, sql_id + '.recovery.sql')
        # 将回滚sql写入文件保存
        file_object = open(sql_recovery_file, 'w')
        file_object.write(sql_recovery)
        file_object.write('\n')
        file_object.close()
        try:
            cur_rows = conn.exec_non_select(sql_commands, args=())
            logger.info(u'影响%d行！' % cur_rows)
            data = {'rtn': '00', 'msg': u'执行成功'}
            try:
                sql = Sql.objects.filter(id=sql_id)
                sql.update(result='执行成功', end_time=timezone.now(), execute_user=request.user.username,
                           recovery_file=sql_recovery_file)
            except Exception as e:
                logger.info(u'执行sql id:' + sql_id + u' 成功,但更新sql执行结果错误:' + str(e))
                data = {'rtn': '98', 'msg': '执行sql成功，但更新sql执行结果错误:' + str(e)}
        except Exception as e:
            sql = Sql.objects.filter(id=sql_id)
            sql.update(result='执行失败', end_time=timezone.now(), execute_user=request.user.username)
            logger.info(u'执行sql错误;id:' + sql_id + ',sql:' + sql_commands + ',ERROR:' + str(e))
            data = {'rtn': '99', 'msg': '执行SQL错误:' + str(e)}
        return HttpResponse(json.dumps(data))
    else:
        data = {'rtn': '99', 'msg': u'没有操作权限，请联系管理员添加权限!'}
        return HttpResponse(json.dumps(data))


@csrf_exempt
@login_required
def get_new_line(request):
    if request.method == 'POST':
        try:
            file_obj = json.loads(request.body)['file']
            seek = json.loads(request.body)['seek']
            with open(file_obj) as f:
                # Go to the end of file
                # f.seek(0, 2)
                curr_position = int(seek)
                f.seek(curr_position)
                lines = f.readlines()
                if not lines:
                    f.seek(curr_position)
                    data = {'lines': [], 'seek': seek}
                    # time.sleep(s)
                else:
                    seek = f.tell()
                    data = {'lines': lines, 'seek': seek}
                # logger.info(data)
                return HttpResponse(json.dumps(data))
        except Exception as e:
            logger.info(e)
    else:
        logger.info(request.method)
        return HttpResponse(json.dumps({'line': 'ERR'}))


@csrf_exempt
@login_required
@permission_required('nova.access_command', raise_exception=True)
def shell(request):
    file_name = request.user.username + '.command.log'
    command_file = os.path.join(base_path, 'logs', file_name)
    if not os.path.exists(command_file):
        os.mknod(command_file)
    file_size = os.path.getsize(command_file)
    if request.method == 'POST':
        command = json.loads(request.body)['command']
        asset_ip = json.loads(request.body)['asset_ip']

        # 使用ansible API接口
        # results = Runner(
        #     pattern='*',
        #     # pattern='web2',
        #     forks=10,
        #     module_name='shell',
        #     module_args=command,
        #     host_list=asset_ip,
        #     # remote_port=10085,
        #     remote_user='root',
        #     # private_key_file = key_path,
        #     environment={'LANG': 'zh_CN.UTF-8', 'LC_CTYPE': 'zh_CN.UTF-8'}
        # ).run()
        #
        # if results is None:
        #     print "No hosts found"
        #     sys.exit(1)
        #
        # for (key, msg) in results.items():
        #     try:
        #         with open(command_file, 'a') as f:
        #             if key == 'dark':
        #                 print "DOWN *********"
        #                 for (hostname, result) in msg.items():
        #                     logger.info("%s DOWN>>> %s\n" % (hostname, result))
        #                     f.write("%s DOWN>>> \n%s\n" % (hostname, result))
        #             if key == 'contacted':
        #                 for (hostname, result) in msg.items():
        #                     if 'failed' in result:
        #                         print "FAILED *******"
        #                         logger.info("%s FAILED>>> %s\n" % (hostname, result))
        #                         f.write("%s FAILED>>> \n%s\n" % (hostname, result))
        #                     else:
        #                         print "UP ***********"
        #                         logger.info("%s STDOUT>>> %s\n" % (hostname, result['stdout']))
        #                         f.write("%s STDOUT>>> \n%s\n" % (hostname, result['stdout']))
        #     except Exception as e:
        #         logger.info(e)

        # 使用ansible 命令
        command = '''ansible all -i "%s," -m shell -a "%s"''' % (asset_ip, command)
        logger.info(command)
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = ''
        errors = ''
        logger.info(command_file)
        while True:
            if p.stdout:
                stdout = p.stdout.readline()
                if stdout == '' and p.poll() is not None:
                    break
                if stdout != '':
                    # logger.info(stdout.strip('\n'))
                    output = output + stdout
                    # file_object.write(stdout)
                    with open(command_file, 'a') as f:
                        f.write(stdout)
            if p.stderr:
                stderr = p.stderr.readline()
                if stderr == '' and p.poll() is not None:
                    break
                if stderr != '':
                    logger.info(u'执行命令出错了！')
                    logger.info(stderr.strip('\n'))
                    errors = errors + stderr
                    # file_object.write(stderr)
                    with open(command_file, 'a') as f:
                        f.write(stderr)

        data = {'rtn': '00', 'command': command, 'command_file': command_file, 'file_size': file_size}
        logger.info(data)
        return HttpResponse(json.dumps(data))
    else:
        asset_ip = request.GET.get('asset_ip')
        data = {'asset_ip': asset_ip, 'command_file': command_file, 'file_size': file_size}
    return render(request, 'shell.html', data)


# @require_role('user')
@login_required()
@csrf_exempt
def host_connect(request, asset_id):
    username = request.user.username
    # asset_id = request.GET.get('asset_id')
    user_asset_ids = get_user_asset_id(request)
    if int(asset_id) in user_asset_ids:
        role_name = request.GET.get('role')
        asset = get_object(Asset, id=asset_id)
        if asset:
            hostname = asset.hostname
            host_ip = asset.ip
            host_user = username
            host_port = asset.port
        if not host_ip:
            return render(request, '404.html', locals())
        else:
            return render(request, 'gateone.html', locals())
    else:
        data = json.dumps({'rtn': "99", 'msg': "没有连接权限，请联系管理员!!!"})
        return render(request, 'message.html', data)


# @require_role('user')
@login_required
def get_auth_obj(request):
    # import time, hmac, hashlib, json
    user = request.user.username
    # 安装gateone的服务器以及端口.
    gateone_server = GATEONE_SERVER
    # 之前生成的api_key 和secret
    gateone_api_key = GATEONE_API_KEY
    gateone_secret = GATEONE_SECRET

    authobj = {
        'api_key': gateone_api_key,
        'upn': "gateone",
        'timestamp': str(int(time.time() * 1000)),
        'signature_method': 'HMAC-SHA1',
        'api_version': '1.0'
    }
    my_hash = hmac.new(gateone_secret, digestmod=hashlib.sha1)
    my_hash.update(authobj['api_key'] + authobj['upn'] + authobj['timestamp'])

    authobj['signature'] = my_hash.hexdigest()
    auth_info_and_server = {"url": gateone_server, "auth": authobj}
    valid_json_auth_info = json.dumps(auth_info_and_server)
    # logger.info(valid_json_auth_info)
    return HttpResponse(valid_json_auth_info)


@login_required
def task_log(request):
    try:
        celery_log = Config.objects.get(name='log', config_key='celery_log').config_value
        file_size = os.path.getsize(celery_log)
        data = {'log_file': celery_log, 'file_size': file_size}
        return render(request, 'task_logs.html', context=data)
    except Exception as e:
        logger.info(e)
        data = json.dumps({'rtn': "99", 'msg': "无法打开日志文件，请联系管理员!!!"})
        return render(request, 'message.html', data)


@login_required()
@csrf_exempt
@permission_required('nova.access_file', raise_exception=True)
def update_ksbm_oss_file(request):
    logger.info('User is:%s;Request is: upload file to oss.' % request.user.username)
    if User.has_perm(request.user, 'nova.upload_oss_file'):
        if request.body:
            upload_file_id = json.loads(request.body)['upload_file_id']
            ksnd = json.loads(request.body)['ksnd']
            fjlx_dm = json.loads(request.body)['fjlx_dm']
            db_name = json.loads(request.body)['db_name']
            db_env = json.loads(request.body)['db_env']
        else:
            data = {'rtn': '98', 'msg': u'未提交必要参数!'}
            return HttpResponse(json.dumps(data))
        try:
            db_info = Database.objects.get(db_name=db_name, env=db_env)
        except Database.DoesNotExist:
            data = {'rtn': '99', 'msg': u'未找到该数据库配置！'}
        logger.info('db_info is:%s' % db_info)
        endpoint = ENDPOINT
        # 连接数据库
        try:
            if db_info.type == 'sqlserver':
                conn = MsSQL(host=db_info.ip, port=db_info.port, db=db_info.db_name, user=db_info.username,
                             password=db_info.password)
            if db_info.type == 'mysql':
                conn = Mysql(host=db_info.ip, port=int(db_info.port), db=db_info.db_name, user=db_info.username,
                             password=db_info.password, charset="utf8")
        except Exception as e:
            data = {'rtn': '99', 'msg': '连接数据库错误:' + str(e)}
            return HttpResponse(json.dumps(data))
        upload_file = UploadFile.objects.get(id=upload_file_id)
        logger.info('upload file:%s' % upload_file.file_name)
        accessKey = OssBucketApp.objects.get(name=upload_file.app_name, env=upload_file.env).accesskey_set.get()
        try:
            auth = oss2.Auth(accessKey.accessKeyID, _dec_(data=accessKey.accessKeySecret))
            logger.info(u'认证成功.')
            endpoint = 'http://oss-cn-beijing.aliyuncs.com'
        except Exception as e:
            logger.info(e)
            data = {'rtn': '97', 'msg': 'OSS认证失败:' + str(e)}
            return HttpResponse(json.dumps(data))
        # 判断使用cname访问
        if len(accessKey.cname) > 1:
            bucket = oss2.Bucket(auth, accessKey.cname, accessKey.ossBucketName, is_cname=True)
        else:
            bucket = oss2.Bucket(auth, endpoint, accessKey.ossBucketName)
        try:
            zjhm = upload_file.file_name.split('.')[0]
            sql = """SELECT FJ FROM bm_fjxx a, bm_bmxx b where a.BMXH=b.BMXH AND
                     b.ZJHM=%s AND b.BMXH LIKE %s AND a.FJLX_DM=%s"""
            args = (zjhm, ksnd, fjlx_dm)
            logger.info(sql)
            logger.info(args)
            cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(sql, args)
            logger.info(u'查询%d条记录！' % cur_rows)
            for i in dict_list:
                old_url = i.get('FJ')
                logger.info('OLD url is :%s' % old_url)
                url = re.sub(r"([http|https]://.+?)\?.+", '\g<1>', old_url)
                logger.info('file_url is: %s' % url)
                # 上传object文件
                local_path = upload_file.file_path
                dest_url = re.sub(r"http.+?com/(.+?)", '\g<1>', url)
                with open(local_path, 'rb') as file_obj:
                    bucket.put_object(dest_url, file_obj)
                new_url = bucket.sign_url('GET', dest_url, 60 * 60 * 24 * 365 * 500)  # 获取object签名
                new_url2 = new_url.replace('%2F', '/')
                logger.info('NEW url is :%s' % new_url2)
                sql = """UPDATE bm_fjxx a, bm_bmxx b SET a.FJ=%s where a.BMXH=b.BMXH AND
                          b.ZJHM=%s AND b.BMXH LIKE %s AND a.FJLX_DM=%s"""
                args = (new_url2, zjhm, ksnd, fjlx_dm)
                logger.info(sql)
                logger.info(args)
                cur_rows = conn.exec_non_select(sql, args)
                logger.info(u'影响%d行！' % cur_rows)
                data = {'rtn': "00", 'msg': "更新成功"}
                try:
                    UploadFile.objects.filter(id=upload_file_id).update(result='更新成功', upload_time=timezone.now())
                except Exception as e:
                    data = {'rtn': '98', 'msg': '更新文件成功，但更新该执行结果错误:' + str(e)}
                return HttpResponse(json.dumps(data))
        except Exception as e:
            logger.info(e)
            data = {'rtn': "99", 'msg': "更新失败:" + str(e)}
            return HttpResponse(json.dumps(data))
    else:
        data = {'rtn': "99", 'msg': "没有权限，请联系管理员！"}
        return HttpResponse(json.dumps(data))


@login_required
@permission_required('nova.access_file', raise_exception=True)
def upload_file_list(request):
    logger.info('User is%s;Request is: upload file.' % request.user.username)
    if User.has_perm(request.user, 'nova.upload_oss_file'):
        res = request.GET
        if 'upload_file_id' in res:
            upload_file_id = request.GET['upload_file_id']
            upload_files = UploadFile.objects.filter(id=upload_file_id)
        else:
            upload_files = UploadFile.objects.order_by('-upload_time').all()
        data = {'upload_files': upload_files}
        return render(request, 'upload_file.html', context=data)
    else:
        # return render(request, 'deny.html')
        return render(request, 'deny.html')


@login_required
def http_data(request):
    """
    第一次查询全量数据，后面只查询增量数据
    :param request:
    :return:
    """
    # 连接数据库
    res = request.GET
    if 'last_time' in res:
        last_time = request.GET['last_time']
    else:
        last_time = 0
    if 'item_id' in res:
        item_id = request.GET['item_id']
        try:
            item_name = HttpStep.objects.get(item_id=item_id).name
        except HttpStep.DoesNotExist:
            item_name = ServiceStep.objects.get(item_id=item_id).name
        except Exception as e:
            logger.info(e)
    else:
        item_id = 0
    try:
        history = History.objects.filter(clock__gt=last_time, item_id=item_id)
    except Exception as e:
        logger.info(e)
    data = []
    for i in history:
        # 获取当前时间，数据库存的time.time()时间戳单位是秒，JS中则单位是毫秒，所以这里乘以1000
        # 需要GMT时间+8小时
        data.append([(i.clock + 8 * 60 * 60) * 1000, i.value])
    if len(data) > 0:
        last_time = data[-1][0] / 1000 - 8 * 60 * 60
    content = {"item": item_id, "msg": u"操作成功！", "data": data, 'last_time': last_time, 'item_name': item_name}
    # logger.info(item_id)
    return HttpResponse(json.dumps(content), content_type='application/json')


@login_required
@permission_required('nova.access_monitor', raise_exception=True)
def monitor_web(request):
    res = request.GET
    if 'item_id' in res:
        item_id = request.GET['item_id']
        try:
            item_name = HttpStep.objects.get(item_id=item_id).name
        except HttpStep.DoesNotExist:
            item_name = ServiceStep.objects.get(item_id=item_id).name
        except Exception as e:
            logger.info(e)
        data = {'item_id': item_id, 'item_name': item_name}
        return render(request, 'monitor_item.html', data)
    else:
        http_tests = HttpTest.objects.order_by('-item_id').all()
        data = {'http_tests': http_tests}
        return render(request, 'monitor.html', data)


@login_required
@csrf_exempt
@permission_required('nova.access_monitor', raise_exception=True)
def fpcy_request_log(request):
    if request.method == 'GET':
        service_tests = ServiceTest.objects.order_by('-item_id').all()
        data = {'service_tests': service_tests}
        return render(request, 'fpcy_request_log.html', data)
    if request.method == 'POST':
        param = json.loads(request.body)
        # logger.info(param)
        if param and param.get('item_id') == 'all':
            service_test = ServiceTest.objects.all()
        try:
            data = serializers.serialize('json', service_test, fields=('item_id', 'result', 'comment'))
        except Exception as e:
            print e
        return HttpResponse(json.dumps(data), content_type='application/json')
    else:
        data = {'rtn': '99', 'msg': u'请求非法，未提交必要参数!'}
        return HttpResponse(json.dumps(data, encoding='utf-8', ensure_ascii=False))


@login_required()
@csrf_exempt
@permission_required('nova.access_log', raise_exception=True)
def access_log(request):
    logger.info('User is:%s;Request is: query access log.' % request.user.username)
    db_name = 'app_log'
    db_env = 'slave'
    try:
        db_info = Database.objects.get(db_name=db_name, env=db_env)
    except Database.DoesNotExist:
        data = {'rtn': '99', 'msg': u'未找到该数据库配置！'}
    logger.info('db_info is:%s' % db_info)
    # 连接数据库
    try:
        if db_info.type == 'mongodb':
            mongodb = Mongodb(host=db_info.ip, port=db_info.port, db=db_info.db_name, user=db_info.username,
                              password=db_info.password)
    except Exception as e:
        data = {'rtn': '99', 'msg': '连接数据库错误:' + str(e)}
        return HttpResponse(json.dumps(data))
    db = mongodb.get_database()
    collection = db['nginx_ls']
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=string.atoi('1'))
    start_time = datetime.datetime.strptime(str(start_date), '%Y-%m-%d')
    end_time = datetime.datetime.strptime(str(today), '%Y-%m-%d')
    logger.info(start_time)
    logger.info(end_time)
    if request.method == 'GET':
        all_counts = collection.find({"time": {"$gte": start_time, "$lte": end_time}}).count()
        page_size = 10
        # 记算分多少页
        if all_counts % page_size != 0:
            page_count = (all_counts / page_size) + 1
        else:
            page_count = (all_counts / page_size)
        page_index = 1
        if page_index == 1:
            access_logs = list(
                collection.find({"time": {"$gte": start_time, "$lte": end_time}}, {"_id": 0}).limit(page_size))
        else:
            access_logs = list(collection.find({"time": {"$gte": start_time, "$lte": end_time}}, {"_id": 0}).skip(
                page_index * page_size).limit(page_size))
        page_size_option = [10, 20, 50, 100]
        data = {'start_time': start_time, 'end_time': end_time, 'access_logs': access_logs, 'all_counts': all_counts,
                'page_index': page_index,
                'page_count': page_count, 'page_size': page_size, 'page_size_option': page_size_option}
        return render(request, 'access_log.html', data)
    if request.method == 'POST':
        param = json.loads(request.body)
        logger.info(param)
        if param:
            page_index = param['page_index']
            page_size = param['page_size']
            ip = param.get('ip')
            status = param.get('status')
            refer = param.get('refer')
            request = param.get('request')
            start_time = param.get('start_time')
            end_time = param.get('end_time')
            user_agent = param.get('userAgent')
            if len(start_time) == 10:
                start_time = datetime.datetime.strptime(start_time.encode('utf-8'), '%Y-%m-%d')
            else:
                start_time = datetime.datetime.strptime(start_time.encode('utf-8'), '%Y-%m-%d %H:%M:%S')
            if len(end_time) == 10:
                end_time = datetime.datetime.strptime(end_time.encode('utf-8'), '%Y-%m-%d')
            else:
                end_time = datetime.datetime.strptime(end_time.encode('utf-8'), '%Y-%m-%d %H:%M:%S')
            logger.info(start_time)
            logger.info(end_time)
            query_args = {}
            if start_time != '' and end_time != '':
                query_args['time'] = {"$gte": start_time, "$lte": end_time}
            for k, v in param.items():
                if v != '':
                    if k == 'ip' or k == 'status':
                        query_args[k] = '%s' % v
                    if k == 'refer' or k == 'request' or k == 'userAgent':
                        query_args[k] = {"$regex": v, "$options": "i"}
            logger.info(query_args)
            try:
                all_counts = collection.find(query_args).count()
            except Exception as e:
                logger.info(e)
            if all_counts == 0:
                data = {'rtn': '01', 'msg': u'查询不到数据!'}
                logger.info(data)
                return HttpResponse(json.dumps(data))
            else:
                if page_index == 1:
                    access_logs = list(
                        collection.find(query_args, {"_id": 0}).limit(page_size))
                else:
                    access_logs = list(
                        collection.find(query_args, {"_id": 0}).skip((page_index - 1) * page_size).limit(page_size))
                try:
                    for i in access_logs:
                        i['time'] = i['time'].strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    logger.info(e)
                # 记算分多少页
                if all_counts % page_size != 0:
                    page_count = (all_counts / page_size) + 1
                else:
                    page_count = (all_counts / page_size)
                page_size_option = [10, 20, 50, 100]
                data = {'rtn': '00', 'access_logs': access_logs, 'all_counts': all_counts,
                        'page_index': page_index, 'page_count': page_count, 'page_size': page_size,
                        'page_size_option': page_size_option}
                return HttpResponse(json.dumps(data), content_type='application/json')
        else:
            data = {'rtn': '99', 'msg': u'请求非法，未提交必要参数!'}
            return HttpResponse(json.dumps(data))


def query_fpcy_from_mongodb(data_time, end_time, collection):
    # 查询发票查验数据
    logger.info(u'从mongodb提取发票查验统计数据.')
    try:
        # data_list = collection.find_one({"time": data_time}, {"_id": 0, "time": 0})
        data_list = collection.find_one({"time": {"$gte": data_time, "$lt": end_time}}, {"_id": 0, "time": 0})
        # logger.info(str(data_list).decode('string_escape'))
        # logger.info(data_list)
        logger.info(data_list['data'])
        return data_list['data']
    except Exception as e:
        # logger.info(u'从mongodb提取发票查验统计数据异常:' + str(e))
        logger.info(u'从mongodb提取发票查验统计数据异常！')
        return None


@login_required()
@csrf_exempt
@permission_required('nova.access_monitor', raise_exception=True)
def fpcy_stat(request):
    db_env = 'slave'
    try:
        # 连接mongodb数据库
        info_mongo = Database.objects.get(db_name='stats', env=db_env)
        mongodb = Mongodb(host=info_mongo.ip, port=info_mongo.port, db=info_mongo.db_name, user=info_mongo.username,
                          password=info_mongo.password)
        db_mongo = mongodb.get_database()
    except Exception as e:
        data = {'rtn': '99', 'msg': u'连接数据库错误:' + str(e)}
        logger.info(data)
    if request.method == 'GET':
        page_index = 1
        page_size = 10
        res = request.GET
        if 'stat_day' in res:
            begin_day = request.GET['stat_day']
            stat_day = datetime.datetime.strptime(str(begin_day), '%Y-%m-%d')
        else:
            # 默认当天年月日
            begin_day = datetime.date.today()
            # date转datetime
            # begin_day_datetime = datetime.datetime.strptime(str(begin_day), '%Y-%m-%d')
            # 当天00:00:00转时间戳
            begin_day_seconds = time.mktime(datetime.datetime.strptime(str(begin_day), '%Y-%m-%d').timetuple())
            # 当天22:00前取前一天
            if time.time() - begin_day_seconds < 22 * 60 * 60:
                stat_day = begin_day - datetime.timedelta(days=string.atoi('1'))
            else:
                stat_day = datetime.date.today()
            # date转datetime
            stat_day = datetime.datetime.strptime(str(stat_day), '%Y-%m-%d')
        # 统计开始与统计结束时间均取22:00:00
        begin_time = stat_day - datetime.timedelta(hours=string.atoi('2'))
        end_time = begin_time + datetime.timedelta(hours=string.atoi('24'))
        last_time = stat_day - datetime.timedelta(days=string.atoi('1'))
        # 转字符串
        begin_time = begin_time.strftime('%Y-%m-%d %H:%M:%S')
        last_time = last_time.strftime('%Y-%m-%d')
        end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
        stat_day = stat_day.strftime('%Y-%m-%d')
        # # date转datetime
        # begin_day_datetime = datetime.datetime.strptime(begin_time, '%Y-%m-%d %H:%M:%S')
        # last_day_datetime = datetime.datetime.strptime(last_time, '%Y-%m-%d')
        # end_day_datetime = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        logger.info('begin_time is: %s' % begin_time)
        logger.info('end_time is: %s' % end_time)
        logger.info('stat_day is: %s' % stat_day)

        try:
            # 发票入库情况
            logger.info('#' * 100)
            logger.info(u'发票入库情况:')
            try:
                collection = db_mongo['fpcy_fprkqk']
                data_sql_fprkqk = query_fpcy_from_mongodb(begin_time, end_time, collection)
            except Exception as e:
                logger.info(e)

            # 营收情况
            logger.info(u'营收情况:')
            data_sql_ysqk = []
            collection = db_mongo['fpcy_ysqk_dmfy']
            # 获取超级鹰用户的题分信息
            try:
                collection = db_mongo['fpcy_ysqk']
                data_sql_ysqk = query_fpcy_from_mongodb(begin_time, end_time, collection)
            except Exception as e:
                logger.info(e)

            # 用户充值、消费点数情况
            logger.info(u'用户充值、消费点数情况:')
            try:
                collection = db_mongo['fpcy_yhczxfdsqk']
                data_sql_yhczxfdsqk = query_fpcy_from_mongodb(begin_time, end_time, collection)
            except Exception as e:
                logger.info(e)

            logger.info(u'用户查验反馈情况表:')
            try:
                collection = db_mongo['fpcy_yhcyfkqk']
                data_sql_yhcyfkqkb = query_fpcy_from_mongodb(begin_time, end_time, collection)
            except Exception as e:
                logger.info(e)

            logger.info(u'子产品查验情况表:')
            try:
                collection = db_mongo['fpcy_zcpcyqk']
                data_sql_zcpcyqks = query_fpcy_from_mongodb(begin_time, end_time, collection)
            except Exception as e:
                logger.info(e)

            logger.info(u'企业接口查验情况:')
            try:
                collection = db_mongo['fpcy_qyjkcyqk']
                data_sql_qyjkcyqks = query_fpcy_from_mongodb(begin_time, end_time, collection)
            except Exception as e:
                logger.info(e)

            logger.info(u'核心服务状态表:')
            try:
                collection = db_mongo['fpcy_hxfwzt']
                data_sql_hxfwztbs = query_fpcy_from_mongodb(begin_time, end_time, collection)
            except Exception as e:
                logger.info(e)

            logger.info(u'税局查验服务状态表:')
            try:
                collection = db_mongo['fpcy_sjcyfwzt']
                data_sql_sjcyfwztbs = query_fpcy_from_mongodb(begin_time, end_time, collection)
            except Exception as e:
                logger.info(e)

            logger.info(u'打码情况:')
            try:
                collection = db_mongo['fpcy_dmqk']
                data_sql_dmqks = query_fpcy_from_mongodb(begin_time, end_time, collection)
            except Exception as e:
                logger.info(e)

            logger.info(u'税局响应情况（>60秒）:')
            try:
                collection = db_mongo['fpcy_sjxyqk']
                data_sql_sjxyqks = query_fpcy_from_mongodb(begin_time, end_time, collection)
            except Exception as e:
                logger.info(e)

            logger.info(u'用户查验请求详情:')
            try:
                collection = db_mongo['fpcy_yhcyqqxq']
                data_sql_yhcyqqxq = query_fpcy_from_mongodb(begin_time, end_time, collection)
            except Exception as e:
                logger.info(e)

            logger.info(u'税局查验请求详情:')
            try:
                collection = db_mongo['fpcy_sjcyqqxq']
                data_sql_sjcyqqxq = query_fpcy_from_mongodb(begin_time, end_time, collection)
            except Exception as e:
                logger.info(e)

            logger.info(u'用户账号点数情况:')
            try:
                collection = db_mongo['fpcy_yhzhdsqk']
                # data_fpcy_yhzhdsqk = query_fpcy_from_mongodb(begin_time, end_time, collection)
                # add 20180424
                all_counts = len(collection.find_one({"time": stat_day}).get('data'))
                # 记算分多少页
                if all_counts % page_size != 0:
                    page_count = (all_counts / page_size) + 1
                else:
                    page_count = (all_counts / page_size)
                if page_index == 1:
                    data_fpcy_yhzhdsqk = collection.find_one({"time": stat_day}, {"_id": 0, "time": 0}).get('data')[0:10]
                else:
                    data_start = (page_index - 1) * page_size
                    data_end = (page_index - 1) * page_size + page_size
                    data_fpcy_yhzhdsqk = collection.find_one({"time": stat_day}, {"_id": 0, "time": 0}).get('data')[
                                         data_start:data_end]
                page_size_option = [10, 20, 50, 100]
                logger.info(data_fpcy_yhzhdsqk)
                # end add 20180424
            except Exception as e:
                logger.info(e)
                data_fpcy_yhzhdsqk = None

            logger.info(u'百望查验服务状态表:')
            try:
                collection = db_mongo['fpcy_bwcyfwztb']
                data_sql_bwcyfwztb = query_fpcy_from_mongodb(begin_time, end_time, collection)
            except Exception as e:
                logger.info(e)

            # 统计核心服务状态表取乐税与百望的合计
            data_sql_hxfwztb_sum = []
            data_hxfwztb_tmp = data_sql_hxfwztbs[-1]
            data_hxfwztb_tmp[0] = u'乐税'
            data_sql_hxfwztb_sum.append(data_hxfwztb_tmp)
            data_hxfwztb_tmp = data_sql_bwcyfwztb[-1]
            data_hxfwztb_tmp[0] = u'百望'
            data_sql_hxfwztb_sum.append(data_hxfwztb_tmp)
            # 计算合计
            data_col_len = len(data_sql_hxfwztb_sum[0])
            total = [0 for i in range(data_col_len)]
            for i in data_sql_hxfwztb_sum:
                for j in range(len(i))[1:]:
                    try:
                        if i[j] != '' and i[j] is not None and str(i[j]).find('%') == -1 and str(i[j]).find('-') == -1:
                            total[j] = total[j] + i[j]
                        if str(i[j]).find('%') != -1:
                            total[j] = '-'
                        if str(i[j]).find('-') != -1:
                            pass
                    except Exception as e:
                        logger.info(e)
            total[0] = u'合计'
            for i in range(len(total)):
                if total[i] == 0:
                    total[i] = '-'
            data_sql_hxfwztb_sum.append(total)
            # 重新计算合计后的百分比
            try:
                for record in data_sql_hxfwztb_sum:
                    record[3] = str(round(float(record[2]) / float(record[1]) * 100, 2)) + '%'
                    record[5] = str(round(float(record[4]) / float(record[1]) * 100, 2)) + '%'
                    record[7] = str(round(float(record[6]) / float(record[1]) * 100, 2)) + '%'
                    record[9] = str(round(float(record[8]) / float(record[1]) * 100, 2)) + '%'
            except Exception as e:
                logger.info(e)
            logger.info(data_sql_hxfwztb_sum)

            # 核心服务状态表明细
            data_hxfwztb = json.dumps(data_sql_hxfwztbs)
            data_bwcyfwztb = json.dumps(data_sql_bwcyfwztb)

            logger.info(data_hxfwztb)
            logger.info(data_bwcyfwztb)
            logger.info('#' * 100)
        except Exception as e:
            data = {'rtn': '99', 'msg': u'查询错误:' + str(e)}
            logger.info(data)
        if datetime.datetime.strptime(str(stat_day), '%Y-%m-%d') >= datetime.datetime.strptime(str('2018-04-20'),
                                                                                               '%Y-%m-%d'):
            return render(request, 'fpcy_stat.html', locals())
        else:
            return render(request, 'fpcy_stat.20180419.html', locals())
    else:
        param = json.loads(request.body)
        if param:
            page_index = param['page_index']
            page_size = param['page_size']
            table_name = param.get('table_name')
            stat_day = param['stat_day']
            logger.info(u'用户账号点数情况:')
            try:
                collection = db_mongo['fpcy_yhzhdsqk']
                all_counts = len(collection.find_one({"time": stat_day}).get('data'))  # 记算分多少页
                if all_counts % page_size != 0:
                    page_count = (all_counts / page_size) + 1
                else:
                    page_count = (all_counts / page_size)
                if page_index == 1:
                    data_fpcy_yhzhdsqk = collection.find_one({"time": stat_day}, {"_id": 0, "time": 0}).get('data')[
                                         0:page_size]
                else:
                    data_start = (page_index - 1) * page_size
                    data_end = (page_index - 1) * page_size + page_size
                    data_fpcy_yhzhdsqk = collection.find_one({"time": stat_day}, {"_id": 0, "time": 0}).get('data')[
                                         data_start:data_end]
                page_size_option = [10, 20, 50, 100]
            except Exception as e:
                logger.info(e)
            logger.info(data_fpcy_yhzhdsqk)
            data = {'rtn': '00', 'data_fpcy_yhzhdsqk': data_fpcy_yhzhdsqk, 'all_counts': all_counts,
                    'page_index': page_index, 'page_count': page_count, 'page_size': page_size,
                    'page_size_option': page_size_option}
            return HttpResponse(json.dumps(data), content_type='application/json')


@login_required
@csrf_exempt
def get_fpcy_request_area(request):
    # 业务库
    db_env = 'slave'
    # 连接数据库
    try:
        # fpcy库
        db_info = Database.objects.get(db_name='fpcy', env=db_env)
        conn = Mysql(host=db_info.ip, port=int(db_info.port), db=db_info.db_name, user=db_info.username,
                     password=db_info.password, charset="utf8")
    except Exception as e:
        data = {'rtn': '99', 'msg': u'连接数据库错误:' + str(e)}
        logger.info(json.dumps(data, encoding='utf-8', ensure_ascii=False))
    if request.method == 'GET':
        res = request.method
        if 'stat_day' in res:
            begin_day = request.GET['stat_day']
            begin_time = datetime.datetime.strptime(str(begin_day), '%Y-%m-%d')
        else:
            # 默认当天年月日
            begin_day = datetime.date.today()
            begin_time = datetime.date.today()
        end_time = begin_time + datetime.timedelta(days=string.atoi('1'))
        begin_time = begin_time.strftime('%Y-%m-%d')
        end_time = end_time.strftime('%Y-%m-%d')
        try:
            sql1 = """
                  SELECT SUBSTR(a.invoiceType,1,3) name,count(*) value from (
                  SELECT invoiceType,count(*) cnt FROM fpcy_requeststatistics_log
                  WHERE inputTime BETWEEN %s AND %s
                  GROUP BY invoiceType order by invoiceType
                  )a where a.invoiceType like %s
                  GROUP BY SUBSTR(a.invoiceType,1,5) ORDER BY 2 desc
            """
            sql2 = """
                  SELECT invoiceType,count(*) cnt FROM fpcy_requeststatistics_log
                  WHERE inputTime BETWEEN %s AND %s AND invoiceType like %s
                  GROUP BY invoiceType order by invoiceType
                  """
            args = (begin_time, end_time, '%增值税%')
            cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(sql1, args)
            req_list = dict_list
            cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(sql2, args)
            for i in req_list:
                name = i['name']
                detail = ''
                for j in dict_list:
                    if name in j['invoiceType']:
                        detail += j['invoiceType'] + '：' + str(j['cnt']) + ';'
                i['detail'] = detail
        except Exception as e:
            logger.info(e)
        data = {'req_list': req_list}
        return HttpResponse(json.dumps(data))


@login_required
@csrf_exempt
@permission_required('nova.access_monitor', raise_exception=True)
def fpcy_request_area(request):
    return render(request, 'fpcy_request_area.html')


def file_iterator(file_name, chunk_size=1024):
    with open(file_name) as f:
        while True:
            c = f.read(chunk_size)
            if c:
                yield c
            else:
                break


@login_required
@csrf_exempt
@permission_required('nova.access_file', raise_exception=True)
def download(request):
    logger.info("User is:%s;Request is:download file!" % request.user.username)
    if User.has_perm(request.user, 'nova.access_file'):
        if request.method == 'POST':
            assets = request.POST.getlist('assets_name', '')
            file_path = request.POST.get('file_path')
            if 'webapps' in file_path:
                data = {'msg': u'下载文件包含敏感文件，请联系管理员！'}
                return render(request, 'message.html', data)
            local_base_path = '/tmp'
            time_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            download_path = os.path.join(local_base_path, time_now)
            if os.path.exists(download_path):
                pass
            else:
                os.makedirs('%s' % download_path)
            for i in assets:
                asset = Asset.objects.get(ip=i)
                local_path = os.path.join(download_path, asset.ip)
                os.makedirs('%s' % local_path)
                # 下载文件
                try:
                    RunCmd(host=asset.ip, port=asset.port, username=asset.username,
                           password=asset.password).download_file(file_path, local_path)
                except Exception as e:
                    logger.info(e)
            tmp_dir_name = os.path.basename(download_path)
            file_zip = local_base_path + '/' + tmp_dir_name + '.zip'
            zf = zipfile.ZipFile(file_zip, "w", zipfile.ZIP_DEFLATED)
            for dirname, subdirs, files in os.walk(download_path):
                zf.write(dirname)
                for filename in files:
                    zf.write(os.path.join(dirname, filename))
            zf.close()
            shutil.rmtree(download_path)
            file_size = os.path.getsize(file_zip)
            if file_size >= 200 * 1024 * 1024:
                data = {'msg': u'压缩文件大小超过200MB, 请联系管理员！'}
                return render(request, 'message.html', data)
            else:
                response = StreamingHttpResponse(file_iterator(file_zip))
                response['Content-Type'] = 'application/octet-stream'
                response['Content-Disposition'] = 'attachment;filename="%s.zip"' % tmp_dir_name
                return response
        if request.method == 'GET':
            return render(request, 'download.html')
    else:
        return render(request, 'deny.html')


@login_required
@csrf_exempt
@permission_required('nova.access_command', raise_exception=True)
def config_ssh_public_key(request):
    logger.info("User is:%s;Request is:config ssh public key!" % request.user.username)
    if User.has_perm(request.user, 'nova.access_command'):
        if request.method == 'POST':
            asset_ips = json.loads(request.body)['asset_ip'].encode('utf-8')
            asset_user = json.loads(request.body)['asset_user'].encode('utf-8')
            logger.info(asset_ips)
            asset_ip_list = asset_ips.split(',')
            lines = ''
            ansible_hosts_file = '/etc/ansible/hosts'
            if asset_user == 'dcyt':
                # 创建ssh公钥
                cmd = '''su - dcyt -c "if [ ! -e ~/.ssh/id_rsa ]; then ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa;fi"'''
                subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            else:
                # 配置root用户公钥
                # 创建ssh公钥
                cmd = "if [ ! -e ~/.ssh/id_rsa ]; then ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa;fi"
                subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                for ip in asset_ip_list:
                    ip_with_port = ip.split(':')
                    asset_ip = ip_with_port[0]
                    host = Asset.objects.get(ip=asset_ip)
                    try:
                        output = ''
                        errs = ''
                        # 配置/etc/ansible/hosts文件
                        cmd = '''if [ -e %s ]; then if ( ! grep '^%s' %s ); then
                                echo %s ansible_ssh_pass="%s" >> %s;fi;fi;''' % (
                                ansible_hosts_file, ip, ansible_hosts_file, ip, host.password, ansible_hosts_file)
                        logger.info(cmd)
                        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        # 拷贝公钥至远程服务器
                        # cmd = '''sshpass -p "%s" ssh-copy-id -i ~/.ssh/id_rsa.pub "%s -p%s -o StrictHostKeyChecking=no"''' % (host.password, asset_ip, asset_port)
                        ssh_add_key_path = os.path.join(base_path, 'script', 'ssh_addkey.yml')
                        cmd = '''ansible-playbook %s -e "host=%s"''' % (ssh_add_key_path, host.ip)
                        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        if not p.stderr:
                            for line in p.stdout.readlines():
                                output += line
                        else:
                            for line in p.stderr.readlines():
                                errs += line
                        # 去掉ansible_ssh_pass
                        cmd = '''sed -i 's/^%s[[:space:]].*/%s/' %s''' % (ip, ip, ansible_hosts_file)
                        logger.info(cmd)
                        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        # 验证公钥是否配置成功
                        cmd = '''ansible all -i "%s," -m shell -a "ifconfig"''' % ip
                        logger.info(cmd)
                        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        msg = ''
                        for line in p.stdout.readlines():
                            output += line
                            msg += line
                        logger.info(u'=================验证公钥是否配置成功信息=============')
                        logger.info(msg)
                        logger.info(u'=================验证公钥是否配置成功信息=============')
                        # 公钥配置成功后修改连接为公钥连接并清空密码
                        success_msg = '%s | success' % host.ip
                        if success_msg in p.stdout.readlines():
                            host.connect_method = 'PublicKey'
                            host.password = ''
                            host.save()
                        else:
                            for line in p.stderr.readlines():
                                errs += line
                        lines = lines + output + errs
                    except Exception as e:
                        logger.info(e)

            for ip in asset_ip_list:
                ip_with_port = ip.split(':')
                asset_ip = ip_with_port[0]
                host = Asset.objects.get(ip=asset_ip)
                try:
                    output = ''
                    errs = ''
                    # 配置普通ssh用户配置公钥
                    user_add_yml_path = os.path.join(base_path, 'script', 'useradd.yml')
                    # 添加用户
                    ssh_username = Config.objects.get(name='add_ssh_user', config_key='username').config_value
                    ssh_password = Config.objects.get(name='add_ssh_user', config_key='password').config_value
                    cmd = '''ansible-playbook %s -e "host=%s user=%s new_pass=%s"''' % (
                            user_add_yml_path, host.ip, ssh_username, ssh_password)
                    logger.info(cmd)
                    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    if not p.stderr:
                        for line in p.stdout.readlines():
                            output += line
                    else:
                        for line in p.stderr.readlines():
                            errs += line
                    # 推送PublicKey
                    push_ssh_yml_path = os.path.join(base_path, 'script', 'push_ssh.yml')
                    cmd = '''ansible-playbook %s -e "host=%s"''' % (push_ssh_yml_path, host.ip)
                    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    if not p.stderr:
                        for line in p.stdout.readlines():
                            output += line
                    else:
                        for line in p.stderr.readlines():
                            errs += line
                    lines = lines + output + errs
                except Exception as e:
                    logger.info(e)
            logger.info(lines)
            data = {'rtn': '00', 'lines': lines}
            return HttpResponse(json.dumps(data))
        else:
            asset_ip = request.GET.get('asset_ip')
            data = {'asset_ip': asset_ip}
        return render(request, 'config_ssh_key.html', data)


def read_file(file_path):
    file_object = open(file_path)
    while True:
        return file_object.readlines()


@login_required
@permission_required('nova.access_monitor', raise_exception=True)
def view(request):
    res = request.GET
    if 'task_id' in res:
        task_id = request.GET['task_id']
        file_path = os.path.join(base_path, 'logs', 'task_log', task_id)
        try:
            task_name = Task.objects.get(task_id=task_id).name
            task_exec_user = Task.objects.get(task_id=task_id).execute_user
            task_logs = read_file(file_path)
            file_size = os.path.getsize(file_path)
            return render(request, 'view.html', locals())
        except Exception as e:
            logger.info(e)
            data = {'msg': str(e)}
            return render(request, 'message.html', data)
    else:
        data = {'msg': '没有task_id！'}
        return render(request, 'message.html', data)
