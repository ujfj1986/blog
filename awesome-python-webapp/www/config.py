#!/usr/bin/env python3
# -*- coding:utf-8 -*-

__author__ = 'Jiejing Shan'

import config_default

def get_configs():
	configs = config_default.configs
	try:
		import config_override
		configs = merge(configs, config_override.configs)
	except :
		pass
	return configs
