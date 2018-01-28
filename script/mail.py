# -*- coding:utf-8 -*-

import os
import sys

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import base64
import logging

reload(sys)
sys.setdefaultencoding('utf8')
# Get an instance of a logger
logger = logging.getLogger("django")


class EMail:
    def __init__(self, smtp_server, smtp_port, user, password, receiver):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.user = user
        self.password = password
        self.receiver = receiver
        # self.acc = acc

    def send_email(self, subject='', content='', attachment=[]):
        msg = MIMEMultipart()
        if not isinstance(subject, unicode):
            subject = unicode(subject)
        msg["Subject"] = subject
        msg["From"] = self.user
        msg["To"] = self.receiver
        # msg["Cc"] = acc

        content = content.encode('utf-8')
        part = MIMEText(content, 'plain', 'utf-8')
        msg.attach(part)

        # xls类型附件
        file_name = attachment
        # part = MIMEText(open(file_name,'rb').read(), 'base64', 'utf-8')
        # part["Content-Type"] = 'application/octet-stream'
        # basename = os.path.basename(file_name)
        # part.add_header('Content-Disposition', 'attachment', filename=('gb2312', '', file_name))
        # msg.attach(part)

        for i in file_name:
            part = MIMEApplication(open(i, 'rb').read())
            part.add_header('Content-Disposition', 'attachment',
                            filename='=?utf-8?b?' + base64.b64encode(i.encode('UTF-8')) + '?=')
            msg.attach(part)

        # 连接smtp邮件服务器,端口默认是25
        s = smtplib.SMTP_SSL(self.smtp_server, port=self.smtp_port, timeout=30)
        # 登陆服务器
        s.login(self.user, self.password)
        # 发送邮件
        try:
            s.sendmail(self.user, self.receiver.split(','), msg.as_string())
            logger.info("Email query data %s send successfully" % file_name)
            s.close()
            for i in file_name:
                os.remove(i)
            return True
        except Exception, e:
            logger.info(e)
            return False
