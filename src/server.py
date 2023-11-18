import socket

server = socket.socket()
server.bind(("127.0.0.1", 80))

server.listen(50)
while True:
    print(f"[*] Listening 127.0.0.1:80")
    client, addr = server.accept()
    print(f"[{addr[1]}] Connected")
    
    while True:
        print(f"[{addr[1]}] Waiting messages")
        data = client.recv(512)
        if data == b"GET":
            print(f"[{addr[1]}] Send 'HTML'")
            client.send(b"HTML")
        elif data == b"CLOSE":
            print(f"[{addr[1]}] Close")
            client.close()
            break