#!/usr/bin/python
# -*- coding:utf-8 -*-

__author__ = "Jiejing Shan"

'''
Define database table models.
'''

import time, uuid

from transwarp.db import next_id
from transwarp.orm import Model, IntegerField, StringField, BooleanField, FloatField, TextField

class User(Model):
	'''
	User table.
	'''
	__table__ = 'users'

	id = StringField(primary_key = True, default = next_id, ddl = 'varchar(50)')
	email = StringField(updatable = False, ddl = 'varchar(50)')
	password = StringField(ddl = 'varchar(50)')
	admin = BooleanField()
	name = StringField(ddl = 'varchar(50)')
	image = StringField(ddl = 'varchar(50)')
	create_at = FloatField(updatable = False, default = time.time)

class Blog(Model):
	'''
	Blog table.
	'''
	__table__ = 'blogs'

	id = StringField(primary_key = True, default = next_id, ddl = 'varchar(50)')
	user_id = StringField(updatable = False, ddl = 'varchar(50)', foreign_key = True, foreign_table_name = 'user', foreign_field = 'id')
	user_name = StringField(ddl = 'varchar(50)')
	user_image = StringField(ddl = 'varchar(50)')
	title = StringField(ddl = 'varchar(50)')
	summary = StringField(ddl = 'varchar(200)')
	content = TextField()
	create_at = FloatField(updatable = False, default = time.time)

class Comment(Model):
	'''
	Comment table.
	'''
	__table__ = 'comments'

	id = StringField(primary_key = True, default = next_id, ddl = 'varchar(50)')
	blog_id = StringField(updatable = False, ddl = 'varchar(50)', foreign_key = True, foreign_table_name = 'blog', foreign_field = 'id')
	user_id = StringField(updatable = False, ddl = 'varchar(50)', foreign_key = True, foreign_table_name = 'user', foreign_field = 'id')
	user_name = StringField(ddl = 'varchar(50)')
	user_image = StringField(ddl = 'varchar(50)')
	content = TextField()
	create_at = FloatField(updatable = False, default= time.time)
	context_id = StringField(ddl = 'varchar(50)') #被回复评论的id

class Tag(Model):
	'''
	Tag table. Store blog's tag.
	'''
	__table__ = 'tags'

	id = StringField(primary_key = True, default = next_id, ddl = 'varchar(50)')
	content = StringField(ddl = 'varchar(50)')

class CtxBlogTag(Model):
	'''
	Store the relationship of blog and tag.
	'''
	__table__ = 'ctx_blog_tag'

	id = StringField(primary_key = True, default = next_id, ddl = 'varchar(50)')
	blog_id = StringField(ddl = 'varchar(50)')
	tag_id = StringField(ddl = 'varchar(50)')
