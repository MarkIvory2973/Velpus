import asyncio
import struct
import uuid
import const

Users = {
    uuid.UUID("44a908c6-c0fa-4b73-bf04-174cb92c3f6c"): "2uA3F39njf$"
}

async def SendMsg(client_writer, msg):
    msg = struct.pack("! B", msg)
    client_writer.write(msg)
    await client_writer.drain()

async def handle_client(client_reader, client_writer):
    UUID = None
    MSG = None
    servers = {}
    
    while True:
        data = await client_reader.read(4096)
        if not data:
            break
        # VELPUS_AUTH: |-CMD-|-UUID-|-MSG-|
        if data[0] == const.VELPUS_AUTH:
            try:
                auth = struct.unpack("! B 16s B", data)
            except:
                await SendMsg(client_writer, const.VELPUS_FAILED)
                break
            
            UUID = uuid.UUID(bytes=auth[1])
            MSG = auth[2]
            
            if not UUID in Users:
                await SendMsg(client_writer, const.VELPUS_INVALID_UUID)
                break
            
            if MSG == const.VELPUS_ALLMSG:
                await SendMsg(client_writer, const.VELPUS_SUCCEED)
        # VELPUS_CONNECT: |-CMD-|-INTYPE-|-IP-|-PORT-|
        elif data[0] == const.VELPUS_CONNECT and UUID:
            # VELPUS_IPV4
            if data[1] == const.VELPUS_IPV4:
                try:
                    connect = struct.unpack("! B B 4s H f", data)
                except:
                    await SendMsg(client_writer, const.VELPUS_FAILED)
                
                server = ".".join(map(str, connect[2])), connect[3]
                
            try:
                servers[server] = await asyncio.wait_for(asyncio.open_connection(*server), connect[4])
            except asyncio.TimeoutError:
                await SendMsg(client_writer, const.VELPUS_CONNECTION_TIMEOUT)
                continue
            except:
                await SendMsg(client_writer, const.VELPUS_FAILED)
                continue
            
            if MSG == const.VELPUS_SUCCEED:
                await SendMsg(client_writer, const.VELPUS_SUCCEED)
        # VELPUS_SEND: |-CMD-|-INTYPE-|-IP-|-PORT-|-DATASIZE-|
        elif data[0] == const.VELPUS_SEND and UUID:
            # VELPUS_IPV4
            if data[1] == const.VELPUS_IPV4:
                send = struct.unpack("! B B 4s H Q", data[:16])
                server = ".".join(map(str, send[2])), send[3]
                
            servers[server][1].write(data[16:16 + send[4]])
            await servers[server][1].drain()
            
            await SendMsg(client_writer, const.VELPUS_SUCCEED)
        # VELPUS_RECV: |-CMD-|-INTYPE-|-IP-|-PORT-|-BUFSIZE-|
        elif data[0] == const.VELPUS_RECV and UUID:
            # VELPUS_IPV4
            if data[1] == const.VELPUS_IPV4:
                recv = struct.unpack("! B B 4s H Q", data)
                server = ".".join(map(str, recv[2])), recv[3]
                
            data = await servers[server][0].read(recv[4])
            client_writer.write(data)
            await client_writer.drain()
        # VELPUS_DISCONNECT: |-CMD-|-INTYPE-|-IP-|-PORT-|
        elif data[0] == const.VELPUS_DISCONNECT:
            # VELPUS_IPV4
            if data[1] == const.VELPUS_IPV4:
                disconnect = struct.unpack("! B B 4s H", data)
                server = ".".join(map(str, disconnect[2])), disconnect[3]
                
            servers[server][1].close()
            servers.pop(server)
            
            await SendMsg(client_writer, const.VELPUS_SUCCEED)
            
    client_writer.close()

async def main():
    server = await asyncio.start_server(handle_client, "127.0.0.1", 8080)
    async with server:
        await server.serve_forever()

asyncio.run(main())