# -*- coding:utf-8 -*-

from __future__ import absolute_import

import paramiko
import time
from datetime import datetime
import os
import configmodule
import socket
import logging

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
        self.__private_key = paramiko.RSAKey.from_private_key_file('/root/.ssh/id_rsa')

    def run_command(self, cmd):
        print "[%s@%s:%s] out:" % (self.__username, self.__host, self.__port)
        s = paramiko.SSHClient()
        s.load_system_host_keys()
        s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if ssh_key_password == 'private_key':
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
            result = stdout.read()
            error = stderr.read()
            s.close()
            if error:
                logger.info("[%s@%s:%s] error: " % (self.__username, self.__host, self.__port))
                logger.info(error)
            if result:
                logger.info("[%s@%s:%s] out: " % (self.__username, self.__host, self.__port))
                logger.info(result)
            return result, error

    def file_exist(self, remote_path, create=''):
        print "[%s@%s:%s] out:" % (self.__username, self.__host, self.__port)
        if self.__username == 'root':
            t = paramiko.Transport((self.__host, int(self.__port)))
            if ssh_key_password == 'private_key':
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

    def upload_file(self, local_path, remote_path):
        print "[%s@%s:%s] out:" % (self.__username, self.__host, self.__port)
        if self.__username == 'root':
            t = paramiko.Transport((self.__host, int(self.__port)))
            if ssh_key_password == 'private_key':
                t.connect(username=self.__username, pkey=self.__private_key)
            else:
                t.connect(username=self.__username, password=self.__password)
            sftp = paramiko.SFTPClient.from_transport(t)
            print '#########################################'
            print 'Begin upload file %s to %s:%s at %s ' % (
                local_path, self.__host, remote_path, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            remote_base_dir = os.path.split(remote_path)[0]
            try:
                sftp.stat(remote_base_dir)
                # print("remote base %s dir exist." % remote_base_dir)
            except IOError:
                print("remote base dir %s not exist." % remote_base_dir)
                sftp.mkdir(remote_base_dir)
            try:
                sftp.put(local_path, remote_path)
                print 'Upload file %s success to %s:%s at %s ' % (
                    local_path, self.__host, remote_path, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            except Exception as e:
                print u"上传失败!"
                logger.info(e)
            finally:
                t.close()
                print '#########################################'
                # return 'done'
