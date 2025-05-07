import socket
import threading
import json
import hashlib
import random
import ecies
import binascii

sha = hashlib.sha256()

keys = ecies.generate_key()

secretKey = keys.secret
PUBLICKEY = keys.public_key.format(True)






def handleClient(conn, addr, plateManager):
    global running
    print(f"NEW CONNECTION: {addr} connected\n")
    
    connected = True
    send(conn, f"PUBLICKEY:{binascii.hexlify(PUBLICKEY).decode('utf-8')}")
    while connected:
        if not running:
            send(conn, DCMSG)
            break
        try:
            msgLength = conn.recv(HEADER)
            if msgLength:
                msgLength = int(msgLength)
                msg = conn.recv(msgLength)

                msg = ecies.decrypt(secretKey, msg).decode(FORMAT)
                print(msg)

                if msg == DCMSG:
                    send(conn, "DISCONNECTED")
                    connected = False
                    print(f"{addr} Disconnected.")

                else:

                    handleArgs(conn, msg, plateManager)
        except ConnectionResetError:
            connected = False
    print(f"{addr} disconnected.")


def send(conn, msg):
    if conn == "BANK":
        print(str(msg))
    else:
        print("Sending...")
        msg = str(msg).encode(FORMAT)

        msgLength = str(len(msg))
        msgLength = f"{msgLength:>64}".encode(FORMAT)
        conn.send(msgLength)
        print(f"HEADER OUT")
        conn.send(msg)
        print("MESSAGE OUT")

def start(plateManager):
    global running
    server.listen()

    while True:
        try:
            if not running:
                break
            conn, addr = server.accept()

            thread = threading.Thread(target=handleClient, args=(conn, addr, plateManager))
            thread.start()
            print(f"ACTIVE CONNECTIONS: {threading.active_count() - 2}")
        except OSError:
            break


def handleArgs(conn, msg, plateManager):
    global running
    args = msg.split(":")
    sent = False

    if args[0] == "TRYCHARGE" and len(args) >= 3: # TRYCHARGE:[PLATE]:[PIN]:[AMOUNT]

        for user in plateManager.users:
            if user.plate == args[1] and user.pin == hash(args[2] + user.salt):
                if (user.balance - float(args[3]) >= 0):
                    user.balance -= float(args[3])
                    plateManager.balance += float(args[3])
                    print(
                        f"CHARGED {user.plate} ${args[3]}.\nNEW USER BALANCE: ${user.balance}.\nNEW BANK BALANCE: ${plateManager.balance}")
                    send(conn, "TRUE")
                    break
                else:
                    send(conn, "NULL")

    elif args[0] == "GETBANKBALANCE": # GETBANKBALANCE
        send(conn, plateManager.balance)

    elif args[0] == "GETPLATEINFO" and len(args) >= 2: # GETPLATEINFO:[PLATE]
        for user in plateManager.users:
            if user.plate == args[1]:
                send(conn, f"{user.pin}:{user.balance}")
                sent = True
                break
        if not sent:
            send(conn, "NULL")

    elif args[0] == "REGISTERPLATE" and len(args) >= 4: # TRYREGISTERPLATE:[PLATE]:[PIN]:[BALANCE]
        plateExists = False
        for user in plateManager.users:
            if user.plate == args[1]:
                send(conn, "NULL")
                plateExists = True
                break

        if not plateExists:
            newUser = User()
            newUser.initialiseNewUser(args[1], int(args[2]), float(args[3]))
            plateManager.users.append(newUser)
            send(conn, "TRUE")


    elif args[0] == "SHUTDOWN": # SHUTDOWN:[AUTHCODE]
        if len(args) == 2:

            if hash(args[1]) == AUTHCODE:

                plateManager.save()
                running = False
                server.close()
                plateManager.save()
            else:
                send(conn, "NULL")
    elif args[0] == "GETPLATES":
        print("--Plates--")
        for user in plateManager.users:
            print(str(user))
            send(conn, user)




def getConsoleInput(plateManager):
    global running
    while running:
        msg = input(">>> ")
        handleArgs("BANK", msg, plateManager)

def hash(text):
    hSha = hashlib.sha256()
    hSha.update(text.encode())
    return hSha.hexdigest()

class User:
    def __init__(self):
        self.plate = None
        self.pin = None
        self.salt = ""
        self.balance = None

    def initialiseNewUser(self, plate, pin, balance):
        self.plate = plate

        self.salt = ""
        for _ in range(0, 32):
            self.salt += chr(random.randrange(40, 127))
        self.pin = hash(str(pin) + self.salt)
        self.balance = float(balance)

    def initialiseFromJson(self, plate, info):
        self.plate = plate
        self.pin = info["pin"]
        self.salt = info["salt"]
        self.balance = float(info["balance"])

    def toJSON(self):

        return json.dumps({
            self.plate : {
                "pin" : self.pin,
                "salt" : self.salt,
                "balance" : self.balance
            }
        })

    def setPin(self, oldPin, newPin):

        if hash(oldPin + self.salt) == self.pin:
            self.pin = newPin
    def __str__(self):
        return f"{self.plate},{self.balance},{self.pin},{self.salt}"


class PlateManager:
    def __init__(self, logFile, balance, bankFile):
        self.users = []
        self.logFile = logFile
        self.bankFile = bankFile
        self.balance = balance

    def load(self):

        fb = open(self.bankFile, "r")
        try:
            self.balance = float(fb.read())
        except:
            print("No pre-existing balance. Setting balance to 0...")
            self.balance = 0
        f = open(self.logFile, "r")

        rawData = f.read()
        if rawData != "":

            loadedData = json.loads(rawData)


            self.users = []
            for plate, info in loadedData.items():
                newUser = User()
                newUser.initialiseFromJson(plate, info)
                self.users.append(newUser)

        f.close()

    def save(self):
        fb = open(self.bankFile, "w")
        fb.write(str(self.balance))
        f = open(self.logFile, "w")
        userDict = {}
        for user in self.users:
            userDict[user.plate] = {"pin": user.pin, "balance": user.balance, "salt": user.salt}
        print(json.dumps(userDict))
        f.write(json.dumps(userDict))

    def addUser(self, user):
        self.users.append(user)

    def __str__(self):

        returnStr = f"BANK OF MICAH:\nBALANCE: {self.balance}\n\n"
        returnStr += "PLATE  || BALANCE\n"
        returnStr += "-----------------\n"
        for user in self.users:
            returnStr += f"{user.plate} || ${user.balance}\n"
        return returnStr


HEADER = 64
FORMAT = "utf-8"
PORT = 50512
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
DCMSG = "DISCONNECT"
AUTHCODE = "fb7edbc4da086ca9fc14dfa07217632fde09f93747ef638de86edd9bbb4c7533"
running = True
print(SERVER)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

plateManager = PlateManager("data.json", 0.0, "bankData.txt")
plateManager.load()
print(plateManager)

print("STARTING...")
handleConsole = threading.Thread(target=getConsoleInput,args=[plateManager])
handleConsole.start()

start(plateManager)

