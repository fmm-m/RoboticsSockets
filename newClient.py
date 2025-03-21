import socket

HEADER = 64
PORT = 5050
FORMAT = "utf-8"
DCMSG = "--DISCONNECT"

SERVER = "10.1.1.42"

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER, PORT))

while True:
    msgOut = input(">>> ").encode(FORMAT)
    msgOutLength = f"{len(msgOut):<{HEADER}}".encode(FORMAT)
    client.send(msgOutLength)
    client.send(msgOut)