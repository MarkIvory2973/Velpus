import socket
import ssl
import struct
import uuid
import const

class VelpusClient:
    def __init__(self, proxy, uuid, pri_key):
        context = ssl.create_default_context()
        context.load_verify_locations("server.crt")
        context.check_hostname = False
        
        self.client = context.wrap_socket(socket.socket())
        self.proxy = proxy
        self.uuid = uuid
        self.pri_key = pri_key
        
        self.client.connect(self.proxy)
    
    def Connect(self, cid, server, intype, timeout):
        if intype == const.TYPE.VELPUS_IPV4:
            host = bytes(map(int, server[0].split(".")))
        
        self._SendStruct("! 16s B B 4s H H f", self.uuid.bytes, const.CMD.VELPUS_CONNECT, intype, host, server[1], cid, timeout)
        
        msg = self.client.recv(10)
        msg = struct.unpack("! B B H", msg)
        
        return msg
    
    def Send(self, cid, data):
        self._SendStruct(f"! 16s B H Q {len(data)}s", self.uuid.bytes, const.CMD.VELPUS_SEND, cid, len(data), data)
        
        msg = self.client.recv(10)
        msg = struct.unpack("! B B H", msg)
        
        return msg
        
    def Recv(self, cid, bufsize):
        self._SendStruct("! 16s B H Q", self.uuid.bytes, const.CMD.VELPUS_RECV, cid, bufsize)
        
        raw = self.client.recv(3+bufsize)
        msg = struct.unpack("! B B H", raw[:4])
        data = raw[4:4+bufsize]
        if msg[1] != const.MSG.VELPUS_SUCCEED:
            return msg, None
        
        return msg, data
    
    def Disconnect(self, cid):
        self._SendStruct("! 16s B H", self.uuid.bytes, const.CMD.VELPUS_DISCONNECT, cid)
        
        msg = self.client.recv(10)
        msg = struct.unpack("! B B H", msg)
        
        return msg
    
    def _SendStruct(self, format, *datas):
        data = struct.pack(format, *datas)
        return self.client.sendall(data)
  
vclient = VelpusClient(("127.0.0.1", 8080), uuid.UUID("44a908c6-c0fa-4b73-bf04-174cb92c3f6c"), 29183829)
print(vclient.Connect(5, ("127.0.0.1", 80), const.TYPE.VELPUS_IPV4, 3))
print(vclient.Send(5, b"Hello World!"))
print(vclient.Recv(5, 4096))
print(vclient.Disconnect(5))
vclient.client.close()