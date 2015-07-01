#/usr/bin/env python3
# -*- coding:utf-8 -*-

__author__ = 'Jiejing Shan'

'''
Define all handlers for web app.
'''

from framework import get, post
from models import User
import logging

@get('/')
def test(request):
	users = yield from User.find_all()
	logging.info('users is %s' % str(users))
	return {
	'__template__': 'test.html',
	'users': users
	}
