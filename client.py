import ecies
import sys
import socket
import threading
import binascii

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
   text = input("1. Test charging a card\n2. Get Bank Balance\n3. Get CARD Info\n4. Try registering new card\n5. Disconnect")
   
   if text == "1": # TRYCHARGE:[CARDNUMBER]:[PIN]:[AMOUNT]
       args = input("Please enter CARDNUMBER:PIN:AMOUNT ")
       send(client, f"TRYCHARGE:{args}")
   elif text == "2": # GETBANKBALANCE
       send(client, "GETBANKBALANCE:")
   elif text == "3":    # GETCARDINFO:[CARDNUMBER]
       args = input("Please enter CARDNUMBER ")
       send(client, f"GETCARDINFO:{args}")
   elif text == "4":    # REGISTERCARD:[CARD]:[PIN]:[BALANCE]
       args = input("Please enter CARD:PIN:BALANCE ")
       send(client, f"REGISTERCARD:{args}")
   elif text == "5":
        send(client, "DISCONNECT")
        break
exit()
