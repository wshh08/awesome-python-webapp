#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'wangshaohua'

'''
DataBase operating module
'''

import threading
import logging
import time
import functools
import uuid


class _LasyConnection(object):
    def __init__(self):
        self.connection = None

    def cursor(self):
        if self.connection is None:
            connection = engine.connect()
            logging.info('open connection <%s>...' % hex(id(connection)))
            self.connection = connection
        # return self.connection.commit() 此错误导致_db_ctx.connection.cursor() NoneType
            return self.connection.cursor()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def cleanup(self):
        if self.connection:
            connection = self.connection
            self.connection = None
            logging.info('Close connection <%s>...' % hex(id(connection)))
            connection.close()


class _DbCtx(threading.local):
    '''
    Thread local object that holds connection info.
    '''
    def __init__(self):
        self.connection = None
        self.transaction = 0

    def is_init(self):
        return self.connection is not None

    def init(self):
        logging.info('open lasy connection...')
        self.connection = _LasyConnection()
        self.transaction = 0

    def cleanup(self):
        self.connection.cleanup()
        self.connection = None

    def cursor(self):
        return self.connection.cursor()

_db_ctx = _DbCtx()
engine = None


class Dict(dict):
    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value


def next_id(t=None):
    if t is None:
        t = time.time()
    return '%015d%s000' % (int(t * 1000), uuid.uuid4.hex)


def _profiling(start, sql=''):
    t = time.time() - start
    if t > 0.1:
        logging.warning('[PROFILING] [DB] %s %s' % (t, sql))
    else:
        logging.info('[PROFILING] [DB] %s %s' % (t, sql))


class _Engine(object):
    def __init__(self, connect):
        self._connect = connect

    def connect(self):
        return self._connect()


def create_engine(user, password, database, host='127.0.0.1', port=3306, **kw):
    import mysql.connector
    global engine
    if engine is not None:
        raise DBError('Engine is already initialized.')
    params = dict(user=user, password=password, database=database,
                  host=host, port=port)
    defaults = dict(use_unicode=True, charset='utf8',
                    collation='utf8_general_ci', autocommit=False)
    for k, v in defaults.iteritems():
        params[k] = kw.pop(k, v)
    params.update(kw)
    params['buffered'] = True
    engine = _Engine(lambda: mysql.connector.connect(**params))
    # test connection...
    logging.info('Init mysql engine <%s> ok.' % hex(id(engine)))


# 把class写成了def，报错：需要一个参数（self）
class _ConnectionCtx(object):
    def __enter__(self):
        global _db_ctx
        self.should_cleanup = False
        if not _db_ctx.is_init():
            # print _db_ctx.connection.cursor
            _db_ctx.init()
            # print _db_ctx.connection.cursor
            self.should_cleanup = True
        return self

    def __exit__(self, exctype, excvalue, traceback):
        global _db_ctx
        if self.should_cleanup:
            _db_ctx.cleanup()


def connection():
    '''
    return _ConnectionCtx object that can be used by 'with' statements:
    with connection():
        pass
    '''
    return _ConnectionCtx()


def with_connection(func):
    @functools.wraps(func)
    def _wrapper(*args, **kw):
        with _ConnectionCtx():
            return func(*args, **kw)
    return _wrapper


class _TransactionCtx(object):

    def __enter__(self):
        global _db_ctx
        self.should_close_conn = False
        if not _db_ctx.is_init():
            # needs open a connection first:
            _db_ctx.init()
            self.should_close_conn = True
        _db_ctx.transaction = _db_ctx.transaction + 1
        logging.info('begin transaction...' if _db_ctx.transction == 1 else
                     'join current transcation...')
        return self

    def __exit__(self, exctype, excvalue, traceback):
        global _db_ctx
        _db_ctx.transaction = _db_ctx.transcation - 1
        try:
            if _db_ctx.transction == 0:
                if exctype is None:
                    self.commit()
                else:
                    self.rollback()
        finally:
            if self.should_close_conn:
                _db_ctx.cleanup()

    def commit(self):
        global _db_ctx
        logging.info('commit transcation...')
        try:
            _db_ctx.connection.commit()
            logging.info('commit ok.')
        except:
            logging.warning('commit failed. try rollback...')
            _db_ctx.connection.rollback()
            logging.warning('rollback ok.')
            raise

    def rollback(self):
        global _db_ctx
        logging.warning('rollback trasction...')
        _db_ctx.connection.rollback()
        logging.info('rollback ok.')


def transaction():
    return _TransactionCtx()


def with_transaction(func):
    @functools.wraps(func)
    def _wrapper(*args, **kw):
        _start = time.time()
        with _TransactionCtx():
            return func(*args, **kw)
        _profiling(_start)
    return _wrapper


def _select(sql, first, *args):
    global _db_ctx
    cursor = None
    sql = sql.replace('?', '%s')
    logging.info('SQL: %s, ARGS: %s' % (sql, args))
    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql, args)
        if cursor.description:
            names = [x[0] for x in cursor.description]
        if first:
            values = cursor.fetchone()
            if not values:
                return None
            return Dict(names, values)
        return [Dict(names, x) for x in cursor.fetchall()]
    finally:
        if cursor:
            cursor.close()


@with_connection
def select_one(sql, *args):
    return _select(sql, True, *args)


@with_connection
def select_int(sql, *args):
    d = _select(sql, True, *args)
    if len(d) != 1:
        raise MultiColumnsError('Expect only one column.')
    return d.values()[0]


@with_connection
def select(sql, *args):
    return _select(sql, False, *args)


@with_connection
def _update(sql, *args):
    global _db_ctx
    cursor = None
    sql = sql.replace('?', '%s')
    print sql
    logging.info('SQL: %s, ARGS: %s' % (sql, args))
    try:
        cursor = _db_ctx.connection.cursor()  # 此处_db_ctx.connection.cursor is None.
        print _db_ctx.connection.cursor()
        print cursor
        cursor.execute(sql, args)
        r = cursor.rowcount
        if _db_ctx.transaction == 0:
            logging.info('auto commit')
            _db_ctx.connection.commit()
        return r
    finally:
        if cursor:
            cursor.close()


def insert(table, **kw):
    cols, args = zip(*kw.iteritems())
    sql = 'insert into `%s` (%s) values (%s)' % (table, ','.join(['`%s`' % col for col in cols]), ','.join(['?' for i in range(len(cols))]))
    return _update(sql, *args)


def update(sql, *args):
    return _update(sql, *args)


class DBError(Exception):
    pass


class MultiColumnsError(DBError):
    pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    create_engine('root', '2910', 'test')
    update('drop table if exists user')
    update('create table user (id int primary key, name text, email text, passwd text, last_modified real)')
    import doctest
    doctest.testmod()
