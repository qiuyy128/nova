# -*- coding:utf-8 -*-
import logging
from pymongo import MongoClient
from bson.objectid import ObjectId
# Get an instance of a logger
logger = logging.getLogger("django")


class Mongodb:
    def __init__(self, host, port, db, user, password):
        self.host = host
        self.port = port
        self.db = db
        self.user = user
        self.password = password

    def get_database(self):
        if not self.db:
            raise (NameError, "没有设置数据库信息")
        conn = MongoClient('mongodb://%s:%s@%s:%s/%s' % (self.user, self.password, self.host, self.port, self.db))
        database = conn['%s' % self.db]
        if not database:
            raise (NameError, "连接数据库失败")
        else:
            return database
