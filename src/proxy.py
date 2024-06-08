import asyncio
import ssl
import struct
import uuid
import const

context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain("server.crt", "server.key")

users = {
    uuid.UUID("44a908c6-c0fa-4b73-bf04-174cb92c3f6c"): {
        "connections": {}
    }
}

is_disconnected = lambda UUID, CID: not CID in users[UUID]["connections"] or asyncio.StreamReader.at_eof(users[UUID]["connections"][CID][0])

async def handle_client(client_reader, client_writer):
    await client_writer.start_tls(context)
    
    while True:
        # client -> proxy |-...-|
        raw = await client_reader.read(65535)
        print(raw)
        if not raw:
            break
        
        match raw[16]:
            # VELPUS_CONNECT:
            # -> |-UUID-|-CMD-|-ATYPE-|-IP-|-PORT-|-CID-|-TIMEOUT-|
            # <- |-CMD-|-MSG-|-CID-|
            case const.CMD.VELPUS_CONNECT:
                await connect(client_writer, raw)
            # VELPUS_SEND:
            # -> |-UUID-|-CMD-|-CID-|-BUFSIZE-|-DATA-|
            # <- |-CMD-|-MSG-|-CID-|
            case const.CMD.VELPUS_SEND:
                await send(client_writer, raw)
            # VELPUS_RECV:
            # -> |-UUID-|-CMD-|-CID-|-BUFSIZE-|
            # <- |-CMD-|-MSG-|-CID-|-DATA-|
            case const.CMD.VELPUS_RECV:
                await recv(client_writer, raw)
            # VELPUS_DISCONNECT:
            # -> |-UUID-|-CMD-|-CID-|
            # <- |-CMD-|-MSG-|-CID-|
            case const.CMD.VELPUS_DISCONNECT:
                await disconnect(client_writer, raw)
            case _:
                client_writer.write(struct.pack("! s B", raw[16], const.MSG.VELPUS_UNKNOWN_CMD))
                await client_writer.drain()
                
def auth(view_func):
    async def wrapper(client_writer, raw):
        try:
            UUID = uuid.UUID(bytes=raw[:16])
        except:
            # client <- proxy |-CMD-|-INVALID_UUID-|
            client_writer.write(struct.pack("! s B", raw[16], const.MSG.VELPUS_INVALID_UUID))
            await client_writer.drain()
            return
        
        if not UUID in users:
            # client <- proxy |-CMD-|-INVALID_UUID-|
            client_writer.write(struct.pack("! s B", raw[16], const.MSG.VELPUS_INVALID_UUID))
            await client_writer.drain()
            return
        
        return await view_func(client_writer, raw)
    
    return wrapper

@auth
async def connect(client_writer, raw):
    match raw[17]:
        # IPv4
        case const.TYPE.VELPUS_IPV4:
            # Unpack
            UUID, CMD, _, IP, PORT, CID, TIMEOUT = struct.unpack("! 16s B B 4s H H f", raw)
            UUID = uuid.UUID(bytes=UUID)
            IP = ".".join(map(str, IP))
        case _:
            # client <- proxy |-CONNECT-|-UNSUPPORTED_ATYPE-|-CID-|
            client_writer.write(struct.pack("! B B 2s", raw[0], const.MSG.VELPUS_UNSUPPORTED_ATYPE, raw[24:26]))
            await client_writer.drain()
            return
        
    try:
        # Connect to server
        users[UUID]["connections"] |= {CID: await asyncio.wait_for(asyncio.open_connection(IP, PORT), TIMEOUT)}
        
        # client <- proxy |-CONNECT-|-SUCCEED-|-CID-|
        client_writer.write(struct.pack("! B B H", CMD, const.MSG.VELPUS_SUCCEED, CID))
        await client_writer.drain()
        return
    except asyncio.TimeoutError:
        # client <- proxy |-CONNECT-|-TIMEOUT-|-CID-|
        client_writer.write(struct.pack("! B B H", CMD, const.MSG.VELPUS_TIMEOUT, CID))
        await client_writer.drain()
        return
    
@auth
async def send(client_writer, raw):
    # Unpack
    UUID, CMD, CID, BUFSIZE = struct.unpack("! 16s B H Q", raw[:27])
    UUID = uuid.UUID(bytes=UUID)
    DATA = raw[27:27 + BUFSIZE]
    
    if is_disconnected(UUID, CID):
        # client <- proxy |-SEND-|-UNCONNECTED-|-CID-|
        client_writer.write(struct.pack("! B B H", CMD, const.MSG.VELPUS_UNCONNECTED, CID))
        await client_writer.drain()
        return
        
    # proxy -> server |-DATA-|
    users[UUID]["connections"][CID][1].write(DATA)
    await users[UUID]["connections"][CID][1].drain()
    
    # client <- proxy |-SEND-|-SUCCEED-|-CID-|
    client_writer.write(struct.pack("! B B H", CMD, const.MSG.VELPUS_SUCCEED, CID))
    await client_writer.drain()

@auth
async def recv(client_writer, raw):
    # Unpack
    UUID, CMD, CID, BUFSIZE = struct.unpack("! 16s B H Q", raw)
    UUID = uuid.UUID(bytes=UUID)
    
    if is_disconnected(UUID, CID):
        # client <- proxy |-RECV-|-UNCONNECTED-|-CID-|
        client_writer.write(struct.pack("! B B H", CMD, const.MSG.VELPUS_UNCONNECTED, CID))
        await client_writer.drain()
        return
        
    # proxy <- server |-DATA-|
    DATA = await users[UUID]["connections"][CID][0].read(BUFSIZE)
    
    # client <- proxy |-RECV-|-SUCCEED-|-CID-|-DATA-|
    client_writer.write(struct.pack(f"! B B H {len(DATA)}s", CMD, const.MSG.VELPUS_SUCCEED, CID, DATA))
    await client_writer.drain()

@auth
async def disconnect(client_writer, raw):
    # Unpack
    UUID, CMD, CID = struct.unpack("! 16s B H", raw)
    UUID = uuid.UUID(bytes=UUID)
    
    if is_disconnected(UUID, CID):
        # client <- proxy |-DISCONNECT-|-UNCONNECTED-|-CID-|
        client_writer.write(struct.pack("! B B H", CMD, const.MSG.VELPUS_UNCONNECTED, CID))
        await client_writer.drain()
        return
    
    # Disconnect
    users[UUID]["connections"][CID][1].close()
    await users[UUID]["connections"][CID][1].wait_closed()
    users[UUID]["connections"].pop(CID)
    
    # client <- proxy |-DISCONNECT-|-SUCCEED-|-CID-|
    client_writer.write(struct.pack("! B B H", CMD, const.MSG.VELPUS_SUCCEED, CID))
    await client_writer.drain()
    return

async def runserver(ip, port):
    server = await asyncio.start_server(handle_client, ip, port)
    async with server:
        await server.serve_forever()
        
asyncio.run(runserver("127.0.0.1", 8080))