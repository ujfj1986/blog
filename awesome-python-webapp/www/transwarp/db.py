#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
db module
	use ages:
	create_engine()
	with connection() or transaction():
		select()
		...
		update()
'''

import threading, logging, functools, time, uuid
# create engine
# use ages:
#	db.create_engine(usr='root',
#		password='password',
#		database='test',
#		host='127.0.0.1', port=3306)
# return : NONE
def create_engine(usr, password, database, host='127.0.0.1', port='3306', **kw):
	import mysql.connector
	global engine
	if engine is not None:
		raise DbError('Engine is already initialized.')
	params = dict(user=usr, password=password, database=database, host=host, port=port)
	defaults = dict(use_unicode=True, charset='utf8', collation='utf8_general_ci', auto_commit=False)
	for k, v in defaults.iteritems():
		params[k] = kw.pop(k, v)
	params.update(kw)
	params['buffered'] = True
	engine = _Engine(lambda: mysql.connector.connect(**params))
	logging.info('Init mysql engine <%s> ok.' % hex(id(engine)))

# connection
# use ages:
#	db.connection()
def connection():
	return _ConnectCtx()

# with_connection
# use ages:
# 	@with_connection
#	def do_some_operation()
#		pass
# as:
#	with connection():
#		do_some_operation()
def with_connection(func):
	@functools.wraps(func)
	def _wrapper(*args, **kw):
		with connection():
			return func(args, kw)
	return _wrapper

#transaction
# use ages:
#	db.transaction()
def transaction():
	return _TransactionCtx()

#with_transaction
# use ages:
#	@with_transaction
#	def do_some_operation():
#		pass
# as:
#	with transaction():
#		do_some_operation()
def with_transaction(func):
	@functools.wraps(func)
	def _wrapper(*args, **kw):
		with transaction():
			return func(args, kw)
	return _wrapper

# create_table
def create_table(name, **colums):
	r'''use ages:
		db.create_table(name='user',
			**colums)
	'''
	pass

#remove_table
def remove_table(name):
	pass

# _select
@with_connection
def _select(sql, isOnlyOne, *args):
	''' execute select sql operation and return a dict list or None '''
	global _db_ctx
	cursor = None
	try :
		cursor = _db_ctx.engine().execute(sql, args)
		if cursor.description:
			names = [ x[0] for x in cursor.description]
		if isOnlyOne:
			values = cursor.fetchone()
			if not values:
				return None
			return dict(zip(names, values))
		return [dict(zip(names, x)) for x in cursor.fetchall()]
	finally:
		if cursor:
			cursor.close()

def select_one(sql, *args):
	return _select(sql, True, args)

# select
# use ages:
#	db.select('select * from user')
#return: a sql running resault list
def select(sql, *args):
	return _select(sql, False, args)

@with_transaction
def _update(sql, *args):
	global _db_ctx
	cursor = None
	try :
		cursor = _db_ctx.engine().execute(sql, args)
		return cursor.rowcount
	finally:
		if cursor:
			cursor.close()

# update
# execute all insert, update, and delete operation.
# use ？ as placeholder
# use ages:
#	db.update('insert into user(id, name) values (?, ?)', 4, 'Jack')
#	db.updata(table, where, sets)
def update(table, where, sets):
	where_cols, where_args = zip(*where.iteritems())
	sets_cols, sets_args = zip(*sets.iteritems())

	sql = 'update %s set %s where %s' % \
		(table, ','.join(['%s=?' % sets_col for sets_col in sets_cols]),
			','.join(['%s=?' % where_col for where_col in where_cols]))
	args = sets_args + where_args
	return _update(sql, *args)

def update(sql, *args):
	return _update(sql, args)

# insert
# execute insert operation
def insert(table, **kw):
	cols, args = zip(*kw.iteritems())
	sql = 'insert into %s (%s) values (%s)' % \
		(table, ','.join(['%s' % col for col in cols]), \
			','.join(['?' for i in range(len(cols))]))
	return _update(sql, *args)

# delete
# delete a row in table
def delete(table, **where):
	cols, args = zip(*where.iteritems())
	sql = 'delete from %s where %s' % \
		(table, ','.join(['%s=?' % col for col in cols]))
	return _update(sql, *args)

# DbError
class DBError(Exception) :
	pass

# database engine class
class _Engine(object):
	"""docstring for _Engine"""
	def __init__(self, connect):
		super(_Engine, self).__init__()
		self._connect = connect
	def connect(self):
		return self._connect
	def cursor(self):
		if self._connect is None :
			raise DBError('don\'t connect to database')
		return self._connect.cursor()
	def cleanup(self):
		if self._connect:
			connection = self._connection
			self._connection = None
			logging.info('close connection <%s>...' % hex(id(connection)))
			connection.close()
	def execute(self, sql, *args):
		cursor = None
		sql = sql.replace('?', '%s')
		logging.info('SQL: %s, ARGS: %s' % (sql, args))
		try:
			cursor = self._connect.cursor()
			cursor.execute(sql, args)
			return cursor
		except Exception, e:
			raise
		else:
			pass
		finally:
			pass
	def commit(self):
		if self._connect is None:
			raise DBError('don\'t connect to database')
		try :
			self._connect.commit()
		except:
			logging.warning('commit failed. try rollback...')
			self._connect.rollback()
			logging.warning('rollback ok.')
			raise

	def rollback(self):
		if self._connect is None:
			raise DbError('don\'t connect to database')
		self._connect.rollback()

engine = None

# database context class
# threading.local is for thread safe
class _DbCtx(threading.local):
	"""docstring for _DbCtx"""
	def __init__(self):
		super(_DbCtx, self).__init__()
		self.should_cleanup = False
		self.transactions = 0
		self._engine = None

	def is_init(self):
		return self._engine is not None

	def init(self):
		global engine
		self._engine = engine
		self.should_cleanup = True
		self.transactions = 0

	def cleanup(self):
		if self.should_cleanup :
			engine = self._engine
			self._engine = None
			engine.cleanup()
			self.should_cleanup = False
	def engine(self):
		return self._engine

_db_ctx = _DbCtx()

# database connection context class
class _ConnectCtx(object):
	"""docstring for _ConnectCtx
	use by with connect()"""
	def __init__(self):
		super(_ConnectCtx, self).__init__()

	def __enter__(self):
		global _db_ctx
		if not _db_ctx.is_init():
			_db_ctx.init()
		return self


	def __exit__(slef, exctype, excvalue, traceback):
		global _db_ctx
		_db_ctx.cleanup()

# database transaction context class
class _TransactionCtx(object):
	"""docstring for _TransactionCtx"""
	def __init__(self):
		super(_TransactionCtx, self).__init__()
	def __enter__(self):
		global _db_ctx
		if not _db_ctx.is_init():
			_db_ctx.init()
		_db_ctx.transactions = _db_ctx.transactions + 1
		return self
	def __exit__(self):
		global _db_ctx
		_db_ctx.transactions = _db_ctx.transactions - 1
		try :
			if _db_ctx.transactions == 0:
				if exctype is None:
					_db_ctx.engine().commit()
				else:
					_db_ctx.engine().rollback()
		finally:
			if _db_ctx.should_cleanup:
				_db_ctx.cleanup()

if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG)
	create_engine('www-data', 'www-data', 'test')
	update('drop table if exists user')
	update('create table user (id int primary key, name text, email text, passwd text, last_modified real)')
	import doctest
	doctest.testmod()
