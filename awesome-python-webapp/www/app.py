#!/use/bin/env python3
# -*- coding:utf-8 -*-

__author__ = 'Jiejing Shan'

'''
Define web app.
'''

import logging, time, os
from framework import init, add_routes, start, add_template
from datetime import datetime

from transwarp import db
from jinja2 import Environment, FileSystemLoader

logging.basicConfig(level=logging.INFO)

def init_jinja2(**kw):
	logging.info('init jinja2.')
	options = dict(autoescape = kw.get('autoescape', True),
		block_start_string = kw.get('block_start_string', '{%'),
		block_end_string = kw.get('block_end_string', '%}'),
		variable_start_string = kw.get('variable_start_string', '{{'),
		variable_end_string = kw.get('variable_end_string', '}}'),
		auto_reload = kw.get('auto_reload', True))
	path = kw.get('path', None)
	if path is None:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
	logging.info('set jinja2 template path: %s' % path)
	env = Environment(loader=FileSystemLoader(path), **options)
	filters = kw.get('filters', None)
	if filters is not None:
		for name, f in filters.items():
			env.filters[name] = f
	add_template(env)

def datetime_filter(t):
	delta = int(time.time() - t)
	if delta < 60:
		return u'1分钟前'
	if delta < 3600:
		return u'%s分钟前' % (delta // 60)
	if delta < 86400:
		return u'%s小时前' % (delta // 3600)
	if delta < 604800:
		return u'%s天前' % (delta // 86400)
	dt = datetime.fromtimestamp(t)
	return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

def init_database():
	db.create_engine(**db_config)

from config import get_configs
configs = get_configs()
server_config = configs['server']
db_config = configs['db']
session_config = configs['session']
init(server_config['host'], server_config['port'])
init_database()
init_jinja2(filters=dict(datetime=datetime_filter))
add_routes('handlers')
start()
