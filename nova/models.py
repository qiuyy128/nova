# -*- coding:utf-8 -*-

from django.db import models
from django.contrib.auth.models import User, Group
import hashlib
import os
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
import base64
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rsa_pub = os.path.join(BASE_DIR, 'script', 'rsa.pub')
rsa_key = os.path.join(BASE_DIR, 'script', 'rsa.key')


def _enc_(data=''):
    with open(rsa_pub, 'r') as f:
        public_key = f.read()
        rsa_key_obj = RSA.importKey(public_key)
        cipher_obj = Cipher_PKCS1_v1_5.new(rsa_key_obj)
        cipher_text = base64.b64encode(cipher_obj.encrypt(data))
        return cipher_text

# Create your models here.

ASSET_ENV = (
    (1, U'生产环境'),
    (2, U'准生产环境'),
    (3, U'测试环境')
)

ASSET_STATUS = (
    (1, u"已使用"),
    (2, u"未使用"),
    (3, u"报废")
)

ASSET_TYPE = (
    (1, u"物理机"),
    (2, u"虚拟机"),
    (3, u"交换机"),
    (4, u"路由器"),
    (5, u"防火墙"),
    (6, u"Docker"),
    (7, u"其他")
)


class AssetGroup(models.Model):
    GROUP_TYPE = (
        ('P', 'PRIVATE'),
        ('A', 'ASSET'),
    )
    name = models.CharField(max_length=80, unique=True)
    comment = models.CharField(max_length=160, blank=True, null=True)
    asset_groups = models.ManyToManyField(Group, blank=True, verbose_name=u"所属用户组")

    def __unicode__(self):
        return self.name


class Asset(models.Model):
    """
    asset modle
    """
    ip = models.CharField(unique=True, max_length=32, blank=True, null=True, verbose_name=u"主机IP")
    other_ip = models.CharField(max_length=255, blank=True, null=True, verbose_name=u"其他IP")
    hostname = models.CharField(max_length=50, verbose_name=u"主机名")
    port = models.IntegerField(blank=True, null=True, verbose_name=u"端口号")
    assetgroups = models.ManyToManyField(AssetGroup, blank=True, verbose_name=u"所属主机组")
    username = models.CharField(max_length=16, blank=True, null=True, verbose_name=u"管理用户名")
    password = models.CharField(max_length=256, blank=True, null=True, verbose_name=u"密码")
    use_default_auth = models.BooleanField(default=True, verbose_name=u"使用默认管理账号")
    mac = models.CharField(max_length=20, blank=True, null=True, verbose_name=u"MAC地址")
    remote_ip = models.CharField(max_length=16, blank=True, null=True, verbose_name=u'远控卡IP')
    brand = models.CharField(max_length=64, blank=True, null=True, verbose_name=u'硬件厂商型号')
    cpu = models.CharField(max_length=64, blank=True, null=True, verbose_name=u'CPU')
    memory = models.CharField(max_length=128, blank=True, null=True, verbose_name=u'内存')
    disk = models.CharField(max_length=1024, blank=True, null=True, verbose_name=u'硬盘')
    system_type = models.CharField(max_length=32, blank=True, null=True, verbose_name=u"系统类型")
    system_version = models.CharField(max_length=8, blank=True, null=True, verbose_name=u"系统版本号")
    system_arch = models.CharField(max_length=16, blank=True, null=True, verbose_name=u"系统平台")
    cabinet = models.CharField(max_length=32, blank=True, null=True, verbose_name=u'机柜号')
    position = models.IntegerField(blank=True, null=True, verbose_name=u'机器位置')
    number = models.CharField(max_length=32, blank=True, null=True, verbose_name=u'资产编号')
    status = models.IntegerField(choices=ASSET_STATUS, blank=True, null=True, default=1, verbose_name=u"机器状态")
    asset_type = models.IntegerField(choices=ASSET_TYPE, blank=True, null=True, verbose_name=u"主机类型")
    env = models.IntegerField(choices=ASSET_ENV, blank=True, null=True, verbose_name=u"运行环境")
    sn = models.CharField(max_length=128, blank=True, null=True, verbose_name=u"SN编号")
    date_added = models.DateTimeField(auto_now=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name=u"是否激活")
    comment = models.CharField(max_length=300, blank=True, null=True, verbose_name=u"备注")
    configs = models.CharField(max_length=128, blank=True, null=True, verbose_name=u"部署的应用")

    def __unicode__(self):
        return self.ip


class AppHost(models.Model):
    ip = models.CharField(max_length=25, blank=False, null=False, verbose_name=u"主机IP")
    name = models.CharField(max_length=25, blank=False, null=False, verbose_name=u"应用名称")
    port = models.IntegerField(blank=False, null=False, verbose_name=u"应用端口号")
    status = models.CharField(max_length=20, blank=False, null=False, verbose_name=u"运行状态")
    deploy_path = models.CharField(max_length=100, blank=True, null=True, verbose_name=u"部署路径")
    comment = models.CharField(max_length=100, blank=True, null=True, verbose_name=u"备注")
    env = models.CharField(max_length=25, blank=False, null=False, verbose_name=u"部署环境")

    def __unicode__(self):
        return '%s:%s' % (self.env, self.name)


class AppGroup(models.Model):
    name = models.CharField(max_length=40, unique=True)
    comment = models.CharField(max_length=160, blank=True, null=True)
    user_groups = models.ManyToManyField(Group, blank=True, verbose_name=u"所属用户组")

    def __unicode__(self):
        return self.name


class App(models.Model):
    name = models.CharField(max_length=30, blank=False, null=False, verbose_name=u"服务名称")
    port = models.IntegerField(blank=False, null=False, verbose_name=u"应用端口号")
    apphosts = models.ManyToManyField(AppHost, blank=True, verbose_name=u"服务节点名称")
    status = models.CharField(max_length=20, blank=False, null=False, verbose_name=u"运行状态")
    comment = models.CharField(max_length=100, blank=True, null=True, verbose_name=u"备注")
    svn_url = models.TextField(blank=True, null=True, verbose_name=u'SVN路径')
    env = models.CharField(max_length=25, blank=False, null=False, verbose_name=u"部署环境")
    appgroups = models.ManyToManyField(AppGroup, blank=True, verbose_name=u"所属应用组")

    def __unicode__(self):
        return '%s:%s' % (self.env, self.name)


class Task(models.Model):
    task_id = models.CharField(max_length=255, blank=False, null=False, verbose_name=u"任务id")
    name = models.CharField(max_length=80, blank=False, null=False, verbose_name=u"任务名称")
    status = models.CharField(max_length=40, blank=False, null=False, verbose_name=u"运行状态")
    start_time = models.DateTimeField(blank=False, null=False, verbose_name=u"开始时间")
    end_time = models.DateTimeField(blank=True, null=True, verbose_name=u"结束时间")
    result = models.CharField(max_length=1000, blank=True, null=True, verbose_name=u"结果")
    app_id = models.CharField(max_length=30, blank=True, null=True, verbose_name=u"app_id")
    svn_url = models.TextField(blank=True, null=True, verbose_name=u'SVN路径')
    detail = models.CharField(max_length=200, blank=True, null=True, verbose_name=u"任务详情")
    execute_user = models.CharField(max_length=30, blank=True, null=True, verbose_name=u"操作人")

    def __unicode__(self):
        return self.task_id


class AppConfig(models.Model):
    name = models.CharField(max_length=30, blank=False, null=False, verbose_name=u"服务名称")
    svn_url = models.CharField(max_length=200, null=True, verbose_name=u'SVN路径')
    files = models.CharField(max_length=300, blank=False, null=False, verbose_name=u"配置文件")
    env = models.CharField(max_length=25, blank=False, null=False, verbose_name=u"部署环境")

    def __unicode__(self):
        return '%s:%s %s' % (self.env, self.name, self.files)


class Sql(models.Model):
    db_name = models.CharField(max_length=30, blank=False, null=False, verbose_name=u"数据库")
    env = models.CharField(max_length=20, blank=False, null=False, verbose_name=u"环境")
    sql = models.TextField(blank=True, null=True, verbose_name=u"sql")
    start_time = models.DateTimeField(blank=False, null=False, verbose_name=u"开始时间")
    end_time = models.DateTimeField(blank=True, null=True, verbose_name=u"结束时间")
    result = models.CharField(max_length=2000, blank=True, null=True, verbose_name=u"结果")
    submit_user = models.CharField(max_length=30, blank=True, null=True, verbose_name=u"提交人")
    execute_user = models.CharField(max_length=30, blank=True, null=True, verbose_name=u"操作人")
    recovery_file = models.CharField(max_length=80, blank=True, null=True, verbose_name=u"恢复文件")

    def __unicode__(self):
        return '%s:%s' % (self.env, self.db_name)


class Database(models.Model):
    env = models.CharField(max_length=20, blank=False, null=False, verbose_name=u"环境")
    type = models.CharField(max_length=20, blank=False, null=False, verbose_name=u"数据库类型")
    ip = models.CharField(max_length=80, blank=False, null=False, verbose_name=u"ip")
    port = models.CharField(max_length=20, blank=False, null=False, verbose_name=u"端口")
    db_name = models.CharField(max_length=20, blank=False, null=False, verbose_name=u"数据库名称")
    username = models.CharField(max_length=30, blank=False, null=False, verbose_name=u"用户名")
    password = models.CharField(max_length=40, blank=False, null=False, verbose_name=u"密码")
    comment = models.CharField(max_length=40, blank=True, null=True, verbose_name=u"说明")

    def __unicode__(self):
        return '%s:%s' % (self.env, self.db_name)


class UploadFile(models.Model):
    file_name = models.CharField(max_length=30, blank=False, null=False, verbose_name=u"文件名称")
    file_type = models.CharField(max_length=30, blank=True, null=True, verbose_name=u"文件类型")
    file_path = models.CharField(max_length=200, blank=True, null=True, verbose_name=u"文件路径")
    env = models.CharField(max_length=20, blank=False, null=False, verbose_name=u"环境")
    app_name = models.CharField(max_length=64, blank=False, null=False, verbose_name=u"应用名称")
    upload_time = models.DateTimeField(blank=False, null=False, verbose_name=u"上传时间")
    result = models.CharField(max_length=100, blank=True, null=True, verbose_name=u"结果")

    def __unicode__(self):
        return self.file_name


class OssBucketApp(models.Model):
    name = models.CharField(max_length=30, blank=False, null=False, verbose_name=u"应用名称")
    env = models.CharField(max_length=20, blank=False, null=False, verbose_name=u"环境")
    comment = models.CharField(max_length=64, blank=False, null=False, verbose_name=u"说明")

    def __unicode__(self):
        return self.name


class AccessKey(models.Model):
    accessKeyID = models.CharField(max_length=30, blank=False, null=False, verbose_name=u"AccessKEY ID")
    accessKeySecret = models.CharField(max_length=200, blank=False, null=False, verbose_name=u"AccessKEY Secret")
    env = models.CharField(max_length=20, blank=False, null=False, verbose_name=u"环境")
    ossBucketName = models.CharField(max_length=64, blank=False, null=False, verbose_name=u"OSS Bucket Name")
    cname = models.CharField(max_length=100, blank=True, null=True, verbose_name=u"OSS Bucket Cname")
    ossBucketApp = models.ManyToManyField(OssBucketApp, blank=True, verbose_name=u"bucket应用名称")

    def __unicode__(self):
        return self.accessKeyID

    def save(self, *args, **kwargs):
        # self.accessKeySecret = hashlib.sha1(self.accessKeySecret + self.accessKeyID).hexdigest()
        self.accessKeySecret = _enc_(self.accessKeySecret.encode('utf-8'))
        super(AccessKey, self).save(*args, **kwargs)


class History(models.Model):
    item_id = models.BigIntegerField(blank=True, null=True, verbose_name=u"item_id")
    clock = models.BigIntegerField(blank=False, null=False, verbose_name=u"时间")
    value = models.IntegerField(blank=False, null=False, verbose_name=u"状态值")

    def __unicode__(self):
        return self.itemid


class HttpStep(models.Model):
    name = models.CharField(max_length=30, blank=False, null=False, verbose_name=u"服务名称")
    url = models.CharField(max_length=2000, blank=False, null=False, verbose_name=u"服务URL")
    timeout = models.CharField(max_length=20, blank=False, null=False, default='15s', verbose_name=u"超时时间")
    required_item = models.CharField(max_length=64, blank=True, null=True, verbose_name=u"返回项")
    required = models.CharField(max_length=64, blank=True, null=True, verbose_name=u"返回值")
    status_codes = models.CharField(max_length=100, blank=False, null=False, verbose_name=u"返回状态码")
    step_field = models.CharField(max_length=2000, blank=True, null=True, verbose_name=u"请求参数")
    post_type = models.CharField(max_length=20, blank=True, null=True, verbose_name=u"请求类型")
    item_id = models.CharField(max_length=20, blank=True, null=True, verbose_name=u"item_id")

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.item_id = int(time.time())
        super(HttpStep, self).save(*args, **kwargs)


class HttpTest(models.Model):
    name = models.CharField(max_length=50, blank=False, null=False, verbose_name=u"服务名称")
    status = models.IntegerField(blank=True, null=False, verbose_name=u"状态")
    last_check_time = models.DateTimeField(auto_now=True, null=True, verbose_name=u"上次检查时间")
    next_check_time = models.DateTimeField(auto_now=True, null=True, verbose_name=u"下次检查时间")
    comment = models.CharField(max_length=50, blank=True, null=False, verbose_name=u"说明")
    item_id = models.CharField(max_length=20, blank=False, null=False, verbose_name=u"item_id")

    def __unicode__(self):
        return self.name


class HttpToken(models.Model):
    name = models.CharField(max_length=50, blank=False, null=False, verbose_name=u"名称")
    token = models.CharField(max_length=100, blank=False, null=False, verbose_name=u"token")
    last_time = models.BigIntegerField(blank=False, null=False, verbose_name=u"获取token时间")
    comment = models.CharField(max_length=80, blank=False, null=False, verbose_name=u"说明")

    def __unicode__(self):
        return self.name


class Mail(models.Model):
    name = models.CharField(max_length=50, blank=False, null=False, verbose_name=u"名称")
    is_mail = models.CharField(max_length=80, blank=True, null=True, verbose_name=u"是否发送")
    content = models.CharField(max_length=2000, blank=True, null=True, verbose_name=u"内容")
    mail_time = models.BigIntegerField(blank=True, null=True, verbose_name=u"发送时间")
    smtp_server = models.CharField(max_length=2000, blank=True, null=True, verbose_name=u"smtp服务器")
    smtp_port = models.CharField(max_length=2000, blank=True, null=True, verbose_name=u"smtp端口")
    user = models.CharField(max_length=2000, blank=True, null=True, verbose_name=u"用户名")
    password = models.CharField(max_length=2000, blank=True, null=True, verbose_name=u"密码")
    receiver = models.CharField(max_length=2000, blank=True, null=True, verbose_name=u"接收者")

    def __unicode__(self):
        return self.name


class Config(models.Model):
    name = models.CharField(max_length=50, blank=False, null=False, verbose_name=u"名称")
    config_key = models.CharField(max_length=80, blank=True, null=True, verbose_name=u"配置参数")
    config_value = models.CharField(max_length=500, blank=True, null=True, verbose_name=u"配置参数值")
    comment = models.CharField(max_length=500, blank=True, null=True, verbose_name=u"说明")

    def __unicode__(self):
        return self.name


class ServiceStep(models.Model):
    name = models.CharField(max_length=30, blank=False, null=False, verbose_name=u"服务名称")
    content = models.CharField(max_length=2000, blank=False, null=False, verbose_name=u"服务内容")
    timeout = models.CharField(max_length=20, blank=False, null=False, default='15s', verbose_name=u"超时时间")
    required_item = models.CharField(max_length=64, blank=True, null=True, verbose_name=u"返回项")
    required = models.CharField(max_length=64, blank=True, null=True, verbose_name=u"返回值")
    status_codes = models.CharField(max_length=30, blank=True, null=True, verbose_name=u"返回状态码")
    step_field = models.CharField(max_length=2000, blank=True, null=True, verbose_name=u"请求参数")
    step_type = models.CharField(max_length=30, blank=True, null=True, verbose_name=u"请求类型")
    db_name = models.CharField(max_length=50, blank=True, null=True, verbose_name=u"数据库名称")
    db_env = models.CharField(max_length=20, blank=True, null=True, verbose_name=u"数据库环境")
    item_id = models.CharField(max_length=20, blank=True, null=True, verbose_name=u"item_id")

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.item_id = int(time.time())
        super(ServiceStep, self).save(*args, **kwargs)


class ServiceTest(models.Model):
    name = models.CharField(max_length=50, blank=False, null=False, verbose_name=u"服务名称")
    result = models.IntegerField(blank=True, null=False, verbose_name=u"服务结果")
    last_check_time = models.DateTimeField(auto_now=True, null=True, verbose_name=u"上次检查时间")
    next_check_time = models.DateTimeField(auto_now=True, null=True, verbose_name=u"下次检查时间")
    comment = models.CharField(max_length=200, blank=True, null=False, verbose_name=u"说明")
    item_id = models.CharField(max_length=20, blank=False, null=False, verbose_name=u"item_id")

    def __unicode__(self):
        return self.name


class OperationLog(models.Model):
    username = models.CharField(max_length=50, blank=False, null=False, verbose_name=u"用户名称")
    log_info = models.CharField(max_length=1000, blank=False, null=False, verbose_name=u"日志信息")
    result = models.CharField(max_length=200, null=True, verbose_name=u"操作结果")
    operation_time = models.DateTimeField(auto_now=True, null=True, verbose_name=u"操作时间")

    def __unicode__(self):
        return self.name
