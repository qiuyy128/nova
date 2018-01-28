# -*- coding:utf-8 -*-
import pymssql
import logging
# Get an instance of a logger
logger = logging.getLogger("django")


def result_iterable(key, values):
    for row in values:
        yield dict(zip(key, row))


class MsSQL:
    def __init__(self, host, port, db, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db

    def __get_connect(self):
        if not self.db:
            raise (NameError, "没有设置数据库信息")
        self.conn = pymssql.connect(host=self.host, port=self.port, database=self.db, user=self.user, password=self.password)
        cur = self.conn.cursor()
        if not cur:
            raise (NameError, "连接数据库失败")
        else:
            return cur

    def exec_select(self, sql, args=()):
        cur = self.__get_connect()
        cur.execute(sql, args)
        cur_list = cur.fetchall()
        cur_desc = cur.description
        cur_rows = int(cur.rowcount)

        columns = [x[0] for x in cur_desc]
        dict_list = list(result_iterable(columns, cur_list))

        # 查询完毕后必须关闭连接
        cur.close()
        self.conn.close()
        return cur_list, cur_desc, cur_rows, dict_list

    def exec_non_select(self, sql, args=()):
        cur = self.__get_connect()
        try:
            cur.execute(sql, args)
            cur_rows = int(cur.rowcount)
            cur.close()
            self.conn.commit()
        except Exception, e:
            logger.info('Execute sql error:')
            logger.info(e)
            self.conn.rollback()
            raise e
        # self.conn.commit()
        self.conn.close()
        return cur_rows
