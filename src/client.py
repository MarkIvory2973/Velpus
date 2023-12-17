import socket
import struct
import uuid
import tdmsc
import const

class VelpusClient:
    def __init__(self, proxy, uuid, pri_key):
        self.client = socket.socket()
        self.proxy = proxy
        self.uuid = uuid
        self.pri_key = pri_key
        
    def Auth(self):
        self.client.connect(self.proxy)
        
        self._SendStruct("! B 16s", const.CMD.VELPUS_AUTH, self.uuid.bytes)
        
        msg = self.client.recv(2)
        msg = struct.unpack("! B B", msg)[1]
        
        return msg
    
    def Connect(self, cid, server, intype, timeout):
        if intype == const.TYPE.VELPUS_IPV4:
            host = bytes(map(int, server[0].split(".")))
        
        self._SendStruct("! B B H 4s H f", const.CMD.VELPUS_CONNECT, intype, cid, host, server[1], timeout, encrypt=True)
        
        msg = self.client.recv(2)
        msg = struct.unpack("! B B", msg)[1]
        
        return msg
    
    def Send(self, cid, data):
        self._SendStruct(f"! B H Q {len(data)}s", const.CMD.VELPUS_SEND, cid, len(data), data, encrypt=True)
        
        msg = self.client.recv(2)
        msg = struct.unpack("! B B", msg)[1]
        
        return msg
        
    def Recv(self, cid, bufsize):
        self._SendStruct("! B H Q", const.CMD.VELPUS_RECV, cid, bufsize, encrypt=True)
        
        msg = self.client.recv(2)
        msg = struct.unpack("! B B", msg)[1]
        
        if msg != const.MSG.VELPUS_SUCCEED:
            return msg, None
        
        data = self.client.recv(bufsize)
        
        return msg, data
    
    def Disconnect(self, cid):
        self._SendStruct("! B H", const.CMD.VELPUS_CONNECT, cid, encrypt=True)
        
        msg = self.client.recv(2)
        msg = struct.unpack("! B B", msg)[1]
        
        return msg
    
    def _SendStruct(self, format, *datas, encrypt=False):
        data = struct.pack(format, *datas)
        if encrypt:
            table = tdmsc.generate_table(self.pri_key, 10)
            data = tdmsc.encrypt(data, table)
        return self.client.send(data)
    
vclient = VelpusClient(("127.0.0.1", 8080), uuid.UUID("44a908c6-c0fa-4b73-bf04-174cb92c3f6c"), 39871510)
print(vclient.Auth())
print(vclient.Connect(5, ("127.0.0.1", 80), const.TYPE.VELPUS_IPV4, 0.1))
print(vclient.Send(5, b"GET"))
print(vclient.Recv(5, 4096))
print(vclient.Send(5, b"CLOSE"))
vclient.client.close()