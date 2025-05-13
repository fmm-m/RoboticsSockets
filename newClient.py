import socket
import threading



def start():
    global running
    while True:
        if not running:
            break
        msgOut = input(">>> ").encode(FORMAT)
        msgOutLength = f"{len(msgOut):<{HEADER}}".encode(FORMAT)
        client.send(msgOutLength)
        client.send(msgOut)

def receive():
    global running
    while True:
        msgLength = int(client.recv(HEADER).decode(FORMAT))
        msg = client.recv(msgLength).decode(FORMAT)
        if msg == DCMSG:
            running = False
            break
        print(msg)



HEADER = 64
PORT = 5050
FORMAT = "utf-8"
DCMSG = "DISCONNECT"
SERVER = "10.1.1.42"

running = True

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER, PORT))

receiver = threading.Thread(target=receive)
receiver.start()

start()