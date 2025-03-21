import socket
import threading

HEADER = 64
FORMAT = "utf-8"
PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
DCMSG = "--DISCONNECT"
print(SERVER)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server.bind((SERVER, PORT))

def handleClient(conn, addr):
    print(f"NEW CONNECTION: {addr} connected")
    
    connected = True
    while connected:

        msgLength = conn.recv(HEADER)
        if msgLength:
            msgLength = int(msgLength)
            msg = str(conn.recv(msgLength).decode(FORMAT))
            
            if msg == DCMSG:
                connected = False
                print(f"{addr} Disconnected.")
            else:
                print(f"{addr}: {msg}")



def start():
    server.listen()

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handleClient, args=(conn, addr))
        thread.start()
        print(f"ACTIVE CONNECTIONS: {threading.active_count() - 1}")
        

print("STARTING...")
start()