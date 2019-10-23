
from aiosmb import logger
# the decorators below are used extensively to support the "result, exception" return types

def red_gen_deepdebug(funct):
	async def wrapper(*args, **kwargs):
		try:
			print('GEN_CALL:%s PARAMS: %s' % (funct.__name__, repr(args)))
			async for x in funct(*args, **kwargs):
				print('GEN_RET :%s VALUE: %s' % (funct.__name__, repr(x)))
				if x is None:
					print('GEN_RET ERROR @%s! ret value is a simple None. This is not according to coding guidelines' % funct.__name__)
				if len(x) < 2:
					print('GEN_RET ERROR @%s! only one parameter returned. This is not according to coding guidelines' % funct.__name__)
				if x[-1] is not None and isinstance(x[-1], Exception):
					print('GEN_RET ERROR @%s! the last return parameter is not None and also not an exception!' % funct.__name__)
				
				if x[-1] is not None:  #the last arg MUST ALWAYS be an exception or none!
					yield None, x[-1]
					break
				yield x
		except Exception as error:
			yield None, error
	return wrapper

def red_gen_original(funct):
	async def wrapper(*args, **kwargs):
		try:
			async for x in funct(*args, **kwargs):
				if x[-1] is not None:  #the last arg MUST ALWAYS be an exception or none!
					yield None, x[-1]
					break
				yield x
		except Exception as error:
			yield None, error
	return wrapper

def red_deepdebug(funct):
	async def wrapper(*args, **kwargs):
		try:
			print('CALL:%s PARAMS: %s' % (funct.__name__, repr(args)))
			x = await funct(*args, **kwargs)
			print('RET :%s VALUE: %s' % (funct.__name__, repr(x)))
			if x is None:
				print('GEN_RET ERROR @%s! ret value is a simple None. This is not according to coding guidelines' % funct.__name__)
			if len(x) < 2:
				print('GEN_RET ERROR @%s! only one parameter returned. This is not according to coding guidelines' % funct.__name__)
			if x[-1] is not None and isinstance(x[-1], Exception):
				print('GEN_RET ERROR @%s! the last return parameter is not None and also not an exception!' % funct.__name__)
			
			if x[-1] is None:
				return x
			return x

		except Exception as error:
			print('EXC:%s REASON: %s' % (funct.__name__, repr(error)))
			return None, error
	return wrapper	

def red_original(funct):
	async def wrapper(*args, **kwargs):
		try:			
			x = await funct(*args, **kwargs)
			if x[-1] is not None:
				raise x[-1]
			return x
		except Exception as error:
			return None, error
	return wrapper

def red(funct):
	if logger.getEffectiveLevel() == 1:
		return red_deepdebug(funct)
	return red_original(funct)

def red_gen(funct):
	if logger.getEffectiveLevel() == 1:
		return red_gen_deepdebug(funct)
	return red_gen_original(funct)

async def rr(coro):
	try:
		x = await coro
		error = x[-1] #the last arg MUST ALWAYS be an exception or none!
		if error is not None:
			raise error
		return x
	except Exception as e:
		raise e
	


async def rr_gen(coro):
	try:
		async for x in coro:
			if x[-1] is not None:  #the last arg MUST ALWAYS be an exception or none!
				raise x[-1]
				break
			yield x
	except Exception as e:
		raise e
