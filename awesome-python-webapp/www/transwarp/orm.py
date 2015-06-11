#!/usr/bin/python
# -*- coding:utf-8 -*-

__author__ = "Jiejing Shan"

''' ORM module for web app
	using this module for easy to create User, Comment, Blog .etc from database
'''

import db, logging, time

class Field(object):
	"""define the database's Field"""
	_count = 0

	def __init__(self, **kw):
		super(Field, self).__init__()
		self.name = kw.get('name', None)
		self._default = kw.get('default', None)
		self.primary_key = kw.get('primary_key', False)
		self.nullable = kw.get('nullable', False)
		self.updatable = kw.get('updatable', True)
		self.insertable = kw.get('insertable', True)
		self.ddl = kw.get('ddl', '')
		self.foreign_key = kw.get('foreign_key', False)
		self.foreign_table_name = kw.get('foreign_table_name', None)
		self.foreign_field = kw.get('foreign_field', None)
		self._order = Field._count
		Field._count = Field._count + 1

	@property
	def default(self):
		d = self._default
		return d() if callable(d) else d

	def __str__(self):
		s = ['<%s:%s,%s,default(%s),' % (self.__class__.__name__, self.name, self.ddl, self._default)]
		self.nullable and s.append('N')
		self.updatable and s.append('U')
		self.insertable and s.append('I')
		self.foreign_key and s.append('Foreign %s.%s' % (self.foreign_table_name, self.foreign_field))
		s.append('>')
		return ' '.join(s)

class IntegerField(Field):
	''' integer field in database'''
	def __init__(self, **kw):
		if not 'default' in kw:
			kw['default'] = 0
		if not 'ddl' in kw:
			kw['ddl'] = 'bigint'
		super(IntegerField, self).__init__(**kw)

class StringField(Field):
	"""string field in database"""
	def __init__(self, **kw):
		if not 'default' in kw:
			kw['default'] = ''
		if not 'ddl' in kw:
			kw['ddl'] = 'varchar(255)'
		super(StringField, self).__init__(**kw)

class FloatField(Field):
	''' float field in database'''
	def __init__(self, **kw):
		if not 'default' in kw:
			kw['default'] = 0.0
		if not 'ddl' in kw :
			kw['ddl'] = 'real'
		super(FloatField, self).__init__(**kw)

class BooleanField(Field):
	def __init__(self, **kw):
		if not 'default' in kw:
			kw['default'] = False
		if not 'ddl' in kw:
			kw['ddl'] = 'bool'
		super(BooleanField, self).__init__(**kw)

class TextField(Field):
	def __init__(self, **kw):
		if not 'default' in kw:
			kw['default'] = ''
		if not 'ddl' in kw:
			kw['ddl'] = 'text'
		super(TextField, self).__init__(**kw)

class BlobField(Field):
	def __init__(self, **kw):
		if not 'default' in kw :
			kw['default'] = ''
		if not 'ddl' in kw:
			kw['ddl'] = 'blob'
		super(BlobField, self).__init__(**kw)

class VersionField(Field):
	def __init__(self, name=None):
		super(VersionField, self).__init__(name=name, default = 0, ddl = 'bigint')

_triggers = frozenset(['pre_insert', 'pre_update', 'pre_delete'])

def _gen_sql(table_name, mapping):
	''' according to the mapping's table fields, create the sql comment that create the table'''
	pk = None
	foreign_keys = []
	sql = ['-- generating SQL for %s:' % table_name, 'create table `%s` (' % table_name]
	for f in sorted(mapping.values(), lambda x, y: cmp(x._order, y._order)):
		if not hasattr(f, 'ddl'):
			raise StandardError('no ddl in field: %s' % f)
		ddl = f.ddl
		nullable = f.nullable
		if f.primary_key:
			pk = f.name
		if f.foreign_key:
			foreign_keys.append(('%s' % f.name, '%s', f.foreign_table_name, '%s' % f.foreign_field))
		sql.append(nullable and '	`%s` %s,' % (f.name, ddl) or '	`%s` %s not null,' % (f.name, ddl))
	fklen = len(foreign_keys)
	sql.append(fklen == 0 and '	primary key(`%s`)' % pk or '	primary key(`%s`),' % pk)
	i = 0
	for fk in foreign_keys:
		sql.append(i == fklen - 1 and '	foreign key(`%s`) references %s(%s)' % fk or '	foreign key(`%s`) references %s(%s),' % fk)
	sql.append(');')
	return '\n'.join(sql)

class ModelMetaClass(type):
	'''
	Metaclass for model class object
	'''
	def __new__(cls, name, base, attrs):
		#skip Model class:
		if name == 'Model':
			return type.__new__(cls, name, base, attrs)

		#store all subclasses info:
		if not hasattr(cls, 'subclasses'):
			cls.subclasses = {}
		if not name in cls.subclasses:
			cls.subclasses[name] = name
		else:
			logging.warning('Redefine class: %s' % name)

		logging.info('Scan ORMapping %s ....' % name)
		mapping = dict()
		primary_key = None
		for k, v in attrs.iteritems():
			if isinstance(v, Field):
				if not v.name:
					v.name = k
				logging.info('Found mapping: %s => %s' % (k, v))
				# check primary key
				if v.primary_key:
					if primary_key:
						raise TypeError('Cannot define more than 1 primary key in class: %s' % name)
					if v.nullable:
						logging.warning('NOTE: change primary key to non-nullable')
						v.nullable = False
					if v.updatable:
						logging.warning('NOTE: change primary key to non-updatable')
						v.updatable = False
					primary_key = v
				mapping[k] = v

		# check exist of primary key
		if not primary_key:
			raise TypeError('Primary key not defined in class : %s' % name)
		# pop all attributes form attrs which in the mapping
		for k in mapping.iterkeys():
			attrs.pop(k)
		#define default table name in class
		if not '__table__' in attrs:
			attrs['__table__'] = name.lower()
		attrs['__mappings__'] = mapping
		attrs['__primary_key__'] = primary_key
		attrs['__sql__'] = lambda self: _gen_sql(attrs['__table__'], mapping)
		for trigger in _triggers:
			if not trigger in attrs:
				attrs[trigger] = None
		return type.__new__(cls, name, base, attrs)

class Model(dict):
	'''
    Base class for ORM.
    >>> class User(Model):
    ...     id = IntegerField(primary_key=True)
    ...     name = StringField()
    ...     email = StringField(updatable=False)
    ...     passwd = StringField(default=lambda: '******')
    ...     last_modified = FloatField()
    ...     def pre_insert(self):
    ...         self.last_modified = time.time()
    >>> u = User(id=10190, name='Michael', email='orm@db.org')
    >>> r = u.insert()
    >>> u.email
    'orm@db.org'
    >>> u.passwd
    '******'
    >>> u.last_modified > (time.time() - 2)
    True
    >>> f = User.get(10190)
    >>> f.name
    u'Michael'
    >>> f.email
    u'orm@db.org'
    >>> f.email = 'changed@db.org'
    >>> r = f.update() # change email but email is non-updatable!
    >>> len(User.find_all())
    1
    >>> g = User.get(10190)
    >>> g.email
    u'orm@db.org'
    >>> r = g.delete()
    >>> len(db.select('select * from user where id=10190'))
    0
    >>> import json
    >>> print User().__sql__()
    -- generating SQL for user:
    create table `user` (
    	`id` bigint not null,
    	`name` varchar(255) not null,
    	`email` varchar(255) not null,
    	`passwd` varchar(255) not null,
    	`last_modified` real not null,
    	primary key(`id`)
    );
    '''

	__metaclass__ = ModelMetaClass

   	def __init__(self, **kw):
   		super(Model, self).__init__(**kw)

   	def __getattr__(self, key):
   		try :
   			return self[key]
   		except KeyError:
   			raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

   	def __setattr__(self, key, value):
   		self[key] = value

   	@classmethod
   	def get(cls, pk):
   		'''
   		Get by primary key
   		'''
   		d = db.select_one('select * from %s where %s=?' % (cls.__table__, cls.__primary_key__.name), pk)
   		return cls(**d) if d else None

   	@classmethod
   	def find_first(cls, where, *args):
   		'''
   		Find by where clause and return one result. If multiple results found,
   		only the first one returned. If no results found, return None.
   		'''
   		d = db.select_one('select * from %s where %s' % (cls.__table__, where), *args)
   		return cls(**d) if d else None

   	@classmethod
   	def find_by(cls, where, *args):
   		'''
   		Find by where clause and return list.
   		'''
   		sql = 'select * from %s where %s' % (cls.__table__, where)

   		d = db.select(sql, *args)
   		return [cls(**i) for l in d]

   	@classmethod
   	def find_all(cls, *args):
   		'''
   		Find all and return list.
   		'''
   		L = db.select('select * from %s' % cls.__table__)
   		return [cls(**l) for l in L]

   	@classmethod
   	def count_all(cls):
   		'''
   		Get count of rows in table.
   		'''
   		return db.select_int('select count(`%s`) from `%s`' % (cls.__primary_key__.name, cls.__table__))

   	@classmethod
   	def count_by(cls, where, *args):
   		'''
   		Get count of rows that find by where clause.
   		'''
   		return db.select_int('select count(`%s`) from `%s` where %s' % (cls.__primary_key__.name, cls.__table__, where), *args)

   	def update(self):
   		'''
   		Update class's property to database.
   		'''
   		self.pre_update and self.pre_update()
   		L = []
   		args = []
   		for k, v in self.__mappings__.iteritems():
   			if v.updatable:
   				if hasattr(self, k):
   					arg = getattr(self, k)
   				else:
   					arg = v.default()
   					setattr(self, k, arg)
   				L.append('`%s`=?' % k)
   				args.append(arg)
   		pk = self.__primary_key__.name
   		args.append(getattr(self, pk))
   		db.update('update `%s` set %s where %s=?' % (self.__table__, ','.join(L), pk), *args)
   		return self

   	def insert(self):
   		'''
   		Insert this object into database.
   		'''
   		self.pre_insert and self.pre_insert()
   		args = {}
   		for k, v in self.__mappings__.iteritems():
   			if v.insertable:
   				# if hasattr(self, k):
   				# 	arg = getattr(self, k)
   				# else:
   				# 	arg = v.default()
   				# 	setattr(self, k, arg)
   				if not hasattr(self, k):
   					setattr(self, k, v.default)
   				args[k] = getattr(self, k)
   		db.insert(self.__table__, **args)
   		return self

   	def delete(self):
   		'''
   		Delete row from database.
   		'''
   		self.pre_delete and self.pre_delete()
   		pk = self.__primary_key__.name
   		#args = (getattr(self, pk), )
   		#db.update('delete from %s where %s=?' %(self.__table__, pk), *args)
   		db.update('delete from %s where %s=?' % (self.__table__, pk), getattr(self, pk))
   		return self

if __name__ == '__main__' :
	logging.basicConfig(level=logging.DEBUG)
	db.create_engine('web-data', 'web-data', 'test')
	db.update('drop table if exists user')
	db.update('create table user (id int primary key, name text, email text, passwd text, last_modified real)')
	import doctest
	doctest.testmod()
