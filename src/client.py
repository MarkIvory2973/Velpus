import socket
import struct
import uuid
import tdmsc
import const

class VelpusClient:
    def __init__(self, proxy, uuid, pri_key, msgsetting):
        self.client = socket.socket()
        self.proxy = proxy
        self.uuid = uuid
        self.pri_key = pri_key
        self.msgsetting = msgsetting
        
    def Auth(self):
        self.client.connect(self.proxy)
        
        self._SendStruct("! B 16s B", const.CMD.VELPUS_AUTH, self.uuid.bytes, self.msgsetting)
        
        msg = self.client.recv(2)
        msg = struct.unpack("! B B", msg)[1]
        
        return msg
    
    def Connect(self, server, intype, timeout):
        if intype == const.TYPE.VELPUS_IPV4:
            host = bytes(map(int, server[0].split(".")))
        
        self._SendStruct("! B B 4s H f", const.CMD.VELPUS_CONNECT, intype, host, server[1], timeout, encrypt=True)
        
        msg = self.client.recv(2)
        msg = struct.unpack("! B B", msg)[1]
        
        return msg
    
    def Send(self, server, intype, data):
        if intype == const.TYPE.VELPUS_IPV4:
            host = bytes(map(int, server[0].split(".")))
            
        self._SendStruct(f"! B B 4s H Q {len(data)}s", const.CMD.VELPUS_SEND, intype, host, server[1], len(data), data, encrypt=True)
        
        msg = self.client.recv(2)
        msg = struct.unpack("! B B", msg)[1]
        
        return msg
        
    def Recv(self, server, intype, bufsize):
        if intype == const.TYPE.VELPUS_IPV4:
            host = bytes(map(int, server[0].split(".")))
            
        self._SendStruct("! B B 4s H Q", const.CMD.VELPUS_RECV, intype, host, server[1], bufsize, encrypt=True)
        
        msg = self.client.recv(2)
        msg = struct.unpack("! B B", msg)[1]
        
        if msg != const.MSG.VELPUS_SUCCEED:
            return msg, None
        
        data = self.client.recv(bufsize)
        
        return msg, data
    
    def Disconnect(self, server, intype):
        if intype == const.TYPE.VELPUS_IPV4:
            host = bytes(map(int, server[0].split(".")))
            
        self._SendStruct("! B B 4s H", const.CMD.VELPUS_CONNECT, intype, host, server[1], encrypt=True)
        
        msg = self.client.recv(2)
        msg = struct.unpack("! B B", msg)[1]
        
        return msg
    
    def _SendStruct(self, format, *datas, encrypt=False):
        data = struct.pack(format, *datas)
        if encrypt:
            table = tdmsc.generate_table(self.pri_key, 10)
            data = tdmsc.encrypt(data, table)
        return self.client.send(data)
    
vclient = VelpusClient(("127.0.0.1", 8080), uuid.UUID("44a908c6-c0fa-4b73-bf04-174cb92c3f6c"), 39871510, const.TYPE.VELPUS_ALLMSG)
print(vclient.Auth())
print(vclient.Connect(("127.0.0.1", 80), const.TYPE.VELPUS_IPV4, 0.1))
print(vclient.Send(("127.0.0.1", 80), const.TYPE.VELPUS_IPV4, b"GET"))
print(vclient.Recv(("127.0.0.1", 80), const.TYPE.VELPUS_IPV4, 4096))
print(vclient.Send(("127.0.0.1", 80), const.TYPE.VELPUS_IPV4, b"CLOSE"))
vclient.client.close()