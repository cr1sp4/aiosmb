
import asyncio
import enum
import uuid

from aiosmb import logger
from aiosmb.commons.connection.url import SMBConnectionURL
from aiosmb.commons.interfaces.machine import SMBMachine

class EnumResultStatus(enum.Enum):
	RESULT = 'RESULT'
	FINISHED = 'FINISED'
	ERROR = 'ERROR'

class EnumResult:
	def __init__(self, target_id, target, result, error = None, status = EnumResultStatus.RESULT):
		self.target_id = target_id
		self.target = target
		self.error = error
		self.result = result
		self.status = status

class FileTargetGen:
	def __init__(self, filename):
		self.filename = filename

	async def run(self, target_q):
		try:
			cnt = 0
			with open(self.filename, 'r') as f:
				for line in f:
					line = line.strip()
					if line == '':
						continue
					await target_q.put((str(uuid.uuid4()), line))
					await asyncio.sleep(0)
					cnt += 1
			return cnt, None
		except Exception as e:
			return cnt, e

class ListTargetGen:
	def __init__(self, targets):
		self.targets = targets

	async def run(self, target_q):
		try:
			cnt = 0
			for target in self.targets:
				cnt += 1
				await target_q.put((str(uuid.uuid4()),target))
				await asyncio.sleep(0)
			return cnt, None
		except Exception as e:
			return cnt, e


class SMBFileEnum:
	def __init__(self, smb_url, worker_count = 100, depth = 3, enum_url = True):
		self.target_gens = []
		self.smb_mgr = SMBConnectionURL(smb_url)
		self.worker_count = worker_count
		self.task_q = None
		self.res_q = None
		self.depth = depth
		self.workers = []
		self.result_processing_task = None
		self.enum_url = enum_url
		self.__gens_finished = False
		self.__total_targets = 0
		self.__total_finished = 0

	async def __executor(self, tid, target):
		try:
			connection = self.smb_mgr.create_connection_newtarget(target)
			async with connection:
				_, err = await connection.login()
				if err is not None:
					raise err

				machine = SMBMachine(connection)
				async for path, otype, err in machine.enum_all_recursively(depth = self.depth):
					er = EnumResult(tid, target, (path, otype, err))
					await self.res_q.put(er)

		except asyncio.CancelledError:
			return
		except Exception as e:
			await self.res_q.put(EnumResult(tid, target, None, error = e, status = EnumResultStatus.ERROR))
		finally:
			await self.res_q.put(EnumResult(tid, target, None, status = EnumResultStatus.FINISHED))

	async def worker(self):
		try:
			while True:
				indata = await self.task_q.get()
				if indata is None:
					return
				
				tid, target = indata
				try:
					await asyncio.wait_for(self.__executor(tid, target), timeout=10)
				except asyncio.CancelledError:
					return
				except Exception as e:
					pass
		except asyncio.CancelledError:
			return
				
		except Exception as e:
			return e

	async def result_processing(self):
		try:
			while True:
				try:
					er = await self.res_q.get()
					if er.status == EnumResultStatus.FINISHED:
						self.__total_finished += 1
						print('[P][%s/%s][%s]' % (self.__total_targets, self.__total_finished, str(self.__gens_finished)))
						if self.__total_finished == self.__total_targets and self.__gens_finished is True:
							asyncio.create_task(self.terminate())
							return
					
					if er.result is not None:
						path, otype, err = er.result
						if otype is not None:
							print('[%s] %s' % (otype[0].upper(), path))
						if err is not None:
							print('[E] %s %s' % (err, path))
				except asyncio.CancelledError:
					return
				except Exception as e:
					print(e)
					continue
		except asyncio.CancelledError:
			return
		except Exception as e:
			print(e)

	async def terminate(self):
		for worker in self.workers:
			worker.cancel()
		if self.result_processing_task is not None:
			self.result_processing_task.cancel()		

	async def setup(self):
		try:
			if self.res_q is None:
				self.res_q = asyncio.Queue(self.worker_count)
				self.result_processing_task = asyncio.create_task(self.result_processing())
			if self.task_q is None:
				self.task_q = asyncio.Queue()

			for _ in range(self.worker_count):
				self.workers.append(asyncio.create_task(self.worker()))

			return True, None
		except Exception as e:
			return None, e
	
	async def run(self):
		try:
			_, err = await self.setup()
			if err is not None:
				raise err
			
			if self.enum_url is True:
				self.__total_targets += 1
				await self.task_q.put((str(uuid.uuid4()), self.smb_mgr.get_target().get_hostname_or_ip()))
			
			for target_gen in self.target_gens:
				total, err = await target_gen.run(self.task_q)
				self.__total_targets += total
				if err is not None:
					print('Target gen error! %s' % err)

			self.__gens_finished = True
			
			await asyncio.gather(*self.workers)
			return True, None
		except Exception as e:
			print(e)
			return None, e

async def amain():
	import argparse

	parser = argparse.ArgumentParser(description='SMB Share enumerator')
	parser.add_argument('-d', '--depth', type=int, default=3, help='Recursion depth, -1 means infinite')
	parser.add_argument('-w', '--smb-worker-count', type=int, default=100, help='Parallell count')
	parser.add_argument('smb_url', help='Connection URL base, target can be anything. Example: "smb2+ntlm-password://TEST\\victim@test"')
	parser.add_argument('targets', nargs='+', help = 'Hostname or IP address or file with a list of targets')
	args = parser.parse_args()

	logger.setLevel(100)
	enumerator = SMBFileEnum(args.smb_url, worker_count = args.smb_worker_count, depth = args.depth)
	
	notfile = []
	for target in args.targets:
		try:
			f = open(target, 'r')
			f.close()
			enumerator.target_gens.append(FileTargetGen(target))
		except:
			notfile.append(target)
	
	if len(notfile) > 0:
		enumerator.target_gens.append(ListTargetGen(notfile))

	if len(enumerator.target_gens) == 0:
		print('[-] No suitable targets were found!')
		return
		
	await enumerator.run()

def main():
	asyncio.run(amain())

if __name__ == '__main__':
	main()