import ecies
import os, sys, inspect #For dynamic filepaths
import time
import socket
import threading
import math
import binascii

HEADER = 64
PORT = 50512
FORMAT = "utf-8"
DCMSG = "DISCONNECT"
publicKey = b""

#SERVER = "10.1.1.52"
SERVER = "127.0.1.1"

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER, PORT))
connected = True
minReenterTime = 3

def receiveMsgs(client):
    global connected, publicKey
    while True:
        msgLength = client.recv(HEADER).decode(FORMAT)
        if msgLength != "":
            msgLength = int(msgLength)
            msg = client.recv(msgLength).decode(FORMAT)
            print(SERVER, msg)
            if msg == "DISCONNECTED":
                connected = False
                sys.exit("Disconnected from server.")
            msgArgs = msg.split(":")
            if msgArgs[0] == "PUBLICKEY":
                publicKey = binascii.unhexlify(msgArgs[1])

        else:
            break

def timeToString(specificTime):
    currTime = time.localtime(specificTime)
    return f"{currTime[2]}/{currTime[1]}/{currTime[0]} {currTime[3]}:{currTime[4]}:{currTime[5]}"
# [YYYY, MM, DD, HH, MM, SS]

def send(client, msg):
    if publicKey == b"":
        print("[ERROR] Key is empty (Key has not been received).")
    else:
        encodedMsg = ecies.encrypt(publicKey, msg.encode("utf-8"))

        msgLength = f"{len(encodedMsg):<{HEADER}}".encode(FORMAT)
        client.send(msgLength)
        client.send(encodedMsg)

class User:
    def __init__(self, plate, pin, balance):
        self.plate = plate
        self.registrationDate = time.time()
        self.parked = False
        self.timeEntered = time.time()
        self.timeLeft = 0
        self.paymentHistory = []
        self.pin = pin
        self.balance = balance
        send(client, f"REGISTERPLATE:{self.plate}:{self.pin}:{self.balance}")
    def charge(self, charge):
        send(client, f"TRYCHARGE:{self.plate}:{self.pin}:{charge}")





class PlateManagerObj:
    def __init__(self, rate, logFile):
        self.users = []
        self.rate = rate # Cost p/second
        self.logFile = open(logFile, "w")
    
    def log(self, msg):
        print(msg)
        self.logFile.write(f"\n{msg}")
        

    def tryRegister(self, plate):
        for user in self.users:
            if user.plate == plate:
                self.processPlate(plate)
                return False
        while True:
            try:
                pin = int(input("Please enter a 4 digit pin: "))
                break
            except:
                pass
        
        self.users.append(User(plate, pin, 100.0))
        self.log(f"Registered {plate}")
        self.processPlate(plate)
        
    
    def processPlate(self, plate):
        for user in self.users:
            if user.plate == plate:
                currUser = user
                break
        
        if currUser.parked:
            if time.time() - currUser.timeEntered > minReenterTime:
                self.log(f"{currUser.plate} LEFT @ {timeToString(time.time())}")
                currUser.parked = not currUser.parked
                currUser.timeLeft = time.time()
                timeParked = currUser.timeLeft - currUser.timeEntered
                cost = math.floor(self.rate * timeParked * 10) / 10
                
                send(client, f"TRYCHARGE:{currUser.plate}:{currUser.pin}:{cost}")
                self.log(f"Charged {currUser.plate} {cost} @ {timeToString(time.time())}")
                
                
        else:
            if time.time() - currUser.timeLeft > minReenterTime:
                self.log(f"{currUser.plate} ENTERED @ {timeToString(time.time())}")

                currUser.parked = not currUser.parked
                currUser.timeEntered = time.time()

def consoleSend() -> None:
    while True:
        words = input(">>> ")
        send(client, words)
        if words == "END":
            break
    return None
consoleS = threading.Thread(target=consoleSend)
consoleS.start()


manager = PlateManagerObj(1, "output.txt")
receiver = threading.Thread(target=receiveMsgs, args=[client])
receiver.start()

while True:
   if not connected:
       break
   text = input()
   print("1. Test charging a car")
   print("2. Get Bank Balance")
   print("3. Get Plate Info")
   print("4. Try registering new card")
   print("5. Disconnect")
   if text == "1": # TRYCHARGE:[PLATE]:[PIN]:[AMOUNT]
       print("Please enter PLATE:PIN:AMOUNT")
       args = input()
       send(client, "TRYCHARGE:"+args)
   elif text == "2": # GETBANKBALANCE
       send(client, "GETBANKBALANCE:")
   elif text == "3":    # GETPLATEINFO:[PLATE]
       print("Please enter PLATE")
       args = input()
       send(client, "GETPLATEINFO:"+args)
   elif text == "3":    # TRYREGISTERPLATE:[PLATE]:[PIN]:[BALANCE]
       print("Please enter PLATE:PIN:BALANCE")
       args = input()
       send(client, "TRYREGISTERPLATE:"+args)
   elif text == "5":
        send(client, "DISCONNECT")
        break
