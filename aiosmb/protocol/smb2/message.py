import enum
import io

from aiosmb.protocol.smb2.headers import *
from aiosmb.protocol.smb2.commands import *
from aiosmb.protocol.smb2.command_codes import *

class SMB2Transform:
	def __init__(self):
		self.header = None
		self.data   = None
	
	@staticmethod
	def from_bytes(bbuff):
		return SMB2Transform.from_buffer(io.BytesIO(bbuff))

	@staticmethod
	def from_buffer(buff):
		msg = SMB2Transform()
		pos = buff.tell()
		t = buff.read(1)
		buff.seek(pos,0)
		if t == 0xFD:
			#encrypted
			msg.header = SMB2Header_TRANSFORM.from_buffer(buff)
		elif t == 0xFD:
			#encrypted
			msg.header = SMB2Header_COMPRESSION_TRANSFORM.from_buffer(buff)
		else:
			raise Exception('Unknown packet type for SMB2Transform! %s' % t)
		
		msg.data = buff.read()
		return msg

class SMB2Message:
	def __init__(self):
		self.header    = None
		self.command   = None

	@staticmethod
	def from_bytes(bbuff):
		return SMB2Message.from_buffer(io.BytesIO(bbuff))

	@staticmethod
	def from_buffer(buff):
		msg = SMB2Message()
		if SMB2Message.isAsync(buff):
			msg.header = SMB2Header_ASYNC.from_buffer(buff)
		else:
			msg.header = SMB2Header_SYNC.from_buffer(buff)

		classname = msg.header.Command.name
		try:
			if SMB2HeaderFlag.SMB2_FLAGS_SERVER_TO_REDIR in msg.header.Flags:
				classname += '_REPLY'
			else:
				classname += '_REQ'
			msg.command = command2object[classname].from_buffer(buff)
		except Exception as e:
			traceback.print_exc()
			print('Could not find command implementation! %s' % str(e))
			msg.command = SMB2NotImplementedCommand.from_buffer(buff)

		return msg

	@staticmethod
	def isAsync(buff):
		"""
		jumping to the header flags and check if the AYSNC command flag is set
		"""
		pos = buff.tell()
		buff.seek(16, io.SEEK_SET)
		flags = SMB2HeaderFlag(int.from_bytes(buff.read(4), byteorder='little', signed = False))
		buff.seek(pos, io.SEEK_SET)
		return SMB2HeaderFlag.SMB2_FLAGS_ASYNC_COMMAND in flags

	def to_bytes(self):
		t  = self.header.to_bytes()
		t += self.command.to_bytes()
		return t

	def __repr__(self):
		t = "== SMBv2 Message =="
		t += repr(self.header)
		t += repr(self.command)
		return t
		

command2object = {
	'NEGOTIATE_REQ'       : NEGOTIATE_REQ,
	'NEGOTIATE_REPLY'     : NEGOTIATE_REPLY,
	'SESSION_SETUP_REQ'     : SESSION_SETUP_REQ,
	'SESSION_SETUP_REPLY'     : SESSION_SETUP_REPLY,
	'TREE_CONNECT_REQ'     : TREE_CONNECT_REQ,
	'TREE_CONNECT_REPLY'     : TREE_CONNECT_REPLY,
}