import asyncio
import struct
import uuid
import tdmsc
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
        # Connections
        connections = {}
        
        while True:
            # Recieve
            data = await client_reader.read(4096)
            # Connection closed
            if not data:
                break
            # Decrypt
            if UUID:
                table = tdmsc.generate_table(self.users[UUID], 10)
                data = tdmsc.decrypt(data, table)
            # VELPUS_AUTH: |-CMD-|-UUID-|-MSG-|
            if data[0] == const.CMD.VELPUS_AUTH:
                try:
                    # Unpack
                    auth = struct.unpack("! B 16s", data)
                except:
                    # Failed to unpack
                    await self._SendMsg(client_writer, const.MSG.VELPUS_FAILED)
                    continue
                
                # Record UUID
                UUID = uuid.UUID(bytes=auth[1])
                
                if not UUID in self.users:
                    # Invalid UUID
                    await self._SendMsg(client_writer, const.MSG.VELPUS_INVALID_UUID)
                    # Reset UUID
                    UUID = None
                    continue
            # VELPUS_CONNECT: |-CMD-|-INTYPE-|-CID-|-IP-|-PORT-|-TIMEOUT-|
            elif data[0] == const.CMD.VELPUS_CONNECT and UUID:
                # VELPUS_IPV4
                if data[1] == const.TYPE.VELPUS_IPV4:
                    try:
                        # Unpack
                        connect = struct.unpack("! B B H 4s H f", data)
                    except:
                        # Failed to unpack
                        await self._SendMsg(client_writer, const.MSG.VELPUS_FAILED)
                        continue
                    
                    # Unpack IP (IPv4)
                    server = ".".join(map(str, connect[3])), connect[4]
                    
                try:
                    # Connect to server
                    connections[connect[2]] = await asyncio.wait_for(asyncio.open_connection(*server), connect[5])
                except asyncio.TimeoutError:
                    # Timeout
                    await self._SendMsg(client_writer, const.MSG.VELPUS_CONNECTION_TIMEOUT)
                    continue
                except:
                    # Failed to connect
                    await self._SendMsg(client_writer, const.MSG.VELPUS_FAILED)
                    continue
            # VELPUS_SEND: |-CMD-|-CID-|-DATASIZE-|
            elif data[0] == const.CMD.VELPUS_SEND and UUID:
                try:
                    # Unpack
                    send = struct.unpack("! B H Q", data[:11])
                except:
                    # Failed to unpack
                    await self._SendMsg(client_writer, const.MSG.VELPUS_FAILED)
                    continue
                    
                if not send[1] in connections:
                    # Failed to send to a connection that has not been connected yet
                    await self._SendMsg(client_writer, const.MSG.VELPUS_UNCONNECTED)
                    continue
                    
                # Send
                connections[send[1]][1].write(data[11:11 + send[2]])
                await connections[send[1]][1].drain()
            # VELPUS_RECV: |-CMD-|-CID-|-BUFSIZE-|
            elif data[0] == const.CMD.VELPUS_RECV and UUID:
                try:
                    # Unpack
                    recv = struct.unpack("! B H Q", data)
                except:
                    # Failed to unpack
                    await self._SendMsg(client_writer, const.MSG.VELPUS_FAILED)
                    continue
                    
                if not recv[1] in connections:
                    # Failed to send to a connection that has not been connected yet
                    await self._SendMsg(client_writer, const.MSG.VELPUS_UNCONNECTED)
                    continue
                    
                # Succeed
                await self._SendMsg(client_writer, const.MSG.VELPUS_SUCCEED)
                    
                # Recieve
                data = await connections[recv[1]][0].read(recv[2])
                # Send
                client_writer.write(data)
                await client_writer.drain()
                
                continue
            # VELPUS_DISCONNECT: |-CMD-|-CID-|
            elif data[0] == const.CMD.VELPUS_DISCONNECT and UUID:
                try:
                    # Unpack
                    disconnect = struct.unpack("! B H", data)
                except:
                    # Failed to unpack
                    await self._SendMsg(client_writer, const.MSG.VELPUS_FAILED)
                    continue
                    
                connections[disconnect[1]][1].close()
                connections.pop(disconnect[1])
            elif not UUID:
                # Unauthorized
                await self._SendMsg(client_writer, const.MSG.VELPUS_UNAUTHORIZED)
                continue
            else:
                # Unknown command
                await self._SendMsg(client_writer, const.MSG.VELPUS_UNKNOWN_CMD)
                continue
                
            # Succeed
            await self._SendMsg(client_writer, const.MSG.VELPUS_SUCCEED)
        
    async def _SendMsg(self, client_writer, msg):
        # Pack
        msg = struct.pack("! B B", const.CMD.VELPUS_MSG, msg)
        # Send
        client_writer.write(msg)
        await client_writer.drain()

# Users
users = {
    uuid.UUID("44a908c6-c0fa-4b73-bf04-174cb92c3f6c"): 39871510
}

vproxy = VelpusProxy(("127.0.0.1", 8080), users)
asyncio.run(vproxy.Start())