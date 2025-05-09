import ecies
import sys
import socket
import threading
import binascii

# New things
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

reader = SimpleMFRC522()

# Same as base client.py
HEADER = 64
PORT = 50512
FORMAT = "utf-8"
DCMSG = "DISCONNECT"
publicKey = b""

#SERVER = "10.1.1.52"
SERVER = "10.76.95.177"

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER, PORT))
connected = True
minReenterTime = 3

# Function for recieving and decoding messages
def receiveMsgs(client):
    global connected, publicKey
    while True:
        msgLength = client.recv(HEADER).decode(FORMAT)
        if msgLength != "":
            msgLength = int(msgLength)
            msg = client.recv(msgLength).decode(FORMAT)
            
            #print(SERVER, msg)
            if msg == "DISCONNECTED":
                print(SERVER, msg)
                connected = False
                sys.exit("Disconnected from server.")
            msgArgs = msg.split(":")
            if msgArgs[0] == "PUBLICKEY":
                publicKey = binascii.unhexlify(msgArgs[1])
            else:
                print(SERVER, msg)

        else:
            break

#Function for sending and encoding data
def send(client, msg):
    if publicKey == b"":
        print("[ERROR] Key is empty (Key has not been received).")
    else:
        encodedMsg = ecies.encrypt(publicKey, msg.encode("utf-8"))

        msgLength = f"{len(encodedMsg):<{HEADER}}".encode(FORMAT)
        client.send(msgLength)
        client.send(encodedMsg)

receiver = threading.Thread(target=receiveMsgs, args=[client])
receiver.start()

while True:
    if not connected:
        break
    try:
        pin = input('Pin: ')
        balance = input('Balance: ')
        print("Now place your tag to write")
        card = reader.read_id()
        reader.write(pin)
        send(client, f"REGISTERCARD:{card}:{pin}:{balance}")
    finally:
        GPIO.cleanup()
exit()
