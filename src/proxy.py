import asyncio
import struct
import uuid
import const

class VelpusProxy:
    def __init__(self, proxy, users):
        self.proxy = proxy
        self.users = users
        
    async def Start(self):
        server = await asyncio.start_server(self.handle_client, *self.proxy)
        async with server:
            await server.serve_forever()
            
    async def handle_client(self, client_reader, client_writer):
        # UUID
        UUID = None
        # Message setting
        MSGSetting = const.TYPE.VELPUS_ALLMSG
        # Connections
        connections = {}
        
        while True:
            # Recieve
            data = await client_reader.read(4096)
            # Connection closed
            if not data:
                break
            # VELPUS_AUTH: |-CMD-|-UUID-|-MSG-|
            if data[0] == const.CMD.VELPUS_AUTH:
                try:
                    # Unpack
                    auth = struct.unpack("! B 16s B", data)
                except:
                    # Failed to unpack
                    await self._SendMsg(client_writer, const.MSG.VELPUS_FAILED)
                    continue
                
                # Record UUID
                UUID = uuid.UUID(bytes=auth[1])
                # Set message setting
                MSGSetting = auth[2]
                
                if not UUID in self.users:
                    # Invalid UUID
                    await self._SendMsg(client_writer, const.MSG.VELPUS_INVALID_UUID)
                    continue
            # VELPUS_CONNECT: |-CMD-|-INTYPE-|-IP-|-PORT-|
            elif data[0] == const.CMD.VELPUS_CONNECT and UUID:
                # VELPUS_IPV4
                if data[1] == const.TYPE.VELPUS_IPV4:
                    try:
                        # Unpack
                        connect = struct.unpack("! B B 4s H f", data)
                    except:
                        # Failed to unpack
                        await self._SendMsg(client_writer, const.MSG.VELPUS_FAILED)
                        continue
                    
                    # Unpack IP (IPv4)
                    server = ".".join(map(str, connect[2])), connect[3]
                    
                try:
                    # Connect to server
                    connections[server] = await asyncio.wait_for(asyncio.open_connection(*server), connect[4])
                except asyncio.TimeoutError:
                    # Timeout
                    await self._SendMsg(client_writer, const.MSG.VELPUS_CONNECTION_TIMEOUT)
                    continue
                except:
                    # Failed to connect
                    await self._SendMsg(client_writer, const.MSG.VELPUS_FAILED)
                    continue
            # VELPUS_SEND: |-CMD-|-INTYPE-|-IP-|-PORT-|-DATASIZE-|
            elif data[0] == const.CMD.VELPUS_SEND and UUID:
                # VELPUS_IPV4
                if data[1] == const.TYPE.VELPUS_IPV4:
                    try:
                        # Unpack
                        send = struct.unpack("! B B 4s H Q", data[:16])
                    except:
                        # Failed to unpack
                        await self._SendMsg(client_writer, const.MSG.VELPUS_FAILED)
                        continue
                        
                    # Unpack IP
                    server = ".".join(map(str, send[2])), send[3]
                    
                if not server in connections:
                    # Failed to send to a connection that has not been connected yet
                    await self._SendMsg(client_writer, const.MSG.VELPUS_UNCONNECTED)
                    continue
                    
                # Send
                connections[server][1].write(data[16:16 + send[4]])
                await connections[server][1].drain()
            # VELPUS_RECV: |-CMD-|-INTYPE-|-IP-|-PORT-|-BUFSIZE-|
            elif data[0] == const.CMD.VELPUS_RECV and UUID:
                # VELPUS_IPV4
                if data[1] == const.TYPE.VELPUS_IPV4:
                    try:
                        # Unpack
                        recv = struct.unpack("! B B 4s H Q", data)
                    except:
                        # Failed to unpack
                        await self._SendMsg(client_writer, const.MSG.VELPUS_FAILED)
                        continue
                    
                    # Unpack IP
                    server = ".".join(map(str, recv[2])), recv[3]
                    
                if not server in connections:
                    # Failed to send to a connection that has not been connected yet
                    await self._SendMsg(client_writer, const.MSG.VELPUS_UNCONNECTED)
                    continue
                    
                # Succeed
                if MSGSetting == const.TYPE.VELPUS_ALLMSG:
                    await self._SendMsg(client_writer, const.MSG.VELPUS_SUCCEED)
                    
                # Recieve
                data = await connections[server][0].read(recv[4])
                # Send
                client_writer.write(data)
                await client_writer.drain()
                
                continue
            # VELPUS_DISCONNECT: |-CMD-|-INTYPE-|-IP-|-PORT-|
            elif data[0] == const.CMD.VELPUS_DISCONNECT:
                # VELPUS_IPV4
                if data[1] == const.TYPE.VELPUS_IPV4:
                    disconnect = struct.unpack("! B B 4s H", data)
                    server = ".".join(map(str, disconnect[2])), disconnect[3]
                    
                connections[server][1].close()
                connections.pop(server)
            else:
                # Unknown command
                await self._SendMsg(client_writer, const.MSG.VELPUS_UNKNOWN_CMD)
                continue
                
            # Succeed
            if MSGSetting == const.TYPE.VELPUS_ALLMSG:
                await self._SendMsg(client_writer, const.MSG.VELPUS_SUCCEED)
        
    async def _SendMsg(self, client_writer, msg):
        msg = struct.pack("! B B", const.CMD.VELPUS_MSG, msg)
        client_writer.write(msg)
        await client_writer.drain()

users = {
    uuid.UUID("44a908c6-c0fa-4b73-bf04-174cb92c3f6c"): "2uA3F39njf$"
}

vproxy = VelpusProxy(("127.0.0.1", 8080), users)
asyncio.run(vproxy.Start())