#!usr/bin/env python3
# -*- coding:utf-8 -*-

__author__ = 'Jiejing Shan'

'''
Define the web framework for this blog web app.
This web framwork is based aiohttp.
It works at adding the router into aiohttp easily, constructing web Response object easily,
and starting or stoping the service easily.
'''

from aiohttp import web
import asyncio, functools, inspect, os, json, logging

def get(path):
	'''
	Define the decorator @get('/path')
	'''
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'GET'
		wrapper.__route__ = path
		return wrapper
	return decorator

def post(path):
	'''
	Define the decorator @post('/path')
	'''
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'POST'
		wrapper.__route__ = path
		return wrapper
	return decorator

def get_required_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
			args.append(name)
	return tuple(args)

def has_named_kw_args(fn):
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			return True

def get_named_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			args.append(name)
	return tuple(args)

def has_var_kw_arg(fn):
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.VAR_KEYWORD:
			return True

def has_request_arg(fn):
	params = inspect.signature(fn).parameters
	found = False
	for name, param in params.items():
		if name == 'request':
			found = True
			continue
		if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and 	\
			param.kind != inspect.Parameter.KEYWORD_ONLY and 				\
			param.kind != inspect.Parameter.VAR_KEYWORD):
			raise ValueError('request parameter must be the last named parameter in function: %s%s' %\
				(fn.__name__, str(inspect.signature(fn))))
	return found

class RequestHandler(object):

	def __init__(self, fn):
		self._fn = fn
		self._has_request_arg = has_request_arg(fn)
		self._has_var_kw_arg = has_var_kw_arg(fn)
		self._has_named_kw_arg = has_named_kw_args(fn)
		self._name_kw_args = get_named_kw_args(fn)
		self._required_kw_args = get_required_kw_args(fn)

	@asyncio.coroutine
	def __call__(self, request):
		kw = None
		if self._has_var_kw_arg or self._has_named_kw_arg or self._required_kw_args:
			if request.method == 'POST':
				if not request.content_type:
					return web.HTTPBadRequest('Missing Content-Type')
				ct = request.content_type.lower()
				if ct.startswith('application/json'):
					params = yield from request.json()
					if not isinstance(params, dict):
						return web.HTTPBadRequest('JSON body must be onject.')
					kw = params
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
					params = yield from request.post()
					kw = dict(**params)
				else:
					return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
			if request.method == 'GET':
				qs = request.query_string
				if qs:
					kw = dict()
					for k, v in parse.parse_qs(qs, True).items():
						kw[k] = v[0]
		if kw is None:
			kw = dict(**request.match_info)
		else:
			if not self._has_var_kw_arg and self._name_kw_args:
				#remove all unamed kw:
				copy = dict()
				for name in self._name_kw_args:
					if name in kw:
						copy[name] = kw[name]
				kw = copy
			#check named arg:
			for k, v in request.match_info.items():
				if k in kw:
					logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
				kw[k] = v
		if self._has_request_arg:
			kw['request'] = request
		#check required kw:
		if self._required_kw_args:
			for name in self._required_kw_args:
				if not name in kw:
					return web.HTTPBadRequest('Missing argument:%s' % name)
		logging.info('call with args:%s' % str(kw))
		try:
			r = yield from self._fn(**kw)
			return r
		except APIError as e:
			return dict(error=e.error, data=e.data, message=e.message)

def add_route(fn):
	global _routes, _isrun
	method = getattr(fn, '__method__', None)
	route = getattr(fn, '__route__', None)
	if method is None or route is None:
		raise ValueError('@get or @post not defined in %s.' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
	logging.info('add route %s %s => %s(%s)' % (method, route, fn.__name__, ','.join(inspect.signature(fn).parameters.keys())))
	_routes.append([method, route, RequestHandler(fn)])
	if _isrun:
		restart()
	#_app.router.add_route(method, route, RequestHandler(fn))


def add_routes(module):
	n = module.rfind('.')
	if n == (-1):
		mod = __import__(module, globals(), locals())
	else:
		name = module[n+1:]
		mod = getattr(__import__(module[:n], globals(), locals(), [name]), name)
	for attr in dir(mod):
		if attr.startswith('_'):
			continue
		fn = getattr(mod, attr)
		if callable(fn):
			method = getattr(fn, '__method__', None)
			route = getattr(fn, '__route__', None)
			if method and route:
				add_route(fn)

def add_static(path):
	path = os.path.join(path, 'static')
	logging.info('add static %s -> %s.' % ('/static/', path))
	#_app.router.add_static('/static/', path)

def add_middleware(middleware):
	global _middleware, _isrun
	_middleware.add(middleware)
	if _isrun:
		restart()

def add_template(template):
	global _template, _isrun
	_template = template
	if _isrun:
		restart()

def start():
	global _ip, _port, _isrun, _loop, _app, _routes, _handler, _srv, _middleware
	if _ip is None or _port is None:
		raise Exception('Server uninit.')
	if _isrun:
		raise Exception('Server is running.')
	_loop = asyncio.get_event_loop()
	_app = web.Application(loop=_loop, middlewares=list(_middleware))
	_app['__template__'] = _template
	for route in _routes:
		logging.info('add router:[%s]' % str(route))
		if callable(route[2]):
			logging.info('handler %s can call' % route[2])
		_app.router.add_route(route[0], route[1], route[2])
	logging.info('_app.router has %s' % str(_app.router.items()))
	_handler = _app.make_handler()
	f = _loop.create_server(_handler, _ip, _port)
	_srv = _loop.run_until_complete(f)
	logging.info('server started at %s:%s....' % (_ip, _port))
	try:
		_isrun = True
		_loop.run_forever()
	except KeyboardInterrupt:
		pass
	finally:
		_isrun = False
		_loop.run_until_complete(_handler.finish_connections(1.0))
		_handler = None
		_srv.close()
		_loop.run_until_complete(srv.wait_closed())
		_srv = None
		_loop.run_until_complete(_app.finish())
		_app = None

def stop():
	global _isrun, _loop
	if not _isrun:
		return
	_loop.stop()
	_loop.close()


def restart():
	stop()
	start()

def init(ip, port):
	global _app, _ip, _port
	if _app is not None:
		raise Exception('Service has init.')

	_ip = ip
	_port = port
	logging.info('init server at %s:%s...' % (_ip, _port))

@asyncio.coroutine
def logger_factory(app, handler):
	@asyncio.coroutine
	def logger(request):
		logging.info('Request: %s %s' % (request.method, request.path))
		logging.info('app is %s, handler is %s' % (app, handler))
		# yield from asyncio.sleep(0.3)
		return (yield from handler(request))
	return logger

@asyncio.coroutine
def response_factory(app, handler):
	@asyncio.coroutine
	def response(request):
		logging.info('Response handler.')
		r = yield from handler(request)
		if isinstance(r, web.StreamResponse):
			return r
		if isinstance(r, bytes):
			resp = web.Response(body=r)
			resp.content_type = 'application/octet-stream'
			return resp
		if isinstance(r, str):
			if r.startswith('redirect:'):
				return web.HTTPFound(r[9:])
			resp = web.Response(body=r.encode('utf-8'))
			resp.content_type = 'text/html;charset=utf-8'
			return resp
		if isinstance(r, dict):
			template = r.get('__template__')
			if template is None:
				resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o:o.__dict__).encode('utf-8'))
				resp.content_type = 'application/json;charset=utf-8'
				return resp
			else:
				resp = web.Response(body=app['__template__'].get_template(template).render(**r).encode('utf-8'))
				resp.content_type = 'text/html;charset=utf-8'
				return resp
		if isinstance(r, int) and r >= 100 and r < 600:
			return web.Response(t)
		if isinstance(r, tuple) and len(r) == 2:
			t, m = r
			if isinstance(t, int) and t >= 100 and t < 600:
				return web.Response(t, str(m))
		#default:
		resp = web.Response(body=str(r).encode('utf-8'))
		resp.content_type = 'text/plain;charset=utf-8'
		return resp
	return response

_loop = None
_app = None
_srv = None
_handler = None
_isrun = False
_middleware = set([response_factory, logger_factory])
_template = None
_ip = None
_port = None
_routes = []
