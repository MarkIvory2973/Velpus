import socket
import struct
import uuid
import const

class VelpusClient:
    def __init__(self, proxy, uuid, msg):
        self.client = socket.socket()
        self.proxy = proxy
        self.uuid = uuid
        self.msg = msg
        
    def Auth(self):
        self.client.connect(self.proxy)
        
        self._SendStruct("! B 16s B", const.VELPUS_AUTH, self.uuid.bytes, self.msg)
        
        msg = self.client.recv(1)
        msg = struct.unpack("! B", msg)[0]
        
        return msg
    
    def Connect(self, server, intype, timeout):
        if intype == const.VELPUS_IPV4:
            host = bytes(map(int, server[0].split(".")))
        
        self._SendStruct("! B B 4s H f", const.VELPUS_CONNECT, intype, host, server[1], timeout)
        
        msg = self.client.recv(1)
        msg = struct.unpack("! B", msg)[0]
        
        return msg
    
    def Send(self, server, intype, data):
        if intype == const.VELPUS_IPV4:
            host = bytes(map(int, server[0].split(".")))
            
        self._SendStruct(f"! B B 4s H Q {len(data)}s", const.VELPUS_SEND, intype, host, server[1], len(data), data)
        
        msg = self.client.recv(1)
        msg = struct.unpack("! B", msg)[0]
        
        return msg
        
    def Recv(self, server, intype, bufsize):
        if intype == const.VELPUS_IPV4:
            host = bytes(map(int, server[0].split(".")))
            
        self._SendStruct("! B B 4s H Q", const.VELPUS_RECV, intype, host, server[1], bufsize)
        
        data = self.client.recv(bufsize)
        
        return data
    
    def Disconnect(self, server, intype):
        if intype == const.VELPUS_IPV4:
            host = bytes(map(int, server[0].split(".")))
            
        self._SendStruct("! B B 4s H", const.VELPUS_CONNECT, intype, host, server[1])
        
        msg = self.client.recv(1)
        msg = struct.unpack("! B", msg)[0]
        
        return msg
    
    def _SendStruct(self, format, *datas):
        data = struct.pack(format, *datas)
        return self.client.send(data)
    
vclient = VelpusClient(("127.0.0.1", 8080), uuid.UUID("44a908c6-c0fa-4b73-bf04-174cb92c3f6c"), const.VELPUS_ALLMSG)
print(vclient.Auth())
print(vclient.Connect(("127.0.0.1", 80), const.VELPUS_IPV4, 0.0001))
print(vclient.Send(("127.0.0.1", 80), const.VELPUS_IPV4, b"GET"))
print(vclient.Recv(("127.0.0.1", 80), const.VELPUS_IPV4, 4096))
print(vclient.Send(("127.0.0.1", 80), const.VELPUS_IPV4, b"CLOSE"))
vclient.client.close()