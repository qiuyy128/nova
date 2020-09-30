# -*- coding:utf-8 -*-

from __future__ import absolute_import
# from .celery import app
from celery import shared_task, result
import time
import datetime
from django.utils import timezone
import os
import svn.remote
import urllib2
import json
from django.http import HttpResponseRedirect, HttpResponse
from .run_script import RunCmd
from nova.models import Task, AppHost, App, Asset, AppConfig, HttpStep, HttpTest, History, HttpToken, Mail, Database, \
    Config, ServiceStep, ServiceTest, JdkBuildVersion
import logging
from celery.utils.log import get_task_logger
from celery.result import AsyncResult
import socket
import shutil
from script.mail import EMail
from django.db.models import Q
import string
from script.conn_mysql import Mysql
from script.conn_mssql import MsSQL
from script.conn_mongodb import Mongodb
import decimal
import re

import sys
import configmodule
reload(sys)
sys.setdefaultencoding('utf-8')

base_path = os.path.dirname(os.path.abspath(__name__))

config_mode = configmodule.config_mode
# Get an instance of a logger
logger = logging.getLogger("django")

if config_mode == 'Development':
    Configs = configmodule.DevelopmentConfig
if config_mode == 'Testing':
    Configs = configmodule.TestingConfig
if config_mode == 'Production':
    Configs = configmodule.ProductionConfig

SVN_CHECKOUT_NAME = Configs.SVN_CHECKOUT_NAME
svn_username = Configs.svn_username
svn_password = Configs.svn_password
NODE_SOURCE_SERVER = Configs.NODE_SOURCE_SERVER
NODE_SOURCE_STAGING_SERVER = Configs.NODE_SOURCE_STAGING_SERVER
ATTACHMENT_PATH = Configs.ATTACHMENT_PATH
NODE_NAME = Configs.NODE_NAME
FDP_RECEIVE_BASENAME = Configs.FDP_RECEIVE_BASENAME
FDP_RECEIVE_NAME = Configs.FDP_RECEIVE_NAME
STARTUP_APP_SLEEP = Configs.STARTUP_APP_SLEEP
NODE_APP_NUMBER = Configs.NODE_APP_NUMBER
NODE_ENV = Configs.NODE_ENV
JVM_MEMSize = Configs.JVM_MEMSize
JVM_XmnSize = Configs.JVM_XmnSize
PermSize = Configs.PermSize
CONFIG_FILE_PATH = Configs.CONFIG_FILE_PATH

svn_checkout_paths = os.path.join(base_path, '%s') % SVN_CHECKOUT_NAME
config_files_path = os.path.join(base_path, '%s') % CONFIG_FILE_PATH
APP_IP = socket.gethostbyname(socket.gethostname())

# 是否使用代理
enable_proxy = Configs.ENABLE_PROXY
http_proxy = {"http": Configs.HTTP_PROXY}
https_proxy = {"https": Configs.HTTP_PROXY}
CHARGE_POINT_FEE = 15


# 判断路径是否存在并创建
def create_path(path):
    if os.path.exists(path):
        pass
    else:
        os.makedirs('%s' % path)


def edit_ant_build_conf(file_name, app_name, svn_url=''):
    if not os.path.exists(file_name):
        print file_name, 'does not exists'
        exit(1)
    # app_base_name = 'tomcat-' + os.path.basename(app_name)
    # app_env_name = os.path.basename(os.path.dirname(app_name))
    # svn_url = App.objects.get(name=app_base_name, env=app_env_name).svn_url
    # 重新改为传入svn_url，因未部署时App表中没有数据
    svn_url_list = re.split('\n|;', svn_url)
    jar_names_list = []
    for i in svn_url_list:
        i = i.strip()
        jar_names_list.append(i.split('/')[-1])
    with open(file_name) as f:
        lines = f.readlines()
        biz_strings = ""
        adp_strings = ""
        frame_strings = ""
        add_jar_strings = ""
        # jar_names = sorted(os.listdir(app_name))
        jar_names = jar_names_list
        # 打包qxgl时'adp-security'需要放在'adp-sms'后面
        if 'adp-security' in jar_names:
            jar_names.remove('adp-security')
            jar_names.append('adp-security')
        # # dzpt打包时adp-bill需要放在最前面
        # if 'adp-bill' in jar_names:
        #     jar_names.remove('adp-bill')
        #     jar_names.insert(0, 'adp-bill')
        # 中税协因'adp-ws'引用了'adp-ywlc'，故'adp-ywlc'需要先打包
        if 'adp-ws' in jar_names and 'adp-ywlc' in jar_names:
            adp_wx_index = jar_names.index('adp-ws')
            adp_ywlc_index = jar_names.index('adp-ywlc')
            jar_names[adp_wx_index] = 'adp-ywlc'
            jar_names[adp_ywlc_index] = 'adp-ws'
        for jar_name in jar_names:
            if jar_name.find('biz-') == 0 or jar_name.find('mbiz-') == 0:
                add_xml_strings = """				<javac srcdir="${basedir}/%s/src/main/java" destdir="${deploy}/%s/classes" debug="true" debuglevel="lines,source" encoding="UTF-8">
					<classpath refid="project.frame"/>
					<classpath refid="project"/>
				</javac>
				<jar compress="true" update="true" destfile="${deploy}/jars/%s.jar">
					<fileset dir="${basedir}/%s/src/main/resources">
						<include name="**/*.*"/>
					</fileset>
					<fileset dir="${deploy}/%s/classes">
						<include name="**/*.*"/>
					</fileset>
				</jar>\n""" % (jar_name, jar_name, jar_name, jar_name, jar_name)
                biz_strings = biz_strings + add_xml_strings

            if os.path.exists(os.path.join(app_name, 'adp-db')):
                if jar_name == 'adp-db':
                    add_xml_strings = """				<javac srcdir="${basedir}/%s/src/main/java" destdir="${deploy}/%s/classes" debug="true" debuglevel="lines,source" encoding="UTF-8">
					<classpath refid="project.frame"/>
				</javac>
				<jar compress="true" update="true" destfile="${deploy}/jars/%s.jar">
					<fileset dir="${basedir}/%s/src/main/resources">
						<include name="**/*.*"/>
					</fileset>
					<fileset dir="${deploy}/%s/classes">
						<include name="**/*.*"/>
					</fileset>
				</jar>
				\n""" % (jar_name, jar_name, jar_name, jar_name, jar_name)
                    frame_strings = frame_strings + add_xml_strings
                if jar_name.find('adp-') == 0 and jar_name != 'adp-db':
                    add_xml_strings = """				<javac srcdir="${basedir}/%s/src/main/java" destdir="${deploy}/%s/classes" debug="true" debuglevel="lines,source" encoding="UTF-8">
					<classpath refid="project.frame"/>
					<classpath refid="project"/>
				</javac>
				<jar compress="true" update="true" destfile="${deploy}/jars/%s.jar">
					<fileset dir="${basedir}/%s/src/main/resources">
						<include name="**/**"/>
					</fileset>
					<fileset dir="${deploy}/%s/classes">
						<include name="**/*.*"/>
					</fileset>
				</jar>
				\n""" % (jar_name, jar_name, jar_name, jar_name, jar_name)
                    adp_strings = adp_strings + add_xml_strings
            else:
                if jar_name == 'adp-app':
                    add_xml_strings = """				<javac srcdir="${basedir}/%s/src/main/java" destdir="${deploy}/%s/classes" debug="true" debuglevel="lines,source" encoding="UTF-8">
					<classpath refid="project.frame"/>
				</javac>
				<jar compress="true" update="true" destfile="${deploy}/jars/%s.jar">
					<fileset dir="${basedir}/%s/src/main/resources">
						<include name="**/*.*"/>
					</fileset>
					<fileset dir="${deploy}/%s/classes">
						<include name="**/*.*"/>
					</fileset>
				</jar>
				\n""" % (jar_name, jar_name, jar_name, jar_name, jar_name)
                    frame_strings = frame_strings + add_xml_strings
                if jar_name.find('adp-') == 0 and jar_name != 'adp-app':
                    add_xml_strings = """				<javac srcdir="${basedir}/%s/src/main/java" destdir="${deploy}/%s/classes" debug="true" debuglevel="lines,source" encoding="UTF-8">
					<classpath refid="project.frame"/>
					<classpath refid="project"/>
				</javac>
				<jar compress="true" update="true" destfile="${deploy}/jars/%s.jar">
					<fileset dir="${basedir}/%s/src/main/resources">
						<include name="**/**"/>
					</fileset>
					<fileset dir="${deploy}/%s/classes">
						<include name="**/*.*"/>
					</fileset>
				</jar>
				\n""" % (jar_name, jar_name, jar_name, jar_name, jar_name)
                    adp_strings = adp_strings + add_xml_strings

            if jar_name.find('adp-') == 0 or jar_name.find('biz-') == 0 or jar_name.find('mbiz-') == 0:
                add_xml_strings = """				<mkdir dir="${deploy}/%s"/>
				<mkdir dir="${deploy}/%s/classes"/>\n""" % (jar_name, jar_name)
                add_jar_strings = add_jar_strings + add_xml_strings

        lines[104:104] = biz_strings
        lines[77:77] = adp_strings
        lines[51:51] = frame_strings
        lines[40:40] = add_jar_strings

        open(file_name, 'w').writelines(lines)
    f.close()
    fp = open(file_name, 'w')
    for line in lines:
        fp.writelines(line.replace('APP-NAME', '%s' % os.path.basename(app_name)))
    fp.close()


@shared_task
def do_start_app(app_id):
    """
    :param app_id: 应用id列表
    :return:
    """
    outs = ''
    errors = ''
    app_hosts = AppHost.objects.filter(id__in=app_id)
    task_id = do_start_app.request.id
    log_file = os.path.join(base_path, 'logs', 'task_log', task_id)
    if not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file))
    for app_host in app_hosts:
        logger.info(u'开始启动%s on %s, port: %s' % (app_host.name, app_host.ip, app_host.port))
        app_env = app_host.env
        app_name = app_host.name
        if app_name == 'mysql':
            cmd = 'service mysqld start'
        if app_name.find('fdp_') == 0:
            deploy_path = os.path.join('/u01', '%s') % app_name
            app_source_path = os.path.join(deploy_path, 'fdp-source')
            app_server_path = os.path.join(deploy_path, 'fdp_server')
            app_conf_path = os.path.join(app_source_path, 'conf')
            if app_env == 'product':
                app_source_asset = Asset.objects.get(ip=NODE_SOURCE_SERVER)
                node_app_number = 4
            if app_env == 'staging':
                app_source_asset = Asset.objects.get(ip=NODE_SOURCE_STAGING_SERVER)
                node_app_number = 2
            if app_env == 'test':
                app_source_asset = Asset.objects.get(ip=NODE_SOURCE_SERVER)
                node_app_number = 2
            # 判断release命令
            results = RunCmd(host=app_source_asset.ip, port=app_source_asset.port, username=app_source_asset.username,
                             password=app_source_asset.password).file_exist(remote_path='%s' % app_conf_path)
            if results == 'not exist':
                release_cmd = "fis3 release production -c"
            else:
                if app_env == 'product':
                    release_cmd = "fdp release production -c"
                if app_env == 'staging':
                    release_cmd = "fdp release preproduction -c"
                if app_env == 'test':
                    release_cmd = "fdp release test -c"
            if app_host.status == 'init':
                # release fdp-source
                cmd0 = "cd %s;%s;" % (app_source_path, release_cmd)
                print 'release %s on %s:' % (app_name, app_source_asset.ip), cmd0
                out, error = RunCmd(host=app_source_asset.ip, port=app_source_asset.port,
                                    username=app_source_asset.username,
                                    password=app_source_asset.password).run_command(cmd0, log_file)
                outs = outs + out
                errors = errors + error
                # install fdp_server and start fdp_server
                cmd = "cd %s;npm install;" % app_server_path
                app_asset = Asset.objects.get(ip=app_host.ip)
                print 'install npm of %s on %s:' % (app_name, app_asset.ip), cmd
                out, error = RunCmd(host=app_asset.ip, port=app_asset.port, username=app_asset.username,
                                    password=app_asset.password).run_command(cmd, log_file)
                cmd = "cd %s;pm2 start bin/www -i %d --name %s" % (app_server_path, int(node_app_number), app_name)
                outs = outs + out
                errors = errors + error
            else:
                cmd = '''pm2 list|grep '%s ';
                    if [ $? -eq 0 ]; then pm2 start %s;
                    else cd %s;pm2 start bin/www -i %d --name %s;
                    fi;''' % (app_name, app_name, app_server_path, int(node_app_number), app_name)
        if app_name.find('tomcat-') == 0:
            deploy_path = app_host.deploy_path.encode('utf-8')
            logs_path = os.path.join(deploy_path, 'logs')
            catalina_path = os.path.join(deploy_path, 'bin', 'catalina.sh')
            # 判断需要使用的jdk版本
            jdk_version = ''
            try:
                jdk_build_version = JdkBuildVersion.objects.get(app_name=app_name, env=app_env)
                jdk_version = jdk_build_version.jdk_version
                jdk_path = jdk_build_version.jdk_path
            except JdkBuildVersion.DoesNotExist:
                logger.info(u"未配置%sJDK版本，使用jdk1.6！" % app_name)
            if jdk_version:
                cmd = 'source %s;cd %s;%s start;sleep %d' % (jdk_path, logs_path, catalina_path, int(STARTUP_APP_SLEEP))
            else:
                cmd = 'cd %s;%s start;sleep %d' % (logs_path, catalina_path, int(STARTUP_APP_SLEEP))
        app_asset = Asset.objects.get(ip=app_host.ip)
        print 'Start %s on %s:' % (app_name, app_asset.ip), cmd
        out, error = RunCmd(host=app_asset.ip, port=app_asset.port, username=app_asset.username,
                            password=app_asset.password).run_command(cmd, log_file)
        outs = outs + out
        errors = errors + error
        logger.info(u'完成启动%s on %s, port: %s' % (app_host.name, app_host.ip, app_host.port))
    if errors:
        msg = u"启动失败"
    else:
        msg = u"启动成功"
    with open(log_file, 'a') as f:
        f.write(u"%s" % msg)
    return msg


@shared_task
def do_stop_app(app_id):
    """
    :param app_id: 应用id列表
    :return:
    """
    app_hosts = AppHost.objects.filter(id__in=app_id)
    task_id = do_stop_app.request.id
    log_file = os.path.join(base_path, 'logs', 'task_log', task_id)
    if not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file))
    for app_host in app_hosts:
        logger.info(u'开始停止%s on %s, port: %s' % (app_host.name, app_host.ip, app_host.port))
        app_name = app_host.name
        if app_name == 'mysql':
            cmd = 'service mysqld stop'
        if app_name.find('fdp_') == 0:
            cmd = 'pm2 stop %s' % app_name
        if app_name.find('tomcat-') == 0:
            deploy_path = app_host.deploy_path
            cmd = "ps -ef|grep %s|grep -v grep|awk '{print $2}'|xargs kill -9" % deploy_path
        app_asset = Asset.objects.get(ip=app_host.ip)
        print 'Stop %s on %s:' % (app_name, app_asset.ip), cmd
        out, error = RunCmd(host=app_asset.ip, port=app_asset.port, username=app_asset.username,
                            password=app_asset.password).run_command(cmd, log_file)
        logger.info(u'完成停止%s on %s, port: %s' % (app_host.name, app_host.ip, app_host.port))
    if error:
        msg = u'停止失败'
    else:
        msg = u'停止成功'
    with open(log_file, 'a') as f:
        f.write(u"%s" % msg)
    return msg


@shared_task()
def do_reload_app(app_id):
    """
    :param app_id: 应用id列表
    :return:
    """
    app_hosts = AppHost.objects.filter(id__in=app_id)
    outs = ''
    errors = ''
    task_id = do_reload_app.request.id
    log_file = os.path.join(base_path, 'logs', 'task_log', task_id)
    if not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file))
    for app_host in app_hosts:
        outs += u'开始重启%s on %s, port: %s\n' % (app_host.name, app_host.ip, app_host.port)
        app_name = app_host.name
        deploy_path = app_host.deploy_path
        app_env = app_host.env
        if app_name == 'mysql':
            cmd = 'service mysqld restart'
        if app_name.find('fdp_') == 0:
            cmd = 'pm2 reload %s' % app_name
        if app_name.find('tomcat-') == 0:
            # 判断需要使用的jdk版本
            jdk_version = ''
            try:
                jdk_build_version = JdkBuildVersion.objects.get(app_name=app_name, env=app_env)
                jdk_version = jdk_build_version.jdk_version
                jdk_path = jdk_build_version.jdk_path
            except JdkBuildVersion.DoesNotExist:
                logger.info(u"未配置%sJDK版本，使用jdk1.6！" % app_name)
            if jdk_version:
                cmd = "source %s;ps -ef|grep %s|grep -v grep|awk '{print $2}'|xargs kill -9;\
                    cd %slogs/;%sbin/catalina.sh start;sleep %d" % (
                    jdk_path, deploy_path, deploy_path, deploy_path, int(STARTUP_APP_SLEEP))
            else:
                cmd = "ps -ef|grep %s|grep -v grep|awk '{print $2}'|xargs kill -9;\
                    cd %slogs/;%sbin/catalina.sh start;sleep %d" % (
                    deploy_path, deploy_path, deploy_path, int(STARTUP_APP_SLEEP))
        app_asset = Asset.objects.get(ip=app_host.ip)
        out, error = RunCmd(host=app_asset.ip, port=app_asset.port, username=app_asset.username,
                            password=app_asset.password).run_command(cmd, log_file)
        if error:
            errors += error
        if out:
            outs += out
    if errors:
        msg = u'重启失败'
    else:
        msg = u'重启成功'
    with open(log_file, 'a') as f:
        f.write(u"%s" % msg)
    return msg


def checkout(app_name, app_env, svn_url, log_file=''):
    outs = ''
    errors = ''
    app_name = app_name.encode('utf-8')
    app_env = app_env.encode('utf-8')
    svn_url = svn_url.encode('utf-8')
    svn_checkout_path = os.path.join(svn_checkout_paths, app_env)
    logger.info(svn_url)
    if app_name.find('fdp_') == 0:
        app_name_compress = '%s.tar.gz' % app_name
        app_checkout_path = os.path.join(svn_checkout_path, app_name)
        app_checkout_compress_path = os.path.join(svn_checkout_path, '%s') % app_name_compress
        # svn签出版本
        logger.info('=' * 80)
        # r = svn.remote.RemoteClient(svn_url)
        # commit_revision = r.info()['commit_revision']
        # r.checkout('%s' % svn_checkout_path)

        # svn_cmd = "svn co -r %d %s --username %s --password %s --no-auth-cache --non-interactive %s" % (
        #     commit_revision, svn_url, svn_username, svn_password, app_checkout_path)
        svn_cmd = "svn co %s --username %s --password %s --no-auth-cache --non-interactive %s" % (
            svn_url, svn_username, svn_password, app_checkout_path)
        svn_out = os.popen(svn_cmd).read()
        with open(log_file, 'a') as f:
            f.write(u"请稍后,正在下载 %s\n" % svn_url)
            # print svn_out
            f.write(u"文件已经下载到 : %s\n" % app_checkout_path)
        cmd = 'cd %s;tar -zcf %s %s' % (svn_checkout_path, app_name_compress, app_name)
        out = os.popen(cmd).read()
        with open(log_file, 'a') as f:
            f.write(u"%s" % out)
        if os.path.exists(os.path.join(svn_checkout_path, app_name_compress)):
            return True
        else:
            return False
    if app_name.find('tomcat-') == 0:
        app_war_name = app_name.split('tomcat-')[1]
        app_war = '%s.war' % app_name.split('tomcat-')[1]
        app_checkout_path = os.path.join(svn_checkout_path, app_war_name)
        # checkout app
        # for i in svn_url.split(';'):
        for i in re.split('\n|;', svn_url):
            i = i.strip()
            svn_basename = os.path.basename(i)
            tomcat_checkout_path = os.path.join(app_checkout_path, svn_basename)
            svn_cmd = "svn co %s --username %s --password %s --no-auth-cache --non-interactive %s" % (
                i, svn_username, svn_password, tomcat_checkout_path)
            with open(log_file, 'a') as f:
                f.write(u"请稍后,正在下载 %s\n" % i)
                svn_out = os.popen(svn_cmd).read()
                f.write(u"文件已经下载到 : %s\n" % tomcat_checkout_path)
        # ant打包
        build_app_xml = 'build_%s.xml' % app_name.split('tomcat-')[1]
        source_xml = os.path.join(svn_checkout_paths, 'build.xml.orig')
        target_xml = os.path.join(app_checkout_path, build_app_xml)
        shutil.copy2('%s' % source_xml, '%s' % target_xml)
        edit_ant_build_conf(target_xml, app_checkout_path, svn_url)
        # 判断需要使用的jdk版本
        jdk_version = ''
        try:
            jdk_build_version = JdkBuildVersion.objects.get(app_name=app_name, env=app_env)
            jdk_version = jdk_build_version.jdk_version
            jdk_path = jdk_build_version.jdk_path
        except JdkBuildVersion.DoesNotExist:
            logger.info(u"未配置%sJDK版本，使用jdk1.6！" % app_name)
        if jdk_version:
            ant_cmd = "source /etc/profile;source %s;cd %s;ant -f %s %s -debug -l build.log" % (
                jdk_path, app_checkout_path, build_app_xml, app_name.split('tomcat-')[1])
        else:
            ant_cmd = "source /etc/profile;cd %s;ant -f %s %s -debug -l build.log" % (
                app_checkout_path, build_app_xml, app_name.split('tomcat-')[1])
        ant_out = os.popen(ant_cmd).read()
        with open(log_file, 'a') as f:
            f.write(u"%s\n" % ant_cmd)
            f.write(u"%s" % ant_out)
        app_war_ant_path = os.path.join(app_checkout_path, 'deploy', 'war', app_war)
        if os.path.exists(app_war_ant_path):
            return True
        else:
            return False


@shared_task
def do_deploy_app(app_name, app_env, tomcat_version, jdk_version, app_port, deploy_path, svn_url, app_host_ips):
    logger.info(u'部署 %s on %s, env: %s' % (app_name, app_host_ips, app_env))
    attachment_path = os.path.join(base_path, '%s') % ATTACHMENT_PATH
    deploy_path = deploy_path.encode('utf-8')
    svn_checkout_path = os.path.join(svn_checkout_paths, app_env)
    outs = ''
    errors = ''
    app_name = app_name.encode('utf-8')
    task_id = do_deploy_app.request.id
    log_file = os.path.join(base_path, 'logs', 'task_log', task_id)
    if not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file))
    # 调用checkout函数打包
    checkout_flag = checkout(app_name, app_env, svn_url, log_file)
    if not checkout_flag:
        msg = u'checkout打包失败，部署失败!'
        with open(log_file, 'a') as f:
            f.write(u"%s\n" % msg)
        return msg
    # 部署fdp-source
    if app_name.find('fdp_') == 0:
        if app_env == 'product':
            app_source_asset = Asset.objects.get(ip=NODE_SOURCE_SERVER)
        if app_env == 'staging':
            app_source_asset = Asset.objects.get(ip=NODE_SOURCE_STAGING_SERVER)
        if app_env == 'test':
            app_source_asset = Asset.objects.get(ip=NODE_SOURCE_SERVER)
        app_name_compress = '%s.tar.gz' % app_name
        app_checkout_path = os.path.join(svn_checkout_path, app_name)
        app_checkout_compress_path = os.path.join(svn_checkout_path, '%s') % app_name_compress

        remote_path = os.path.join(deploy_path, '%s') % app_name_compress
        # 上传app压缩包
        RunCmd(host=app_source_asset.ip, port=app_source_asset.port, username=app_source_asset.username,
               password=app_source_asset.password).upload_file(app_checkout_compress_path, remote_path, log_file)
        # 安装fdp-source
        cmd = "cd %s;tar -zxf %s;ln -s %s fdp-source;rm -f %s;" % (
            deploy_path, app_name_compress, app_name, app_name_compress)
        out, error = RunCmd(host=app_source_asset.ip, port=app_source_asset.port, username=app_source_asset.username,
                            password=app_source_asset.password).run_command(cmd, log_file)
        outs = outs + out
        errors = errors + error
    # 部署app
    for app_host_ip in app_host_ips:
        app_asset = Asset.objects.get(ip=app_host_ip)
        host_port = app_asset.port
        password = app_asset.password
        host_ip = app_asset.ip
        if app_name == 'mysql':
            print 'Deploy mysql has not config...'
        if app_name.find('fdp_') == 0:
            # 新建部署路径
            RunCmd(host=app_host_ip, port=host_port, username='root', password=password).file_exist(
                remote_path='%s' % deploy_path)
            # 判断是否安装node
            results = RunCmd(host=app_host_ip, port=host_port, username='root', password=password).file_exist(
                remote_path='/usr/local/node')
            if results == 'not exist':
                # 安装node
                node_local_path = os.path.join(attachment_path, '%s') % NODE_NAME
                node_remote_tar_path = os.path.join('/usr/local', '%s') % NODE_NAME
                RunCmd(host=app_host_ip, port=host_port, username='root', password=password).upload_file(
                    local_path=node_local_path, remote_path=node_remote_tar_path, log_file=log_file)
                RunCmd(host=app_host_ip, port=host_port, username='root', password=password).run_command(
                    '''cd /usr/local;tar -zxf %s;rm -f %s;''' % (NODE_NAME, NODE_NAME), log_file)
                # 添加环境变量
                cmd2 = '''echo "export PATH=/usr/local/node/bin:\$PATH" > /etc/profile.d/node.sh;
                    echo "export NODE_ENV=production" >> /etc/profile.d/node.sh;source /etc/profile.d/node.sh;'''
                RunCmd(host=app_host_ip, port=host_port, username='root', password=password).run_command(cmd2, log_file)

            # 判断fdp-receiver是否安装
            remote_path = '/u01'
            fdp_receive_name = FDP_RECEIVE_NAME
            fdp_receive_local_path = os.path.join(attachment_path, '%s') % fdp_receive_name
            fdp_receive_remote_path = os.path.join(remote_path, '%s') % FDP_RECEIVE_BASENAME
            fdp_receive_remote_tar_path = os.path.join(remote_path, '%s') % fdp_receive_name
            results = RunCmd(host=app_host_ip, port=host_port, username='root', password=password).file_exist(
                remote_path='%s' % fdp_receive_remote_path)
            if results == 'not exist':
                print 'Install %s ...' % FDP_RECEIVE_BASENAME
                RunCmd(host=host_ip, port=host_port, username='root', password=password).upload_file(
                    fdp_receive_local_path, fdp_receive_remote_tar_path, log_file)
                cmd = '''cd %s;tar -zxf %s;rm -f %s;cd %s;pm2 start bin/www -i 1 --name receiver''' % (
                    remote_path, fdp_receive_name, fdp_receive_name, fdp_receive_remote_path)
                print 'Start receiver on %s:' % app_asset.ip, cmd
                out, error = RunCmd(host=app_asset.ip, port=app_asset.port, username=app_asset.username,
                                    password=app_asset.password).run_command(cmd, log_file)
                outs = outs + out
                errors = errors + error

        if app_name.find('tomcat-') == 0:
            app_path = app_name.split('tomcat-')[1]
            app_war = '%s.war' % app_name.split('tomcat-')[1]
            svn_url = svn_url.encode('utf-8')
            app_checkout_path = os.path.join(svn_checkout_path, app_path)
            if tomcat_version == 'Tomcat7':
                tomcat_name = Configs.TOMCAT_7_NAME
            if tomcat_version == 'Tomcat6':
                tomcat_name = Configs.TOMCAT_6_NAME
            if tomcat_version == 'Tomcat8':
                tomcat_name = Configs.TOMCAT_8_NAME
            tomcat_local_path = os.path.join(attachment_path, '%s') % tomcat_name
            remote_path = '/u01'
            tomcat_remote_path = os.path.join(remote_path, tomcat_name)
            # 上传tomcat
            RunCmd(host=host_ip, port=host_port, username='root', password=password).upload_file(tomcat_local_path,
                                                                                                 tomcat_remote_path,
                                                                                                 log_file)
            tomcat_app_port_1 = app_port.encode('utf-8').replace('8', '7', 1)
            tomcat_app_port_3 = app_port.encode('utf-8').replace('8', '9', 1)
            # 修改tomcat配置
            cmd2 = '''cd /u01;tar -zxf %s;sed -i -e 's/7000/%s/' -e 's/8000/%s/' -e 's/9000/%s/' \
                        -e 's/APP_NAME/%s/g' tomcat-app/conf/server.xml;\
                        sed -i -e 's/2048M/%sM/g' -e 's/-Xmn400M/%s/' -e 's/256M/%sM/g' tomcat-app/bin/catalina.sh;\
                        mv tomcat-app %s;rm -f %s''' % (
                tomcat_name, tomcat_app_port_1, app_port, tomcat_app_port_3, app_path, JVM_MEMSize, JVM_XmnSize,
                PermSize, os.path.basename(os.path.dirname(deploy_path)), tomcat_name)
            print cmd2
            out, error = RunCmd(host=app_host_ip, port=host_port, username='root', password=password).run_command(cmd2,
                                                                                                                  log_file)
            outs = outs + out
            errors = errors + error
            # install jdk.
            if jdk_version == 'JDK7':
                jdk_name = Configs.JDK_7_NAME
                jdk_base_name = Configs.JDK_7_BASENAME
                jdk_profile_name = '/etc/profile.d/java.1.7.sh'
            if jdk_version == 'JDK6':
                jdk_name = Configs.JDK_6_NAME
                jdk_base_name = Configs.JDK_6_BASENAME
                jdk_profile_name = '/etc/profile.d/java.1.6.sh'
            if jdk_version == 'JDK8':
                jdk_name = Configs.JDK_8_NAME
                jdk_base_name = Configs.JDK_8_BASENAME
                jdk_profile_name = '/etc/profile.d/java.1.8.sh'
            jdk_local_path = os.path.join(attachment_path, '%s') % jdk_name
            jdk_remote_path = os.path.join(remote_path, '%s') % jdk_base_name
            jdk_remote_tar_path = os.path.join(remote_path, '%s') % jdk_name
            # 判断jdk是否安装
            results = RunCmd(host=app_host_ip, port=host_port, username='root', password=password).file_exist(
                remote_path='%s' % jdk_remote_path)
            if results == 'not exist':
                print 'Install %s ...' % jdk_base_name
                RunCmd(host=host_ip, port=host_port, username='root', password=password).upload_file(jdk_local_path,
                                                                                                     jdk_remote_tar_path,
                                                                                                     log_file)
                cmd3 = '''cd /u01;tar -zxf %s;echo "export PATH=/u01/%s/bin:\$PATH" > %s;rm -f %s;source %s''' % (
                    jdk_name, jdk_base_name, jdk_profile_name, jdk_name, jdk_profile_name)
                print cmd3
                out, error = RunCmd(host=host_ip, port=host_port, username='root', password=password).run_command(cmd3,
                                                                                                                  log_file)
                outs = outs + out
                errors = errors + error
            app_war_ant_path = os.path.join(app_checkout_path, 'deploy', 'war', app_war)
            remote_path = os.path.join(deploy_path, 'webapps', app_war)
            # 上传app war包至服务器
            RunCmd(host=app_host_ip, port=host_port, username='root', password=password).upload_file(app_war_ant_path,
                                                                                                     remote_path,
                                                                                                     log_file)
    # 删除app本次压缩包
    if app_name.find('fdp_') == 0:
        os.chdir(svn_checkout_path)
        os.remove('%s' % app_name_compress)
    if errors:
        # print 'error is:'
        # print errors
        msg = u'部署失败'
    else:
        # print 'out is:'
        # print outs
        msg = u'部署成功'
    with open(log_file, 'a') as f:
        f.write(u"%s\n" % msg)
    return msg


@shared_task()
def do_rollback_app(app_name, app_env):
    """
    :param app_name: 应用名称
    :param app_env: 应用环境
    :return:
    """
    app_hosts = AppHost.objects.filter(name=app_name, env=app_env)
    outs = ''
    errors = ''
    task_id = do_rollback_app.request.id
    log_file = os.path.join(base_path, 'logs', 'task_log', task_id)
    if not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file))
    if app_name.find('fdp_') == 0:
        deploy_path = os.path.join('/u01', '%s') % app_name
        if app_env == 'product':
            app_source_asset = Asset.objects.get(ip=NODE_SOURCE_SERVER)
        if app_env == 'staging':
            app_source_asset = Asset.objects.get(ip=NODE_SOURCE_STAGING_SERVER)
        if app_env == 'test':
            app_source_asset = Asset.objects.get(ip=NODE_SOURCE_SERVER)
        app_source_path = os.path.join(deploy_path, 'fdp-source')
        app_source_link = os.path.join(deploy_path, '%s') % app_name
        app_source_bak = os.path.join(deploy_path, '%s.bak') % app_name
        app_server_path = os.path.join(deploy_path, 'fdp_server')
        # 判断是否存在可回滚的版本
        results = RunCmd(host=app_source_asset.ip, port=app_source_asset.port, username=app_source_asset.username,
                         password=app_source_asset.password).file_exist(remote_path='%s' % app_source_bak)
        if results == 'not exist':
            msg = u"没有可回滚的版本！"
            with open(log_file, 'a') as f:
                f.write("[%s@%s:%s] error: %s\n" % (
                    app_source_asset.username, app_source_asset.ip, app_source_asset.port, msg))
            return msg
        else:
            # 回滚
            cmd = "cd %s;rm -rf %s;mv %s %s;" % (deploy_path, app_source_link, app_source_bak, app_source_link)
            out, error = RunCmd(host=app_source_asset.ip, port=app_source_asset.port,
                                username=app_source_asset.username,
                                password=app_source_asset.password).run_command(cmd, log_file)
            if error:
                errors += error
            if out:
                outs += out
            app_conf_path = os.path.join(app_source_path, 'conf')
            results = RunCmd(host=app_source_asset.ip, port=app_source_asset.port, username=app_source_asset.username,
                             password=app_source_asset.password).file_exist(remote_path='%s' % app_conf_path)
            if results == 'not exist':
                release_cmd = "fis3 release production -c"
            else:
                if app_env == 'product':
                    release_cmd = "fdp release production -c"
                if app_env == 'staging':
                    release_cmd = "fdp release preproduction -c"
                if app_env == 'test':
                    release_cmd = "fdp release test -c"
            cmd = "cd %s;%s;" % (app_source_path, release_cmd)
            out, error = RunCmd(host=app_source_asset.ip, port=app_source_asset.port,
                                username=app_source_asset.username,
                                password=app_source_asset.password).run_command(cmd, log_file)
            outs = outs + out
            errors = errors + error
            # reload fdp_server
            cmd = "cd %s;npm update;pm2 reload %s;" % (app_server_path, app_name)
            for app_host in app_hosts:
                app_asset = Asset.objects.get(ip=app_host.ip)
                out, error = RunCmd(host=app_asset.ip, port=app_asset.port, username=app_asset.username,
                                    password=app_asset.password).run_command(cmd, log_file)
                outs = outs + out
                errors = errors
            with open(log_file, 'a') as f:
                f.write(u"更新完成！\n")
    elif app_name.find('tomcat-') == 0:
        for app_host in app_hosts:
            with open(log_file, 'a') as f:
                f.write(u"开始回滚%s on %s, port: %s\n" % (app_host.name, app_host.ip, app_host.port))
            deploy_path = app_host.deploy_path
            app_path = os.path.join(deploy_path, 'webapps', app_name.split('tomcat-')[1])
            app_unpack_path = os.path.join(deploy_path, 'webapps', app_name.split('tomcat-')[1]) + '.war'
            app_unpack_bak = os.path.join(deploy_path, 'webapps', app_name.split('tomcat-')[1]) + '.war.bak'
            app_base = os.path.join(deploy_path, 'webapps')
            app_logs = os.path.join(deploy_path, 'logs')
            app_cache = os.path.join(deploy_path, 'work', 'Catalina', 'localhost')
            app_asset = Asset.objects.get(ip=app_host.ip)
            # 判断是否存在可回滚的版本
            logger.info(app_unpack_bak)
            results = RunCmd(host=app_asset.ip, port=app_asset.port, username=app_asset.username,
                             password=app_asset.password).file_exist(remote_path='%s' % app_unpack_bak)
            if results == 'not exist':
                msg = u"没有可回滚的版本！"
                with open(log_file, 'a') as f:
                    f.write("[%s@%s:%s] error: %s\n" % (app_asset.username, app_asset.ip, app_asset.port, msg))
                return msg
            else:
                # 停止
                cmd = "ps -ef|grep %s|grep -v grep|awk '{print $2}'|xargs kill -9;" % deploy_path
                RunCmd(host=app_asset.ip, port=app_asset.port, username=app_asset.username,
                       password=app_asset.password).run_command(cmd, log_file)
                # 回滚
                cmd = "cd %s;rm -rf %s %s ROOT;mv %s %s;rm -rf %swork;" % (
                    app_base, app_unpack_path, app_path, app_unpack_bak, app_unpack_path, app_cache)
                out, error = RunCmd(host=app_asset.ip, port=app_asset.port, username=app_asset.username,
                                    password=app_asset.password).run_command(cmd, log_file)
                if error:
                    errors += error
                if out:
                    outs += out
                # 启动
                # 判断需要使用的jdk版本
                jdk_version = ''
                try:
                    jdk_build_version = JdkBuildVersion.objects.get(app_name=app_name, env=app_env)
                    jdk_version = jdk_build_version.jdk_version
                    jdk_path = jdk_build_version.jdk_path
                except JdkBuildVersion.DoesNotExist:
                    logger.info(u"未配置%sJDK版本，使用jdk1.6！" % app_name)
                if jdk_version:
                    cmd = "source %s;cd %s;%sbin/catalina.sh start;sleep %d" % (
                        jdk_path, app_logs, deploy_path, int(STARTUP_APP_SLEEP))
                else:
                    cmd = "cd %s;%sbin/catalina.sh start;sleep %d" % (app_logs, deploy_path, int(STARTUP_APP_SLEEP))
                out, error = RunCmd(host=app_asset.ip, port=app_asset.port, username=app_asset.username,
                                    password=app_asset.password).run_command(cmd, log_file)
                if error:
                    errors += error
                if out:
                    outs += out
    else:
        return u'暂不支持操作！'
    if errors:
        msg = u'回滚失败'
    else:
        msg = u'回滚成功'
    with open(log_file, 'a') as f:
        f.write(u"%s\n" % msg)
    return msg


@shared_task
def do_update_app(app_name, app_env):
    logger.info(u'更新 %s, env: %s' % (app_name, app_env))
    outs = ''
    errors = ''
    task_id = do_update_app.request.id
    log_file = os.path.join(base_path, 'logs', 'task_log', task_id)
    if not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file))
    app_name = app_name.encode('utf-8')
    app_env = app_env.encode('utf-8')
    app_hosts = AppHost.objects.filter(name=app_name, env=app_env)
    svn_checkout_path = os.path.join(svn_checkout_paths, app_env)
    svn_url = App.objects.get(name=app_name, env=app_env).svn_url
    print app_hosts.values('ip')
    if app_name.find('fdp_') == 0:
        if app_env == 'product':
            app_source_asset = Asset.objects.get(ip=NODE_SOURCE_SERVER)
        if app_env == 'staging':
            app_source_asset = Asset.objects.get(ip=NODE_SOURCE_STAGING_SERVER)
        if app_env == 'test':
            app_source_asset = Asset.objects.get(ip=NODE_SOURCE_SERVER)
        # 更新fdp-source
        app_name_compress = '%s.tar.gz' % app_name
        app_checkout_path = os.path.join(svn_checkout_path, app_name)
        app_checkout_compress_path = os.path.join(svn_checkout_path, '%s') % app_name_compress
        # svn_cmd = "svn up -r %d %s --username %s --password %s --no-auth-cache --non-interactive %s" % (
        #     commit_revision, svn_url, svn_username, svn_password, app_checkout_path)
        if os.path.exists(app_checkout_path):
            svn_cmd = "svn up --username %s --password %s --no-auth-cache --non-interactive %s" % (
                svn_username, svn_password, app_checkout_path)
        else:
            svn_cmd = "svn co %s --username %s --password %s --no-auth-cache --non-interactive %s" % (
                svn_url, svn_username, svn_password, app_checkout_path)
        print
        with open(log_file, 'a') as f:
            f.write(u"[localhost] out: 请稍后,正在更新 %s\n" % app_checkout_path)
            svn_out = os.popen(svn_cmd).read()
            f.write(u'[localhost] out: %s' % svn_out)
            f.write(u'[localhost] out: 文件已经更新到 %s\n' % app_checkout_path)
        # 替换配置文件 add on 2019-03-05
        app_configs = AppConfig.objects.filter(name=app_name, env=app_env)
        if app_configs:
            app_config_files = {}
            for app_config in app_configs:
                files = app_config.files.split(',')
                app_config_files[app_config.svn_url] = files
            for key in app_config_files:
                for filename in app_config_files[key]:
                    if key[0] == '/':
                        file_path = key[1:]
                    config_file = os.path.join(config_files_path, app_env, app_name, file_path, filename)
                    target_config_file = os.path.join(app_checkout_path, file_path, filename)
                    shutil.copy2('%s' % config_file, '%s' % target_config_file)
                    with open(log_file, 'a') as f:
                        f.write(u"[localhost] out: copy %s to %s.\n" % (config_file, target_config_file))
        # 替换配置文件 add on 2019-03-05
        cmd = 'cd %s;tar -zcf %s %s' % (svn_checkout_path, app_name_compress, app_name)
        out = os.popen(cmd).read()
        print out
        deploy_path = os.path.join('/u01', '%s') % app_name
        app_source_path = os.path.join(deploy_path, 'fdp-source')
        app_server_path = os.path.join(deploy_path, 'fdp_server')
        remote_path = os.path.join(deploy_path, '%s') % app_name_compress
        RunCmd(host=app_source_asset.ip, port=app_source_asset.port, username=app_source_asset.username,
               password=app_source_asset.password).upload_file(app_checkout_compress_path, remote_path, log_file)

        os.chdir(svn_checkout_path)
        os.remove('%s' % app_name_compress)
        app_conf_path = os.path.join(app_checkout_path, 'conf')
        if os.path.exists(app_conf_path):
            if app_env == 'product':
                release_cmd = "fdp release production -c"
            if app_env == 'staging':
                release_cmd = "fdp release preproduction -c"
            if app_env == 'test':
                release_cmd = "fdp release test -c"
            cmd2 = """cd %s;rm -rf %s.bak;mv %s %s.bak;tar -zxf %s;rm -f %s;
                rm -f %s/conf/fdp-conf-secret.js;cp -p %s.bak/conf/fdp-conf-secret.js %s/conf/;cd %s;%s;""" % (
                deploy_path, app_name, app_name, app_name, app_name_compress, app_name_compress, app_name,
                app_name, app_name, app_source_path, release_cmd)
        else:
            release_cmd = "fis3 release production -c"
            # 有特殊配置文件使用其 add on 2019-03-05
            app_configs = AppConfig.objects.filter(name=app_name, env=app_env)
            if app_configs:
                cmd2 = """cd %s;rm -rf %s.bak;mv %s %s.bak;tar -zxf %s;rm -f %s;cd %s;%s;""" % (
                    deploy_path, app_name, app_name, app_name, app_name_compress, app_name_compress, app_source_path,
                    release_cmd)
            else:
                # 有特殊配置文件使用其 add on 2019-03-05
                cmd2 = """cd %s;rm -rf %s.bak;mv %s %s.bak;tar -zxf %s;rm -f %s;
                    rm -f %s/fdp-config-local.js %s/fis-conf.js;
                    cp -p %s.bak/fdp-config-local.js %s/;cp -p %s.bak/fis-conf.js %s/;
                    cd %s;%s;""" % (
                    deploy_path, app_name, app_name, app_name, app_name_compress, app_name_compress, app_name, app_name,
                    app_name, app_name, app_name, app_name, app_source_path, release_cmd)
        out, error = RunCmd(host=app_source_asset.ip, port=app_source_asset.port, username=app_source_asset.username,
                            password=app_source_asset.password).run_command(cmd2, log_file)
        outs = outs + out
        errors = errors + error
        # reload fdp_server
        cmd3 = "cd %s;npm update;pm2 reload %s;" % (app_server_path, app_name)
        print cmd3
        for app_host in app_hosts:
            app_asset = Asset.objects.get(ip=app_host.ip)
            out, error = RunCmd(host=app_asset.ip, port=app_asset.port, username=app_asset.username,
                                password=app_asset.password).run_command(cmd3, log_file)
            outs = outs + out
            errors = errors
        with open(log_file, 'a') as f:
            f.write(u"更新完成！\n")
    if app_name.find('tomcat-') == 0:
        app_path = app_name.split('tomcat-')[1]
        app_war = '%s.war' % app_name.split('tomcat-')[1]
        app_checkout_path = os.path.join(svn_checkout_path, app_path)
        # check update app
        # for i in svn_url.split(';'):
        for i in re.split('\n|;', svn_url):
            i = i.strip()
            svn_basename = os.path.basename(i)
            tomcat_checkout_path = os.path.join(app_checkout_path, svn_basename)
            if os.path.exists(tomcat_checkout_path):
                svn_cmd = "svn up --username %s --password %s --no-auth-cache --non-interactive %s" % (
                    svn_username, svn_password, tomcat_checkout_path)
            else:
                svn_cmd = "svn co %s --username %s --password %s --no-auth-cache --non-interactive %s" % (
                    i, svn_username, svn_password, tomcat_checkout_path)
            with open(log_file, 'a') as f:
                f.write(u"[localhost] out: 请稍后,正在更新 %s\n" % i)
                svn_out = os.popen(svn_cmd).read()
                f.write(u"[localhost] out: %s" % svn_out)
                f.write(u"[localhost] out: 文件已经更新到 %s\n" % tomcat_checkout_path)

        # 替换配置文件
        app_configs = AppConfig.objects.filter(name=app_name, env=app_env)
        if app_configs:
            app_config_files = {}
            for app_config in app_configs:
                files = app_config.files.split(',')
                app_config_files[app_config.svn_url] = files
            for key in app_config_files:
                for filename in app_config_files[key]:
                    config_file = os.path.join(config_files_path, app_env, app_name.split('tomcat-')[1], key, filename)
                    target_config_file = os.path.join(app_checkout_path, key, filename)
                    shutil.copy2('%s' % config_file, '%s' % target_config_file)
                    with open(log_file, 'a') as f:
                        f.write(u"[localhost] out: copy %s to %s.\n" % (config_file, target_config_file))
        # 替换配置文件
        # ant打包
        build_app_xml = 'build_%s.xml' % app_name.split('tomcat-')[1]
        source_xml = os.path.join(svn_checkout_paths, 'build.xml.orig')
        target_xml = os.path.join(app_checkout_path, build_app_xml)
        shutil.copy2('%s' % source_xml, '%s' % target_xml)
        edit_ant_build_conf(target_xml, app_checkout_path, svn_url)
        # 判断需要使用的jdk版本
        jdk_version = ''
        try:
            jdk_build_version = JdkBuildVersion.objects.get(app_name=app_name, env=app_env)
            jdk_version = jdk_build_version.jdk_version
            jdk_path = jdk_build_version.jdk_path
        except JdkBuildVersion.DoesNotExist:
            logger.info(u"未配置%sJDK版本，使用jdk1.6！" % app_name)
        if jdk_version:
            ant_cmd = "source /etc/profile;source %s;cd %s;rm -rf deploy;ant -f %s %s -debug -l build.log" % (
                jdk_path, app_checkout_path, build_app_xml, app_name.split('tomcat-')[1])
        else:
            ant_cmd = "source /etc/profile;cd %s;rm -rf deploy;ant -f %s %s -debug -l build.log" % (
                app_checkout_path, build_app_xml, app_name.split('tomcat-')[1])
        with open(log_file, 'a') as f:
            f.write(u"[localhost] out: %s.\n" % ant_cmd)
            ant_out = os.popen(ant_cmd).read()
            # ant_out = os.system(ant_cmd)
            f.write(u"[localhost] out: %s.\n" % ant_out)
        app_war_ant_path = os.path.join(app_checkout_path, 'deploy', 'war', app_war)
        if os.path.exists(app_war_ant_path):
            # 更新至服务器并重启
            for app_host in app_hosts:
                app_host_asset = Asset.objects.get(ip=app_host.ip)
                deploy_path = app_host.deploy_path
                remote_path = os.path.join(deploy_path, 'webapps', app_war)
                app_base = os.path.join(deploy_path, 'webapps')
                app_cache = os.path.join(deploy_path, 'work', 'Catalina', 'localhost')
                # 停止
                cmd1 = '''ps -ef|grep %s|grep -v grep|awk '{print $2}'|xargs kill -9;
                        cd %s;rm -f %s.bak;mv %s %s.bak;rm -rf %s ROOT;
                        rm -rf %s''' % (deploy_path, app_base, app_war, app_war, app_war, app_path, app_cache)
                RunCmd(host=app_host_asset.ip, port=app_host_asset.port, username=app_host_asset.username,
                       password=app_host_asset.password).run_command(cmd1, log_file)
                # 更新
                RunCmd(host=app_host_asset.ip, port=app_host_asset.port, username=app_host_asset.username,
                       password=app_host_asset.password).upload_file(app_war_ant_path, remote_path, log_file)
                # 启动
                logs_path = os.path.join(deploy_path, 'logs')
                catalina_path = os.path.join(deploy_path, 'bin', 'catalina.sh')
                tag = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                if jdk_version:
                    cmd2 = """source %s;cd %s;
                        if [ -e 'catalina.out' ] ;then mv catalina.out catalina.out.%s.bak;fi;%s start;sleep %d""" % (
                        jdk_path, logs_path, tag, catalina_path, int(STARTUP_APP_SLEEP))
                else:
                    cmd2 = """cd %s;
                        if [ -e 'catalina.out' ] ;then mv catalina.out catalina.out.%s.bak;fi;%s start;sleep %d""" % (
                        logs_path, tag, catalina_path, int(STARTUP_APP_SLEEP))
                out, error = RunCmd(host=app_host_asset.ip, port=app_host_asset.port, username=app_host_asset.username,
                                    password=app_host_asset.password).run_command(cmd2, log_file)
                outs = outs + out
                errors = errors + error
            with open(log_file, 'a') as f:
                f.write(u"更新完成！\n")
        else:
            with open(log_file, 'a') as f:
                f.write(u"打包失败,%s不存在,未更新应用！\n" % app_war_ant_path)
            msg = u"打包失败,%s不存在,未更新应用！\n" % app_war_ant_path
            return msg
    if errors:
        # print 'errors is:'
        # print errors
        msg = u'更新失败'
    else:
        # print 'outs is:'
        # print outs
        msg = u'更新成功'
    return msg


@shared_task
def update_task_status():
    logger = get_task_logger(__name__)
    # logger.info(u'开始 检查任务状态  ----------------->')
    pending_tasks = Task.objects.filter(status='PENDING')
    for pending_task in pending_tasks:
        logger.info('PENDING task count:' + str(pending_tasks.count()))
        task_id = pending_task.task_id
        task = Task.objects.filter(task_id=task_id)
        status = AsyncResult(id=task_id).status
        result = AsyncResult(id=task_id).result
        if status == 'SUCCESS':
            logger.info(u'任务 %s 已完成！' % task_id)
            task.update(status=status, result=result, end_time=timezone.now())
            logger.info(u'已更新任务 %s 状态为SUCCESS！' % task_id)
            task_get = Task.objects.get(task_id=task_id)
            if task_get.name.find(u'部署') == 0:
                if task_get.result == u'部署成功':
                    ips = task_get.detail.split(',')[1].split(':')[1]
                    name = task_get.detail.split(',')[0].split(':')[1]
                    port = task_get.detail.split(',')[2].split(':')[1]
                    env = task_get.detail.split(',')[3].split(':')[1]
                    path = task_get.detail.split(',')[4].split(':')[1]
                    svn_url = task_get.svn_url
                    try:
                        app = App.objects.get(name=name, env=env)
                    except App.DoesNotExist:
                        app = App.objects.create(name=name, status='init', comment=name, port=port, svn_url=svn_url,
                                                 env=env)
                    except Exception, e:
                        print str(e)
                    for ip in ips.split('&'):
                        try:
                            app_host = AppHost.objects.create(ip=ip, status='init', deploy_path=path, comment=name,
                                                              name=name, port=port, env=env)
                        except Exception, e:
                            print str(e)
                        app.app_hosts.add(app_host)
                        logger.info(u'已新增%s:应用%s on %s' % (env, name, ip))
            if task_get.name.find(u'更新') == 0:
                app_hosts = AppHost.objects.filter(id__in=task_get.app_id.split(','))
                for app_host in app_hosts:
                    if app_host.status == 'stopped' or app_host.status == 'init':
                        app_host.status = 'running'
                        app_host.save()
                        logger.info(u'已更新ip:%s,app:%s状态为running！' % (app_host.ip, app_host.name))
            if task_get.name.find(u'重启') == 0:
                pass
            if task_get.name.find(u'启动') == 0 or task_get.name.find(u'停止') == 0:
                app_ids = task_get.app_id.split(',')
                app_hosts = AppHost.objects.filter(id__in=app_ids)
                for app_host in app_hosts:
                    if app_host.status == 'stopped' or app_host.status == 'init':
                        app_host_status = 'running'
                    if app_host.status == 'running':
                        app_host_status = 'stopped'
                    app_host.status = app_host_status
                    app_host.save()
                    logger.info(u'已更新ip:%s,app:%s,port:%s 状态为 %s !' % (
                        app_host.ip, app_host.name, app_host.port, app_host_status))
        if status == 'FAILURE':
            task.update(status=status, result=result, end_time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            logger.info(u'已更新任务' + task_id + '状态为FAILURE！')
            # logger.info(u'结束 检查任务状态  ----------------->')


def get_invoice_token():
    # appKey 与 appSecret 配置
    app_url = Config.objects.get(name='ls_open_api', config_key='url').config_value
    app_key = Config.objects.get(name='ls_open_api', config_key='appKey').config_value
    app_secret = Config.objects.get(name='ls_open_api', config_key='appSecret').config_value
    # 获取token的url
    token_url = "%s?appKey=%s&appSecret=%s" % (app_url, app_key, app_secret)
    logger.info(token_url)
    proxy_support = urllib2.ProxyHandler(https_proxy)
    proxy_dis_support = urllib2.ProxyHandler({})
    # 是否配置代理
    if enable_proxy:
        opener = urllib2.build_opener(proxy_support, urllib2.HTTPHandler)
    else:
        opener = urllib2.build_opener(proxy_dis_support, urllib2.HTTPHandler)
    urllib2.install_opener(opener)
    # 获取最新的token，有效时间两个小时，有效期内不需要重新获取
    req1 = urllib2.Request(token_url)
    f1 = urllib2.urlopen(req1)
    invoice_token = f1.read()
    logger.info('*' * 60)
    logger.info(invoice_token)
    logger.info('*' * 60)
    f1.close()
    return invoice_token


@shared_task
def get_http_mon_data():
    http_steps = HttpStep.objects.all()
    for http_step in http_steps:
        url = http_step.url
        proxy_support = urllib2.ProxyHandler(https_proxy)
        proxy_dis_support = urllib2.ProxyHandler({})
        # 是否配置代理
        if enable_proxy:
            opener = urllib2.build_opener(proxy_support, urllib2.HTTPHandler)
        else:
            opener = urllib2.build_opener(proxy_dis_support, urllib2.HTTPHandler)
        # 参数
        if http_step.name == '发票查验':
            # 获取token，两小时内不需要执行获取token
            try:
                http_token = HttpToken.objects.get(name='发票查验')
                # if time.time() - http_token.last_time < 2 * 60 * 60:
                #     logger.info('token valid!')
                #     invoice_token = http_token.token
                # else:
                #     logger.info('token invalid!!!')
                #     invoice_token = json.loads(get_invoice_token())['token']
                #     HttpToken.objects.filter(name='发票查验').update(token=invoice_token, last_time=int(time.time()))
                # 先每次获取token
                logger.info('每次获取token！')
                invoice_token = json.loads(get_invoice_token())['token']
                HttpToken.objects.filter(name='发票查验').update(token=invoice_token, last_time=int(time.time()))
                # 先每次获取token
            except HttpToken.DoesNotExist:
                invoice_token = json.loads(get_invoice_token())['token']
                HttpToken.objects.create(name='发票查验', token=invoice_token, last_time=int(time.time()),
                                         comment='发票查验token')
            # post_data = {"billTime": "2017-07-25", "invoiceAmount": "9940.17", "invoiceNumber": "71463609",
            #              "token": invoice_token, "invoiceCode": "4403162130"}
            post_data = eval(str(http_step.step_field))
        else:
            if http_step.step_field:
                post_data = eval(str(http_step.step_field))
            else:
                post_data = {}
        # 提交post请求
        logger.info(json.dumps(post_data, encoding='utf-8', ensure_ascii=False))
        urllib2.install_opener(opener)
        req = urllib2.Request(url, json.dumps(post_data), {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req, timeout=int(http_step.timeout.encode('utf-8')))
        status_code = f.getcode()
        if status_code == int(http_step.status_codes):
            result = f.read()
            f.close()
            logger.info('=' * 60)
            # logger.info(result)
            logger.info('=' * 60)
            if http_step.required_item:
                result_msg = json.loads(result).get(http_step.required_item)
                if result_msg == http_step.required:
                    logger.info('SUCCESS')
                    mail_content = u"%s正常" % http_step.name
                    http_status = 200
                else:
                    logger.info('ERROR')
                    logger.info(json.loads(result))
                    mail_content = u"%s不正常,请关注！" % http_step.name
                    http_status = 100
            else:
                logger.info('SUCCESS')
                mail_content = u"%s正常" % http_step.name
                http_status = 200
        else:
            logger.info('FAILED')
            mail_content = u"%s无法使用,请关注！" % http_step.name
            http_status = 500
        try:
            History.objects.create(clock=int(time.time()), value=http_status, item_id=http_step.item_id)
            try:
                http_test = HttpTest.objects.get(item_id=http_step.item_id)
            except HttpTest.DoesNotExist:
                HttpTest.objects.create(name=http_step.name, item_id=http_step.item_id, status=0, comment=http_step.url)
            if http_test.status != http_status:
                HttpTest.objects.filter(item_id=http_step.item_id).update(status=http_status,
                                                                          last_check_time=timezone.now())
            err_cnt = History.objects.filter(
                Q(clock__gte=int(time.time() - 3 * 60), value=100) | Q(clock__gte=int(time.time() - 3 * 60),
                                                                       value=500)).count()
            normal_cnt = History.objects.filter(clock__gte=int(time.time() - 3 * 60), value=200).count()
            try:
                mail_obj = Mail.objects.get(name=http_step.name)
            except Mail.DoesNotExist:
                logger.info(u"未配置%s邮件发送参数，请先配置！" % http_step.name)
            email = EMail(smtp_server=mail_obj.smtp_server, smtp_port=int(mail_obj.smtp_port), user=mail_obj.user,
                          password=mail_obj.password, receiver=mail_obj.receiver)
            if err_cnt >= 3:
                if mail_obj.is_mail == 'Y':
                    logger.info('%s have mailed!' % http_step.name)
                else:
                    content = """Deal all,
                            %s""" % mail_content
                    logger.info('Begin to mail......')
                    email.send_email(subject=mail_content, content=content)
                    Mail.objects.filter(name=http_step.name).update(is_mail='Y', content=mail_content,
                                                                    mail_time=int(time.time()))
            if normal_cnt >= 3 and mail_obj.is_mail == 'Y':
                mail_content = u"%s恢复正常！" % http_step.name
                content = """Deal all,
                        %s""" % mail_content
                logger.info('Begin to mail......')
                email.send_email(subject=mail_content, content=content)
                Mail.objects.filter(name=http_step.name).update(is_mail='N', content=u'恢复正常', mail_time=0)
        except Exception as e:
            logger.info(e)


@shared_task
def get_service_mon_data():
    # 当天年月日
    begin_time = datetime.date.today()
    end_time = begin_time + datetime.timedelta(days=string.atoi('1'))
    begin_time = begin_time.strftime('%Y-%m-%d')
    end_time = end_time.strftime('%Y-%m-%d')
    logger.info('begin_time is: %s' % begin_time)
    logger.info('end_time is: %s' % end_time)
    service_steps = ServiceStep.objects.all()
    for service_step in service_steps:
        # 连接数据库
        db_info = Database.objects.get(db_name=service_step.db_name, env=service_step.db_env)
        try:
            conn = Mysql(host=db_info.ip, port=int(db_info.port), db=db_info.db_name, user=db_info.username,
                         password=db_info.password, charset="utf8")
        except Exception as e:
            data = {'rtn': 99, 'msg': '连接数据库错误:' + str(e)}
            return HttpResponse(json.dumps(data))
        # 参数
        sql = service_step.content
        args = (begin_time, end_time, service_step.name.encode('utf-8'))
        # logger.info(sql)
        # logger.info(str(args).decode('string_escape'))
        cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(sql, args)
        # logger.info(u'查询%d条记录！' % cur_rows)
        service_result = 0
        service_detail = ''
        # logger.info(cur_list)
        for row in dict_list:
            service_result += row.get('cnt')
        for cur in cur_list:
            service_detail += cur[0] + ': ' + str(cur[1]) + ';'
        # 有错误数据存储监控历史表
        if service_result > 0:
            try:
                History.objects.create(clock=int(time.time()), value=service_result, item_id=service_step.item_id)
                try:
                    service_test = ServiceTest.objects.get(item_id=service_step.item_id)
                except ServiceTest.DoesNotExist:
                    ServiceTest.objects.create(name=service_step.name, item_id=service_step.item_id,
                                               result=service_result, comment=service_detail)
                if service_test.result != service_result:
                    ServiceTest.objects.filter(item_id=service_step.item_id).update(result=service_result,
                                                                                    comment=service_detail,
                                                                                    last_check_time=timezone.now())
            except Exception as e:
                logger.info(e)


def query_fpcy_from_mongodb(data_time, end_time, collection):
    # 查询发票查验数据
    logger.info(u'从mongodb取出数据.')
    try:
        # data_list = collection.find_one({"time": data_time}, {"_id": 0, "time": 0})
        data_list = collection.find_one({"time": {"$gte": data_time, "$lt": end_time}}, {"_id": 0, "time": 0})
        # logger.info(str(data_list).decode('string_escape'))
        logger.info(data_list['data'])
        return data_list['data']
    except Exception as e:
        logger.info(u'从mongodb查询发票查验数据异常:' + str(e))
        return None


def save_data_to_mongodb(data, data_time, collection, with_sum='N'):
    data_list = []
    if len(data) == 0:
        return None
    else:
        if type(data) == tuple:
            data = list(data)
        logger.info(u'数据库查询出来的数据:')
        logger.info(str(data).decode('string_escape'))
        for i in range(len(data)):
            if type(data[i]) == tuple:
                data[i] = list(data[i])
            if type(data[i]) == list:
                record = data[i]
                for j in range(len(record)):
                    if type(record[j]) == tuple:
                        record[j] = list(record[j])
                    if record[j] is not None and isinstance(record[j], decimal.Decimal):
                        record[j] = str(record[j])
                        if str(record[j]).find('.') == -1:
                            record[j] = int(record[j])
                        else:
                            record[j] = float(record[j])
                    if record[j] is None:
                        record[j] = ''
        if with_sum == 'Y':
            data_col_len = len(data[0])
            total = [0 for i in range(data_col_len)]
            for i in data:
                for j in range(len(i))[1:]:
                    try:
                        if i[j] != '' and i[j] is not None and str(i[j]).find('%') == -1:
                            total[j] = total[j] + i[j]
                        if str(i[j]).find('%') != -1:
                            total[j] = '-'
                    except Exception as e:
                        logger.info(e)
            total[0] = u'合计'
            data.append(total)
        # 存储数据
        logger.info(u'存储查询数据至mongodb:')
        logger.info({'data': str(data).decode('string_escape'), 'time': data_time})
        try:
            collection.insert({'data': data, 'time': data_time})
        except Exception as e:
            logger.info(e)
        # 查询数据
        try:
            data_list = collection.find_one({"time": data_time}, {"_id": 0, "time": 0})
        except Exception as e:
            logger.info(e)
        logger.info(u'从mongodb取出来的数据:')
        logger.info(str(data_list).decode('string_escape'))
        # logger.info(type(data_list))
        return data_list['data']


# 修改20180524
def save_col_to_mongodb(data, data_time, collection, with_sum='N'):
    data_list = []
    if len(data) == 0:
        return None
    else:
        if type(data) == tuple:
            data = list(data)
        logger.info(u'数据库查询出来的数据:')
        logger.info(str(data).decode('string_escape'))
        for i in range(len(data)):
            if type(data[i]) == tuple:
                data[i] = list(data[i])
            if type(data[i]) == list:
                record = data[i]
                for j in range(len(record)):
                    if type(record[j]) == tuple:
                        record[j] = list(record[j])
                    if record[j] is not None and isinstance(record[j], decimal.Decimal):
                        record[j] = str(record[j])
                        if str(record[j]).find('.') == -1:
                            record[j] = int(record[j])
                        else:
                            record[j] = float(record[j])
                    if record[j] is None:
                        record[j] = ''
            if type(data[i]) == dict:
                record = data[i]
                for (key, value) in record.items():
                    if value is not None and isinstance(value, decimal.Decimal):
                        record[key] = str(value)
                        if str(value).find('.') == -1:
                            record[key] = int(value)
                        else:
                            value = float(value)
                    if value is None:
                        record[key] = ''
        if with_sum == 'Y':
            total_dict = {}
            total_list = data[0].keys()
            for key in total_list:
                total_dict[key] = 0
            for record in data:
                # for j in range(len(i))[1:]:
                for (key, value) in record.items():
                    try:
                        # if value != '' and value is not None and str(value).find('%') == -1:
                        if value != '' and value is not None and type(value) != str and type(value) != unicode:
                            total_dict[key] += value
                        if str(value).find('%') != -1:
                            total_dict[key] = '-'
                    except Exception as e:
                        logger.info(e)
            total_dict['customerId'] = u'合计'
            data.append(total_dict)
        # 存储数据
        logger.info(u'存储查询数据至mongodb:')
        logger.info({'data': str(data).decode('string_escape'), 'time': data_time})
        try:
            collection.insert({'data': data, 'time': data_time})
        except Exception as e:
            logger.info(e)
        # 查询数据
        try:
            data_list = collection.find_one({"time": data_time}, {"_id": 0, "time": 0})
        except Exception as e:
            logger.info(e)
        logger.info(u'从mongodb取出来的数据:')
        logger.info(str(data_list).decode('string_escape'))
        # logger.info(type(data_list))
        return data_list['data']
# 修改20180524


# 查询用户的题分信息
def get_invoice_verification_fee():
    # 查询验证码-用户的题分信息
    # 是否使用代理
    enable_proxy = False  # False表示不配置代理，True表示使用代理
    http_proxy = {"http": Configs.HTTP_PROXY}
    # app_user 与 app_pass 配置
    app_user = Config.objects.get(name='chaojiying', config_key='APP_USER').config_value
    app_pass = Config.objects.get(name='chaojiying', config_key='APP_PASS').config_value
    # chaojiying 接口
    chaojiying_query_url = Config.objects.get(name=u'chaojiying', config_key='CHAOJIYING_QUERY_URL').config_value
    proxy_support = urllib2.ProxyHandler(http_proxy)
    proxy_dis_support = urllib2.ProxyHandler({})
    # 是否配置代理
    if enable_proxy:
        opener = urllib2.build_opener(proxy_support, urllib2.HTTPHandler)
    else:
        opener = urllib2.build_opener(proxy_dis_support, urllib2.HTTPHandler)
    # 参数
    query_data = {"user": app_user,
                  "pass": app_pass,
                  }
    # 提交post请求
    urllib2.install_opener(opener)
    req = urllib2.Request(chaojiying_query_url, json.dumps(query_data), {'Content-Type': 'application/json'})
    f = urllib2.urlopen(req)
    response = f.read()
    f.close()
    return response


@shared_task
def query_fpcy_every_day():
    import script.fpcy_stat_sql as fpcy_sql
    # 当天年月日
    begin_day = datetime.date.today()
    # date转datetime
    # begin_day_datetime = datetime.datetime.strptime(str(begin_day), '%Y-%m-%d')
    # 当天00:00:00转时间戳
    begin_day_seconds = time.mktime(datetime.datetime.strptime(str(begin_day), '%Y-%m-%d').timetuple())
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
    # datetime转字符串用做sql查询变量
    begin_time = begin_time.strftime('%Y-%m-%d %H:%M:%S')
    last_time = last_time.strftime('%Y-%m-%d')
    end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
    stat_day = stat_day.strftime('%Y-%m-%d')
    # date转datetime
    # begin_day_datetime = datetime.datetime.strptime(begin_time, '%Y-%m-%d %H:%M:%S')
    # last_time_datetime = datetime.datetime.strptime(last_time, '%Y-%m-%d')
    # end_day_datetime = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
    logger.info('begin_time is: %s' % begin_time)
    logger.info('last_time is: %s' % last_time)
    logger.info('end_time is: %s' % end_time)
    logger.info('stat_day is: %s' % stat_day)
    zzs_name = "%增值税%"
    # 业务库
    db_env = 'subordinate'
    # 连接数据库
    try:
        # fpcy库
        db_info = Database.objects.get(db_name='fpcy', env=db_env)
        conn = Mysql(host=db_info.ip, port=int(db_info.port), db=db_info.db_name, user=db_info.username,
                     password=db_info.password, charset="utf8")
        # charging库查询
        db_charging = Database.objects.get(db_name='charging', env=db_env)
        conn_charging = Mysql(host=db_charging.ip, port=int(db_charging.port), db=db_charging.db_name,
                              user=db_charging.username, password=db_charging.password, charset="utf8")
        # opendb库查询
        db_opendb = Database.objects.get(db_name='opendb', env=db_env)
        conn_opendb = Mysql(host=db_opendb.ip, port=int(db_opendb.port), db=db_opendb.db_name,
                            user=db_opendb.username, password=db_opendb.password, charset="utf8")
        # ls库查询
        db_ls = Database.objects.get(db_name='ls', env=db_env)
        conn_ls = Mysql(host=db_ls.ip, port=int(db_ls.port), db=db_ls.db_name,
                        user=db_ls.username, password=db_ls.password, charset="utf8")
        # 连接mongodb数据库
        info_mongo = Database.objects.get(db_name='stats', env=db_env)
        mongodb = Mongodb(host=info_mongo.ip, port=info_mongo.port, db=info_mongo.db_name, user=info_mongo.username,
                          password=info_mongo.password)
        db_mongo = mongodb.get_database()
    except Exception as e:
        data = {'rtn': 99, 'msg': u'连接数据库错误:' + str(e)}
        logger.info(json.dumps(data, encoding='utf-8', ensure_ascii=False))
    try:
        # 发票入库情况
        logger.info(u'开始执行发票查验统计:')
        logger.info('#' * 100)
        logger.info(u'发票入库情况:')
        # 先查询当日增量数据
        args = (begin_time, end_time, zzs_name, begin_time, end_time, zzs_name, begin_time, end_time)
        cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(fpcy_sql.sql_fprkqk, args)
        data_sql_fprkqk = list(cur_list)
        for j in range(len(data_sql_fprkqk)):
            if type(data_sql_fprkqk[j]) != list:
                data_sql_fprkqk[j] = list(data_sql_fprkqk[j])
        # 统计总数=当日增量数据+昨日统计数据
        collection = db_mongo['fpcy_fprkqk']
        data_sql_fprkqk_yesterday = query_fpcy_from_mongodb(last_time, end_time, collection)
        for i in range(len(data_sql_fprkqk_yesterday)):
            data_sql_fprkqk_yesterday[i][4] = 0
            data_sql_fprkqk_yesterday[i][5] = 0
            data_sql_fprkqk_yesterday[i][6] = 0
            data_sql_fprkqk_yesterday[i][7] = '-'
            for j in dict_list:
                if data_sql_fprkqk_yesterday[i][0] == j.get('cyfs'):
                    data_sql_fprkqk_yesterday[i][1] += j.get('cnt1')
                    data_sql_fprkqk_yesterday[i][2] += j.get('cnt2')
                    data_sql_fprkqk_yesterday[i][3] += j.get('cnt3')
                    data_sql_fprkqk_yesterday[i][4] = j.get('cnt1')
                    data_sql_fprkqk_yesterday[i][5] = j.get('cnt2')
                    data_sql_fprkqk_yesterday[i][6] = j.get('cnt3')
                    data_sql_fprkqk_yesterday[i][7] = str(
                        round(float(j.get('cnt1')) / float(data_sql_fprkqk_yesterday[i][1]) * 100, 2)) + '%'
        # 计算合计
        # 删除昨日合计
        data_sql_fprkqk_yesterday.pop()
        # 重新计算合计
        data_col_len = len(data_sql_fprkqk_yesterday[0])
        total = [0 for i in range(data_col_len)]
        for i in data_sql_fprkqk_yesterday:
            for j in range(len(i))[1:]:
                try:
                    if i[j] != '' and i[j] is not None and str(i[j]).find('%') == -1:
                        total[j] = total[j] + i[j]
                    if str(i[j]).find('%') != -1:
                        total[j] = '-'
                except Exception as e:
                    logger.info(e)
        total[0] = u'合计'
        data_sql_fprkqk_yesterday.append(total)
        # 重新计算合计后的百分比
        try:
            for record in data_sql_fprkqk_yesterday:
                if record[0] == '合计':
                    record[7] = str(round(float(record[4]) / float(record[1]) * 100, 2)) + '%'
        except Exception as e:
            logger.info(e)
        data_sql_fprkqk = data_sql_fprkqk_yesterday
        logger.info(data_sql_fprkqk)
        try:
            collection = db_mongo['fpcy_fprkqk']
            data_sql_fprkqk = save_data_to_mongodb(data_sql_fprkqk, stat_day, collection)
        except Exception as e:
            logger.info(e)

        # 营收情况
        logger.info(u'营收情况:')
        data_sql_ysqk = []
        # 乐税
        data_sql_ysqk_record = {}
        collection = db_mongo['fpcy_ysqk_dmfy']
        # 获取超级鹰用户的题分信息
        try:
            last_chaojiying_tifen_dic = collection.find_one({"time": last_time}, {"_id": 0, "time": 0})
            last_chaojiying_tifen = last_chaojiying_tifen_dic.get('tifen')
            logger.info(last_chaojiying_tifen_dic)
            # logger.info(type(last_chaojiying_tifen_dic))
        except Exception as e:
            print e
        current_chaojiying_data = json.loads(get_invoice_verification_fee())
        current_chaojiying_data['time'] = stat_day
        logger.info(current_chaojiying_data)
        try:
            collection.insert(current_chaojiying_data)
        except Exception as e:
            logger.info(e)
        current_chaojiying_tifen = current_chaojiying_data['tifen']
        if last_chaojiying_tifen:
            data_sql_ysqk_dmfy = round(float(last_chaojiying_tifen - current_chaojiying_tifen) / 1000.00, 2)
        else:
            data_sql_ysqk_dmfy = round(float(current_chaojiying_tifen) / 1000.00, 2)
        # 营收情况 -> 每张入库成本
        for i in data_sql_fprkqk:
            if i[0] == '乐税':
                data_fprkzs_today = i[4]
        if data_fprkzs_today == 0:
            data_sql_ysqk_mzrkcb = 0
        else:
            data_sql_ysqk_mzrkcb = round(data_sql_ysqk_dmfy / data_fprkzs_today, 2)
        data_sql_ysqk_record['cyfs'] = '乐税'
        data_sql_ysqk_record['col1'] = data_sql_ysqk_dmfy
        data_sql_ysqk_record['col2'] = data_sql_ysqk_mzrkcb
        args = (begin_time, end_time)
        logger.info(args)
        cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(fpcy_sql.sql_ysqk_jfcs, args)
        data_sql_ysqk_jfcs = cur_list[0][0]
        data_sql_ysqk_record['col3'] = data_sql_ysqk_jfcs

        data_sql_ysqk_xfds_yk = data_sql_ysqk_jfcs * 15
        data_sql_ysqk_record['col4'] = data_sql_ysqk_xfds_yk

        data_sql_ysqk_xfje_yk = data_sql_ysqk_xfds_yk / 100
        data_sql_ysqk_record['col5'] = data_sql_ysqk_xfje_yk

        # 营收情况 ->  来源计费系统（charging）
        args = (begin_time, end_time)
        cur_list, cur_desc, cur_rows, dict_list = conn_charging.exec_select(fpcy_sql.sql_ysqk_xfds_sk, args)
        data_sql_ysqk_xfds_sk = cur_list[0][0]
        data_sql_ysqk_record['col6'] = data_sql_ysqk_xfds_sk

        data_sql_ysqk_xfje = data_sql_ysqk_xfds_sk / 100
        data_sql_ysqk_record['col7'] = data_sql_ysqk_xfje

        # 营收情况 ->  充值金额（ls库）
        cur_list, cur_desc, cur_rows, dict_list = conn_ls.exec_select(fpcy_sql.sql_ysqk_czje, args)
        data_sql_ysqk_czje = str(cur_list[0][0])
        data_sql_ysqk_record['col8'] = data_sql_ysqk_czje

        data_sql_ysqk.append(data_sql_ysqk_record)
        # 百望
        data_sql_ysqk_record = {}
        data_sql_ysqk_record['cyfs'] = '百望'
        data_sql_ysqk_record['col1'] = '*'
        data_sql_ysqk_record['col2'] = '*'
        data_sql_ysqk.append(data_sql_ysqk_record)
        # 合计
        data_sql_ysqk_record = {}
        data_sql_ysqk_record['cyfs'] = '合计'
        data_sql_ysqk_record['col1'] = data_sql_ysqk[0]['col1']
        data_sql_ysqk_record['col2'] = data_sql_ysqk[0]['col2']
        data_sql_ysqk.append(data_sql_ysqk_record)
        logger.info(data_sql_ysqk)
        # 存储到mongodb
        try:
            collection = db_mongo['fpcy_ysqk']
            data_sql_ysqk = save_data_to_mongodb(data_sql_ysqk, stat_day, collection)
        except Exception as e:
            logger.info(e)

        # 用户充值、消费点数情况
        logger.info(u'用户充值、消费点数情况:')
        # logger.info(fpcy_sql.sql_yhcyfkqkb)
        data_sql_yhczxfdsqk = []
        args = (begin_time, end_time, begin_time, end_time, begin_time, end_time, begin_time, end_time,
                begin_time, end_time, begin_time, end_time, begin_time, end_time)
        logger.info(args)
        cur_list, cur_desc, cur_rows, dict_list = conn_charging.exec_select(fpcy_sql.sql_yhczxfdsqk_today, args)
        logger.info(u'查询%d条记录！' % cur_rows)
        sql_yhczxfdsqk_today = list(cur_list[0])
        for i in range(len(sql_yhczxfdsqk_today)):
            data_sql_yhczxfdsqk.append(int(sql_yhczxfdsqk_today[i]))
        args = (end_time, end_time, end_time, end_time, end_time, end_time, end_time)
        logger.info(args)
        cur_list, cur_desc, cur_rows, dict_list = conn_charging.exec_select(fpcy_sql.sql_yhczxfdsqk_sum, args)
        logger.info(u'查询%d条记录！' % cur_rows)
        data_sql_yhczxfdsqk_sum = list(cur_list[0])
        logger.info(data_sql_yhczxfdsqk_sum)
        for j in range(len(data_sql_yhczxfdsqk_sum)):
            data_sql_yhczxfdsqk.append(int(data_sql_yhczxfdsqk_sum[j]))
        cur_list, cur_desc, cur_rows, dict_list = conn_charging.exec_select(fpcy_sql.sql_yhczxfdsqk_balance_sum)
        logger.info(u'查询%d条记录！' % cur_rows)
        data_sql_yhczxfdsqk.append(int(cur_list[0][0]))
        try:
            collection = db_mongo['fpcy_yhczxfdsqk']
            data_sql_yhczxfdsqk = save_data_to_mongodb(data_sql_yhczxfdsqk, stat_day, collection)
        except Exception as e:
            logger.info(e)
            # logger.info(data_sql_yhczxfdsqk)

        logger.info(u'用户查验反馈情况表:')
        # logger.info(fpcy_sql.sql_yhcyfkqkb)
        args = (begin_time, end_time, begin_time, end_time, begin_time, end_time, begin_time, end_time,
                begin_time, end_time, begin_time, end_time, begin_time, end_time, begin_time, end_time)
        logger.info(args)
        cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(fpcy_sql.sql_yhcyfkqkb, args)
        logger.info(u'查询%d条记录！' % cur_rows)
        data_sql_yhcyfkqkb = cur_list
        try:
            collection = db_mongo['fpcy_yhcyfkqk']
            data_sql_yhcyfkqkb = save_data_to_mongodb(data_sql_yhcyfkqkb, stat_day, collection)
        except Exception as e:
            logger.info(e)
        # logger.info(data_sql_yhcyfkqkb)

        args = (begin_time, end_time, begin_time, end_time, begin_time, end_time, begin_time, end_time,
                begin_time, end_time, begin_time, end_time)
        logger.info(u'子产品查验情况表:')
        # logger.info(fpcy_sql.sql_zcpcyqk)
        logger.info(args)
        cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(fpcy_sql.sql_zcpcyqk, args)
        logger.info(u'查询%d条记录！' % cur_rows)
        data_sql_zcpcyqks = list(cur_list)
        for j in range(len(data_sql_zcpcyqks)):
            if type(data_sql_zcpcyqks[j]) != list:
                data_sql_zcpcyqks[j] = list(data_sql_zcpcyqks[j])
            data_sql_zcpcyqk = data_sql_zcpcyqks[j]
            data_sql_zcpcyqk.append(data_sql_zcpcyqk[5] * CHARGE_POINT_FEE)
            # 子产品查验情况-消费点数（实扣） -> 来源计费系统（charging）
            # args = (begin_time, end_time)
            # cur_list, cur_desc, cur_rows, dict_list = conn_charging.exec_select(fpcy_sql.sql_zcpcyqk_xfdssk, args)
            if data_sql_zcpcyqk[0] == '收费web端':
                args = (begin_time, end_time, 'getInvoiceInfo')
            elif data_sql_zcpcyqk[0] == '收费微信端':
                args = (begin_time, end_time, 'getInvoiceInfoForWx')
            elif data_sql_zcpcyqk[0] == '企业接口':
                args = (begin_time, end_time, 'getInvoiceInfoForCom')
            else:
                args = ''
            if args:
                cur_list, cur_desc, cur_rows, dict_list = conn_charging.exec_select(fpcy_sql.sql_zcpcyqk_xfdssk, args)
                data_sql_zcpcyqk_xfdssk = int(cur_list[0][1])
            else:
                data_sql_zcpcyqk_xfdssk = '暂时无法统计'
            data_sql_zcpcyqk.append(data_sql_zcpcyqk_xfdssk)
        try:
            collection = db_mongo['fpcy_zcpcyqk']
            data_sql_zcpcyqks = save_data_to_mongodb(data_sql_zcpcyqks, stat_day, collection, with_sum='Y')
        except Exception as e:
            logger.info(e)
        # logger.info(data_sql_zcpcyqks)

        # 20180524修改
        args = (begin_time, end_time, begin_time, end_time, begin_time, end_time, begin_time, end_time,
                begin_time, end_time, begin_time, end_time)
        logger.info(u'企业接口查验情况:')
        # logger.info(fpcy_sql.sql_qyjkcyqk)
        logger.info(args)
        cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(fpcy_sql.sql_qyjkcyqk, args)
        logger.info(u'查询%d条记录！' % cur_rows)
        data_sql_qyjkcyqks = dict_list
        for line in data_sql_qyjkcyqks:
            # 企业接口查验情况 -> 消费点数（应扣）
            line['a10'] = line['a5'] * 15
            # 企业接口查验情况 -> 来源计费系统（charging）
            args = (begin_time, end_time, line['customerId'])
            cur_list, cur_desc, cur_rows, dict_list = conn_charging.exec_select(fpcy_sql.sql_qyjkcyqk_xfds_sk, args)
            line['a11'] = int(cur_list[0][1])
            # 企业接口查验情况 -> 企业名称（opendb）
            args = (line['customerId'],)
            cur_list, cur_desc, cur_rows, dict_list = conn_opendb.exec_select(fpcy_sql.sql_qyjkcyqk_qymc, args)
            if len(cur_list) > 0:
                line['customerId'] = line['customerId'] + '-' + cur_list[0][0] + cur_list[0][1]
        try:
            logger.info(data_sql_qyjkcyqks)
            collection = db_mongo['fpcy_qyjkcyqk']
            data_sql_qyjkcyqks = save_col_to_mongodb(data_sql_qyjkcyqks, stat_day, collection, with_sum='Y')
        except Exception as e:
            logger.info(e)
        # args = (begin_time, end_time, begin_time, end_time, begin_time, end_time, begin_time, end_time,
        #         begin_time, end_time, begin_time, end_time)
        # logger.info(u'企业接口查验情况:')
        # # logger.info(fpcy_sql.sql_qyjkcyqk)
        # logger.info(args)
        # cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(fpcy_sql.sql_qyjkcyqk, args)
        # logger.info(u'查询%d条记录！' % cur_rows)
        # data_sql_qyjkcyqks = list(cur_list)
        # for j in range(len(data_sql_qyjkcyqks)):
        #     if type(data_sql_qyjkcyqks[j]) != list:
        #         data_sql_qyjkcyqks[j] = list(data_sql_qyjkcyqks[j])
        #     data_sql_qyjkcyqk = data_sql_qyjkcyqks[j]
        #     data_sql_qyjkcyqk.append(data_sql_qyjkcyqk[5] * CHARGE_POINT_FEE)
        #     # 企业接口查验情况 -> 来源计费系统（charging）
        #     args = (begin_time, end_time, data_sql_qyjkcyqk[0])
        #     cur_list, cur_desc, cur_rows, dict_list = conn_charging.exec_select(fpcy_sql.sql_qyjkcyqk_xfds_sk, args)
        #     data_sql_qyjkcyqk.append(int(cur_list[0][1]))
        #     # 企业接口查验情况 -> 企业名称（opendb）
        #     args = (data_sql_qyjkcyqk[0],)
        #     cur_list, cur_desc, cur_rows, dict_list = conn_opendb.exec_select(fpcy_sql.sql_qyjkcyqk_qymc, args)
        #     if len(cur_list) > 0:
        #         data_sql_qyjkcyqk[0] = data_sql_qyjkcyqk[0] + '-' + cur_list[0][0] + cur_list[0][1]
        # try:
        #     collection = db_mongo['fpcy_qyjkcyqk']
        #     data_sql_qyjkcyqks = save_data_to_mongodb(data_sql_qyjkcyqks, stat_day, collection, with_sum='Y')
        # except Exception as e:
        #     logger.info(e)
        # # logger.info(data_sql_qyjkcyqks)

        args = (begin_time, end_time, begin_time, end_time, begin_time, end_time, begin_time, end_time,
                begin_time, end_time, begin_time, end_time, begin_time, end_time, begin_time, end_time,
                begin_time, end_time, begin_time, end_time)
        logger.info(u'核心服务状态表:')
        # logger.info(fpcy_sql.sql_hxfwztb)
        logger.info(args)
        cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(fpcy_sql.sql_hxfwztb, args)
        logger.info(u'查询%d条记录！' % cur_rows)
        data_sql_hxfwztbs = list(cur_list)
        for j in range(len(data_sql_hxfwztbs)):
            if type(data_sql_hxfwztbs[j]) != list:
                data_sql_hxfwztbs[j] = list(data_sql_hxfwztbs[j])
            data_sql_hxfwztb = data_sql_hxfwztbs[j]
            data_sql_hxfwztb[0] = data_sql_hxfwztb[0].split('（')[0]
        try:
            # 存储明细
            collection = db_mongo['fpcy_hxfwzt_detail']
            data_sql_hxfwztbs = save_data_to_mongodb(data_sql_hxfwztbs, stat_day, collection)
            # 存储汇总
            collection = db_mongo['fpcy_hxfwzt']
            data_sql_hxfwztbs = save_data_to_mongodb(data_sql_hxfwztbs, stat_day, collection, with_sum='Y')
        except Exception as e:
            logger.info(e)
        # logger.info(data_sql_hxfwztbs)

        args = (begin_time, end_time, begin_time, end_time, begin_time, end_time, begin_time, end_time,
                begin_time, end_time, begin_time, end_time, begin_time, end_time, begin_time, end_time,
                begin_time, end_time, begin_time, end_time, begin_time, end_time)
        logger.info(u'税局查验服务状态表:')
        # logger.info(fpcy_sql.sql_sjcyfwztb)
        logger.info(args)
        cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(fpcy_sql.sql_sjcyfwztb, args)
        logger.info(u'查询%d条记录！' % cur_rows)
        data_sql_sjcyfwztbs = list(cur_list)
        for j in range(len(data_sql_sjcyfwztbs)):
            if type(data_sql_sjcyfwztbs[j]) != list:
                data_sql_sjcyfwztbs[j] = list(data_sql_sjcyfwztbs[j])
            data_sql_sjcyfwztb = data_sql_sjcyfwztbs[j]
            # 可能出现invoiceName为空的情况，需要判断.
            if data_sql_sjcyfwztb[0] is not None:
                data_sql_sjcyfwztb[0] = data_sql_sjcyfwztb[0].split('（')[0]
            else:
                data_sql_sjcyfwztb[0] = '打码未使用'
        try:
            collection = db_mongo['fpcy_sjcyfwzt']
            data_sql_sjcyfwztbs = save_data_to_mongodb(data_sql_sjcyfwztbs, stat_day, collection, with_sum='Y')
        except Exception as e:
            logger.info(e)
        # logger.info(data_sql_sjcyfwztbs)

        args = (begin_time, end_time, begin_time, end_time, begin_time, end_time, begin_time, end_time,
                begin_time, end_time)
        logger.info(u'打码情况:')
        # logger.info(fpcy_sql.sql_dmqk)
        logger.info(args)
        cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(fpcy_sql.sql_dmqk, args)
        logger.info(u'查询%d条记录！' % cur_rows)
        data_sql_dmqks = cur_list
        try:
            collection = db_mongo['fpcy_dmqk']
            data_sql_dmqks = save_data_to_mongodb(data_sql_dmqks, stat_day, collection, with_sum='Y')
        except Exception as e:
            logger.info(e)
        # logger.info(data_sql_dmqks)

        args = (begin_time, end_time, begin_time, end_time)
        logger.info(u'税局响应情况（>60秒）:')
        # logger.info(fpcy_sql.sql_sjxyqk)
        logger.info(args)
        cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(fpcy_sql.sql_sjxyqk, args)
        logger.info(u'查询%d条记录！' % cur_rows)
        data_sql_sjxyqks = cur_list
        try:
            collection = db_mongo['fpcy_sjxyqk']
            data_sql_sjxyqks = save_data_to_mongodb(data_sql_sjxyqks, stat_day, collection)
        except Exception as e:
            logger.info(e)
        # logger.info(data_sql_sjxyqks)

        args = (begin_time, end_time)
        logger.info(u'用户查验请求详情:')
        # logger.info(fpcy_sql.sql_yhcyqqxq)
        logger.info(args)
        cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(fpcy_sql.sql_yhcyqqxq, args)
        logger.info(u'查询%d条记录！' % cur_rows)
        data_sql_yhcyqqxq = cur_list
        try:
            collection = db_mongo['fpcy_yhcyqqxq']
            data_sql_yhcyqqxq = save_data_to_mongodb(data_sql_yhcyqqxq, stat_day, collection)
        except Exception as e:
            logger.info(e)
        # logger.info(data_sql_yhcyqqxq)

        args = (begin_time, end_time)
        logger.info(u'税局查验请求详情:')
        # logger.info(fpcy_sql.sql_sjcyqqxq)
        logger.info(args)
        cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(fpcy_sql.sql_sjcyqqxq, args)
        logger.info(u'查询%d条记录！' % cur_rows)
        data_sql_sjcyqqxq = cur_list
        try:
            collection = db_mongo['fpcy_sjcyqqxq']
            data_sql_sjcyqqxq = save_data_to_mongodb(data_sql_sjcyqqxq, stat_day, collection)
        except Exception as e:
            logger.info(e)
        # logger.info(data_sql_sjcyqqxq)

        args = (begin_time, end_time, begin_time, end_time, begin_time, end_time, begin_time, end_time,
                begin_time, end_time, begin_time, end_time)
        logger.info(u'百望查验服务状态表:')
        # logger.info(fpcy_sql.sql_bwcyfwztb)
        logger.info(args)
        cur_list, cur_desc, cur_rows, dict_list = conn.exec_select(fpcy_sql.sql_bwcyfwztb, args)
        logger.info(u'查询%d条记录！' % cur_rows)
        data_sql_bwcyfwztbs = cur_list
        # 亦可以通过程序处理'（'
        # data_sql_bwcyfwztbs = list(cur_list)
        # for j in range(len(data_sql_bwcyfwztbs)):
        #     if type(data_sql_bwcyfwztbs[j]) != list:
        #         data_sql_bwcyfwztbs[j] = list(data_sql_bwcyfwztbs[j])
        #     data_sql_bwcyfwztb = data_sql_bwcyfwztbs[j]
        #     # 可能出现invoiceName为空的情况，需要判断.
        #     if data_sql_bwcyfwztb[0] is not None:
        #         data_sql_bwcyfwztb[0] = data_sql_bwcyfwztb[0].split('（')[0]
        try:
            collection = db_mongo['fpcy_bwcyfwztb']
            data_sql_bwcyfwztbs = save_data_to_mongodb(data_sql_bwcyfwztbs, stat_day, collection, with_sum='Y')
        except Exception as e:
            logger.info(e)
            # logger.info(data_sql_bwcyfwztbs)

        logger.info(u'用户账号点数情况:')
        # logger.info(fpcy_sql.sql_yhzhdsqk)
        args = ()
        cur_list, cur_desc, cur_rows, dict_list = conn_charging.exec_select(fpcy_sql.sql_yhzhdsqk, args)
        logger.info(u'查询%d条记录！' % cur_rows)
        data_sql_yhzhdsqk = list(cur_list)
        # 更新usercode为用户名称
        for j in range(len(data_sql_yhzhdsqk)):
            if type(data_sql_yhzhdsqk[j]) != list:
                data_sql_yhzhdsqk[j] = list(data_sql_yhzhdsqk[j])
            # 用户账号点数情况 -> 企业名称（opendb）
            args = (data_sql_yhzhdsqk[j][0],)
            cur_list, cur_desc, cur_rows, dict_list = conn_opendb.exec_select(fpcy_sql.sql_qyjkcyqk_qymc, args)
            if len(cur_list) > 0:
                data_sql_yhzhdsqk[j][0] = cur_list[0][0] + cur_list[0][1]
        try:
            collection = db_mongo['fpcy_yhzhdsqk']
            data_sql_yhzhdsqk = save_data_to_mongodb(data_sql_yhzhdsqk, stat_day, collection)
        except Exception as e:
            logger.info(e)
            # logger.info(data_sql_yhzhdsqk)

        # 统计完成发送邮件
        try:
            mail_obj = Mail.objects.get(name='fpcy_stat')
        except Mail.DoesNotExist:
            logger.info(u"未配置发票查验邮件发送参数，请先配置！")
        email = EMail(smtp_server=mail_obj.smtp_server, smtp_port=int(mail_obj.smtp_port), user=mail_obj.user,
                      password=mail_obj.password, receiver=mail_obj.receiver)
        mail_content = u'乐税发票查验统计分析%s至%s' % (begin_time, end_time)
        if mail_obj.is_mail == 'Y':
            stat_url = Config.objects.get(name='fpcy_stat_access', config_key='url').config_value
            stat_username = Config.objects.get(name='fpcy_stat_access', config_key='username').config_value
            stat_password = Config.objects.get(name='fpcy_stat_access', config_key='password').config_value
            content = """
Deal all,
    %s已完成，查看地址: %s
    用户名： %s
    密码： %s
                    """ % (mail_content, stat_url, stat_username, stat_password)
            logger.info('Begin to mail fpcy......')
            email.send_email(subject=mail_content, content=content)
            Mail.objects.filter(name='fpcy_stat').update(mail_time=int(time.time()))
    except Exception as e:
        data = {'rtn': 99, 'msg': u'查询错误:' + str(e)}
        logger.info(json.dumps(data, encoding='utf-8', ensure_ascii=False))


@shared_task
def ecai_sync_data():
    logger.info('*' * 100)
    logger.info(u'易财统计同步数据任务，开始时间：%s' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    import script.ecai_stat_sql as ecai_stat_sql
    try:
        # 连接查询库
        db_env = 'subordinate'
        # lemonacc库
        db_info = Database.objects.get(db_name='lemonacc', env=db_env)
        conn_lemonacc = MsSQL(host=db_info.ip, port=db_info.port, db=db_info.db_name, user=db_info.username,
                              password=db_info.password)
        # ecai库
        db_info = Database.objects.get(db_name='taxagency', env=db_env)
        conn_ecai = Mysql(host=db_info.ip, port=int(db_info.port), db=db_info.db_name, user=db_info.username,
                          password=db_info.password, charset="utf8")
        # report库
        db_info = Database.objects.get(db_name='report', env=db_env)
        conn_report = Mysql(host=db_info.ip, port=int(db_info.port), db=db_info.db_name, user=db_info.username,
                            password=db_info.password, charset="utf8")
        # 连接业务主库，写入统计原始数据，需要连接写入权限的数据库
        db_env = 'product'
        # ecai库
        db_info = Database.objects.get(db_name='taxagency', env=db_env)
        conn_ecai_prod = Mysql(host=db_info.ip, port=int(db_info.port), db=db_info.db_name, user=db_info.username,
                               password=db_info.password, charset="utf8")
    except Exception as e:
        data = {'rtn': '99', 'msg': u'连接数据库错误:' + str(e)}
        logger.info(json.dumps(data, encoding='utf-8', ensure_ascii=False))
    try:
        # 同步昨日后的增量数据
        begin_day = datetime.date.today()
        last_time = begin_day - datetime.timedelta(days=string.atoi('1'))
        last_time = last_time.strftime('%Y-%m-%d')
        logger.info('last_time is: %s' % last_time)

        # 同步ACC_VOUCHER
        args = (last_time,)
        cur_list_source, cur_desc, cur_rows, dict_list_source = conn_lemonacc.exec_select(
            ecai_stat_sql.sql_ecai_all_hdzt_lemon, args)
        logger.info(u'查询%d条记录.' % cur_rows)
        columns = [x[0] for x in cur_desc]
        sql_migrate_batch = ''
        count = 0
        for i in cur_list_source:
            query = 'SELECT * FROM ACC_VOUCHER WHERE AS_ID = %s AND P_ID = %s AND V_ID=%s'
            args = (i[0], i[1], i[2])
            cur_list_target, cur_desc, cur_rows, dict_list_target = conn_ecai.exec_select(query, args)
            # 同步新增数据
            count += 1
            i = list(i)
            i[3] = datetime.datetime.replace(i[3], microsecond=0)
            if cur_rows == 0:
                sql_migrate_part = "INSERT INTO %s (%s) VALUES (" % (
                    'acc_voucher', ', '.join(columns))
                for j in range(len(i)):
                    if j == len(i) - 1:
                        if i[j] is None:
                            sql_migrate_line_tmp = sql_migrate_part + "NULL"
                        else:
                            sql_migrate_line_tmp = sql_migrate_part + "'%s'" % i[j]
                    else:
                        if i[j] is None:
                            sql_migrate_line_tmp = sql_migrate_part + "NULL, "
                        else:
                            sql_migrate_line_tmp = sql_migrate_part + "'%s', " % i[j]
                    sql_migrate_part = sql_migrate_line_tmp
                sql_migrate_line = sql_migrate_line_tmp + ");\n"
                # sql_migrate_batch += sql_migrate_line
                # # 1000条批量同步
                # if count >= 1000:
                #     try:
                #         logger.info(u'需要同步的LEMON数据：')
                #         logger.info(sql_migrate_batch)
                #         if sql_migrate_batch != '':
                #             conn_ecai_prod.exec_non_select(sql_migrate_batch)
                #     except Exception as e:
                #         logger.info(e)
                #     sql_migrate_batch = ''
                #     count = 0
            else:
                # 删除原数据
                sql_migrate_part = "DELETE FROM ACC_VOUCHER WHERE AS_ID=%s AND P_ID=%s AND V_ID=%s;" % (
                    i[0], i[1], i[2])
                sql_migrate_part += "INSERT INTO %s (%s) VALUES (" % (
                    'acc_voucher', ', '.join(columns))
                for j in range(len(i)):
                    if j == len(i) - 1:
                        if i[j] is None:
                            sql_migrate_line_tmp = sql_migrate_part + "NULL"
                        else:
                            sql_migrate_line_tmp = sql_migrate_part + "'%s'" % i[j]
                    else:
                        if i[j] is None:
                            sql_migrate_line_tmp = sql_migrate_part + "NULL, "
                        else:
                            sql_migrate_line_tmp = sql_migrate_part + "'%s', " % i[j]
                    sql_migrate_part = sql_migrate_line_tmp
                sql_migrate_line = sql_migrate_line_tmp + ");\n"
            # 增量时修改为按每条进行同步
            if sql_migrate_line != '':
                logger.info(u'需要同步的LEMON数据：')
                logger.info(sql_migrate_line)
                conn_ecai_prod.exec_non_select(sql_migrate_line)
        # # 不足1000条的数据
        # logger.info(u'需要同步的LEMON数据：')
        # logger.info(sql_migrate_batch)
        # if sql_migrate_batch != '':
        #     conn_ecai_prod.exec_non_select(sql_migrate_batch)

        # 同步report数据
        args = (last_time, last_time)
        cur_list_source, cur_desc, cur_rows, dict_list_source = conn_report.exec_select(
            ecai_stat_sql.sql_ecai_sync_report, args)
        logger.info(u'查询%d条记录.' % cur_rows)
        columns = [x[0] for x in cur_desc]
        sql_migrate = ''
        for i in cur_list_source:
            query = 'SELECT * FROM declare_customer_declare_tax WHERE customerDeclareTaxId = %s'
            args = (i[0],)
            cur_list_target, cur_desc, cur_rows, dict_list_target = conn_ecai.exec_select(query, args)
            # 同步新增数据
            if cur_rows == 0:
                sql_migrate_part = "INSERT INTO %s (%s) VALUES (" % (
                    'declare_customer_declare_tax', ', '.join(columns))
                for j in range(len(i)):
                    if j == len(i) - 1:
                        if i[j] is None:
                            sql_migrate_line_tmp = sql_migrate_part + "NULL"
                        else:
                            sql_migrate_line_tmp = sql_migrate_part + "'%s'" % i[j]
                    else:
                        if i[j] is None:
                            sql_migrate_line_tmp = sql_migrate_part + "NULL, "
                        else:
                            sql_migrate_line_tmp = sql_migrate_part + "'%s', " % i[j]
                    sql_migrate_part = sql_migrate_line_tmp
                sql_migrate_line = sql_migrate_part + ");\n"
                sql_migrate_tmp = sql_migrate + sql_migrate_line
                sql_migrate = sql_migrate_tmp
            else:
                # 判断是否需要更新
                update_row_flag = 'N'
                for j in range(len(i)):
                    if cur_list_target[0][j] != i[j]:
                        update_row_flag = 'Y'
                if update_row_flag == 'Y':
                    # 删除原数据
                    sql_delete = "DELETE FROM declare_customer_declare_tax WHERE customerDeclareTaxId = '%s';" % i[0]
                    sql_migrate += sql_delete
                    # 插入变化的数据
                    sql_migrate_part = "INSERT INTO %s (%s) VALUES (" % (
                        'declare_customer_declare_tax', ', '.join(columns))
                    for j in range(len(i)):
                        if j == len(i) - 1:
                            if i[j] is None:
                                sql_migrate_line_tmp = sql_migrate_part + "NULL"
                            else:
                                sql_migrate_line_tmp = sql_migrate_part + "'%s'" % i[j]
                        else:
                            if i[j] is None:
                                sql_migrate_line_tmp = sql_migrate_part + "NULL, "
                            else:
                                sql_migrate_line_tmp = sql_migrate_part + "'%s', " % i[j]
                        sql_migrate_part = sql_migrate_line_tmp
                    sql_migrate_line = sql_migrate_part + ");\n"
                    sql_migrate_tmp = sql_migrate + sql_migrate_line
                    sql_migrate = sql_migrate_tmp
        logger.info(u'需要同步的report数据：')
        logger.info(sql_migrate)
        if sql_migrate != '':
            # 生产库执行
            conn_ecai_prod.exec_non_select(sql_migrate)

        # sql1 = ecai_stat_sql.sql_ecai_stat1
        # # logger.info(sql1)
        # args = ('xx%', '12%', '00%', '%测试%', '11%', '22%', '23%', '24%', '一般%', '小规模%')
        # cur_list, cur_desc, cur_rows, dict_list = conn_ecai.exec_select(sql1, args)
        # logger.info(u'查询%d条记录！' % cur_rows)
        # for i in dict_list:
        #     if i['accountSetId'] is not None:
        #         account_set_id = i['accountSetId']
        #         args = (account_set_id,)
        #         sql4 = ecai_stat_sql.sql_ecai_stat4
        #         cur_list, cur_desc, cur_rows, dict_list = conn_ecai_prod.exec_select(sql4, args)
        #         if dict_list:
        #             # logger.info(u'存在AS_ID：%s 的记录！' % account_set_id)
        #             stat_inputFirstVouTime = dict_list[0]['inputFirstVouTime']
        #             stat_updateLastVouTime = dict_list[0]['updateLastVouTime']
        #             # 修改统计原始数据
        #             args = (account_set_id,)
        #             # 柠檬云库获取某账套最早新增凭证时间
        #             sql2 = ecai_stat_sql.sql_ecai_stat2
        #             cur_list, cur_desc, cur_rows, dict_list = conn_lemonacc.exec_select(sql2, args)
        #             # logger.info(u'查询%d条记录！' % cur_rows)
        #             if dict_list and dict_list[0]['CREATED_DATE'] != stat_inputFirstVouTime:
        #                 args = (dict_list[0]['CREATED_DATE'], account_set_id)
        #                 update_sql = 'UPDATE stat_customer_detail SET inputFirstVouTime = %s WHERE accountSetId=%s'
        #                 cur_rows = conn_ecai_prod.exec_non_select(update_sql, args)
        #                 logger.info(u'修改%d行统计原始数据inputFirstVouTime of AS_ID: %s！' % (cur_rows, account_set_id))
        #
        #             # 柠檬云库获取某账套最后动账时间
        #             sql3 = ecai_stat_sql.sql_ecai_stat3
        #             args = (account_set_id,)
        #             cur_list, cur_desc, cur_rows, dict_list = conn_lemonacc.exec_select(sql3, args)
        #             # logger.info(u'查询%d条记录！' % cur_rows)
        #             if dict_list and dict_list[0]['MODIFIED_DATE'] != stat_updateLastVouTime:
        #                 args = (dict_list[0]['MODIFIED_DATE'], account_set_id)
        #                 update_sql = 'UPDATE stat_customer_detail SET updateLastVouTime = %s WHERE accountSetId=%s'
        #                 cur_rows = conn_ecai_prod.exec_non_select(update_sql, args)
        #                 logger.info(u'修改%d行统计原始数据updateLastVouTime of AS_ID: %s！' % (cur_rows, account_set_id))
        #         else:
        #             # 插入统计原始数据
        #             # 柠檬云库获取某账套最早新增凭证时间
        #             sql2 = ecai_stat_sql.sql_ecai_stat2
        #             cur_list, cur_desc, cur_rows, dict_list = conn_lemonacc.exec_select(sql2, args)
        #             # logger.info(u'查询%d条记录！' % cur_rows)
        #             if dict_list:
        #                 i['inputFirstVouTime'] = dict_list[0]['CREATED_DATE']
        #             # 柠檬云库获取某账套最后动账时间
        #             sql3 = ecai_stat_sql.sql_ecai_stat3
        #             cur_list, cur_desc, cur_rows, dict_list = conn_lemonacc.exec_select(sql3, args)
        #             # logger.info(u'查询%d条记录！' % cur_rows)
        #             if dict_list:
        #                 i['updateLastVouTime'] = dict_list[0]['MODIFIED_DATE']
        #             # 生成insert sql
        #             columns = i.keys()
        #             insert_sql_part = "INSERT INTO %s (%s) VALUES (" % ('stat_customer_detail', ', '.join(columns))
        #             for j in range(len(columns)):
        #                 if j == len(columns) - 1:
        #                     if i[columns[j]] is None:
        #                         insert_sql_line_tmp = insert_sql_part + "NULL"
        #                     else:
        #                         insert_sql_line_tmp = insert_sql_part + "'%s'" % i[columns[j]]
        #                 else:
        #                     if i[columns[j]] is None:
        #                         insert_sql_line_tmp = insert_sql_part + "NULL, "
        #                     else:
        #                         insert_sql_line_tmp = insert_sql_part + "'%s', " % i[columns[j]]
        #                 insert_sql_part = insert_sql_line_tmp
        #             insert_sql = insert_sql_part + ");\n"
        #             # 插入统计原始数据
        #             cur_rows = conn_ecai_prod.exec_non_select(insert_sql, args=())
        #             logger.info(u'新增%d行统计原始数据！AS_ID:%s' % (cur_rows, account_set_id))
        #     else:
        #         pass
        data = {'rtn': "00", 'msg': "易财统计同步数据成功！"}
        logger.info('*' * 100)
        logger.info(u'易财统计同步数据任务，结束时间:%s' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        logger.info(e)
        data = {'rtn': '99', 'msg': u'易财统计同步数据失败:' + str(e)}
    logger.info(json.dumps(data, encoding='utf-8', ensure_ascii=False))
