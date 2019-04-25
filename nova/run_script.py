# -*- coding:utf-8 -*-

from __future__ import absolute_import

from nova.models import Asset
import paramiko
import time
from datetime import datetime
import os
import configmodule
import socket
import logging

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

APP_IP = socket.gethostbyname(socket.gethostname())

# Get an instance of a logger
logger = logging.getLogger("django")

config_mode = configmodule.config_mode
if config_mode == 'Development':
    Configs = configmodule.DevelopmentConfig
if config_mode == 'Testing':
    Configs = configmodule.TestingConfig
if config_mode == 'Production':
    Configs = configmodule.ProductionConfig
ssh_key_password = Configs.ssh_key_password


class RunCmd(object):
    PORT = 22
    USERNAME = 'root'

    def __init__(self, host, port, username, password):
        self.__host = host
        self.__port = port
        self.__username = username
        self.__password = password
        self.__connect_method = Asset.objects.get(ip=self.__host).connect_method
        self.__private_key = paramiko.RSAKey.from_private_key_file('/root/.ssh/id_rsa')

    def run_command(self, cmd, log_file=''):
        if log_file:
            with open(log_file, 'a') as f:
                f.write("[%s@%s:%s] run: %s\n" % (self.__username, self.__host, self.__port, cmd))
        s = paramiko.SSHClient()
        s.load_system_host_keys()
        s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if self.__connect_method == 'PublicKey':
            s.connect(hostname=self.__host, port=int(self.__port), username=self.__username, pkey=self.__private_key)
        else:
            s.connect(hostname=self.__host, port=int(self.__port), username=self.__username, password=self.__password)
        if self.__username != 'root':
            ssh = s.invoke_shell()
            time.sleep(0.1)
            ssh.send('su - \n')
            buff = ''
            while not buff.endswith('Password: '):
                resp = ssh.recv(9999)
                buff += resp
            ssh.send(self.__super_pwd)
            ssh.send('\n')
            buff = ''
            while not buff.endswith('# '):
                resp = ssh.recv(9999)
                buff += resp
            ssh.send(cmd)
            ssh.send('\n')
            buff = ''
            while not buff.endswith('# '):
                resp = ssh.recv(9999)
                buff += resp
            s.close()
            result = buff
            return result
        else:
            stdin, stdout, stderr = s.exec_command(cmd)
            stdout = stdout.read()
            stderr = stderr.read()
            s.close()
            if log_file:
                with open(log_file, 'a') as f:
                    if stderr:
                        try:
                            f.write("[%s@%s:%s] error: %s\n" % (self.__username, self.__host, self.__port, stderr))
                        except Exception as e:
                            logger.info(str(e))
                            logger.info(str(stderr))
                    if stdout:
                        try:
                            f.write("[%s@%s:%s] out: %s\n" % (self.__username, self.__host, self.__port, stdout))
                        except Exception as e:
                            logger.info(str(e))
                            logger.info(str(stdout))
            return stdout, stderr

    def file_exist(self, remote_path, create=''):
        print "[%s@%s:%s] out:" % (self.__username, self.__host, self.__port)
        if self.__username == 'root':
            t = paramiko.Transport((self.__host, int(self.__port)))
            if self.__connect_method == 'PublicKey':
                t.connect(username=self.__username, pkey=self.__private_key)
            else:
                t.connect(username=self.__username, password=self.__password)
            sftp = paramiko.SFTPClient.from_transport(t)
            remote_base_dir = os.path.split(remote_path)[0]
            try:
                sftp.stat(remote_path)
                result = 'exist'
            except IOError:
                result = 'not exist'
                if create == 'YES':
                    sftp.mkdir(remote_path)
                    print 'Already create remote dir %s.' % remote_path
            finally:
                t.close()
                return result

    def upload_file(self, local_path, remote_path, log_file=''):
        if self.__username == 'root':
            t = paramiko.Transport((self.__host, int(self.__port)))
            if self.__connect_method == 'PublicKey':
                t.connect(username=self.__username, pkey=self.__private_key)
            else:
                t.connect(username=self.__username, password=self.__password)
            sftp = paramiko.SFTPClient.from_transport(t)
            with open(log_file, 'a') as f:
                msg = u'Begin upload file %s to %s:%s at %s.\n' % (
                    local_path, self.__host, remote_path, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                f.write("[localhost] out: %s" % msg)
            remote_base_dir = os.path.split(remote_path)[0]
            try:
                sftp.stat(remote_base_dir)
                # print("remote base %s dir exist." % remote_base_dir)
            except IOError:
                print("remote base dir %s not exist." % remote_base_dir)
                sftp.mkdir(remote_base_dir)
            try:
                sftp.put(local_path, remote_path)
                with open(log_file, 'a') as f:
                    msg = u'Upload file success at %s.\n' % datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write("[localhost] out: %s" % msg)
            except Exception as e:
                error = u"上传失败!失败原因：\n" + str(e)
                with open(log_file, 'a') as f:
                    f.write("[localhost] out: %s" % error)
            finally:
                t.close()
                # return 'done'

    def download_file(self, remote_path, local_path):
        print "[%s@%s:%s] out:" % (self.__username, self.__host, self.__port)
        if self.__username == 'root':
            t = paramiko.Transport((self.__host, int(self.__port)))
            if self.__connect_method == 'PublicKey':
                t.connect(username=self.__username, pkey=self.__private_key)
            else:
                t.connect(username=self.__username, password=self.__password)
            sftp = paramiko.SFTPClient.from_transport(t)
            print '#########################################'
            print 'Begin download file %s:%s to %s.' % (self.__host, remote_path, local_path)
            file_name = os.path.split(remote_path)[1]
            local_file = os.path.join(local_path, file_name)
            try:
                sftp.stat(remote_path)
            except IOError:
                print("remote file %s not exist." % remote_path)

            sftp.get(remote_path, local_file)
            return local_file

            # try:
            #     sftp.get(remote_path, local_file)
            #     print 'Download file %s:% to %s success.' % (self.__host, remote_path, local_file)
            #     logger.info(u'下载成功!')
            #     return local_file
            # except Exception as e:
            #     logger.info(e)
            #     logger.info(u'下载失败!')
            #     return local_file
            # finally:
            #     t.close()
            #     print '#########################################'
