import socket
import threading
import json
import hashlib
import random
import ecies
import binascii


# Stores our clients and their respective keys. addr: keyobject
clients = {}


def send(conn, msg):
    if conn == "BANK":
        print(str(msg))
    else:
        print("Sending...")
        msg = str(msg).encode(FORMAT)

        msgLength = str(len(msg))
        msgLength = f"{msgLength:>64}".encode(FORMAT) # Pads the header to 64 bytes
        conn.send(msgLength)
        print(f"HEADER OUT")
        conn.send(msg)
        print("MESSAGE OUT")


def start(plateManager):
    global running
    server.listen()

    while True: # Constantly accepting new clients
        try:
            if not running:
                break
            conn, addr = server.accept()
            clients[addr] = ecies.generate_key() # add a new keyobject to the clients dict
            thread = threading.Thread(target=handleClient, args=(conn, addr, plateManager))
            thread.start()
            print(f"ACTIVE CONNECTIONS: {threading.active_count() - 2}") # -2 because of the console thread and the start thread
        except OSError:
            break

# ERRORS:
# ERROR1 - User does not have sufficient balance to make the transaction (TRYCHARGE)
# ERROR2 - User does not exist (GETPLATEINFO, TRYCHARGE)
# ERROR3 - User already exists (REGISTERPLATE)
# ERROR4 - Invalid Authcode (SHUTDOWN)

def handleClient(conn, addr, plateManager):
    global running
    print(f"NEW CONNECTION: {addr} connected\n")
    
    connected = True
    # Send the initial public key
    send(conn, f"PUBLICKEY:{binascii.hexlify(clients[addr].public_key.format(True)).decode('utf-8')}")
    while connected:
        if not running:
            send(conn, DCMSG)
            break
        try:
            msgLength = conn.recv(HEADER) # Receive incoming headers from clients
            if msgLength:
                msgLength = int(msgLength)
                msg = conn.recv(msgLength)

                msg = ecies.decrypt(clients[addr].secret, msg).decode(FORMAT) # Receive X bytes specified by msgLength
                print(msg)

                if msg == DCMSG:
                    send(conn, "DISCONNECTED")
                    connected = False
                    print(f"{addr} Disconnected.")

                else:

                    handleArgs(conn, msg, plateManager)

                # Create new key pair and send to the client
                clients[addr] = ecies.generate_key()
                send(conn, f"PUBLICKEY:{binascii.hexlify(clients[addr].public_key.format(True)).decode('utf-8')}")
        except ConnectionResetError:
            connected = False
    print(f"{addr} disconnected.")
    del(clients[addr])


def handleArgs(conn, msg, plateManager):
    global running
    args = msg.split(":")
    sent = False

    if args[0] == "TRYCHARGE" and len(args) >= 3: # TRYCHARGE:[PLATE]:[PIN]:[AMOUNT]
        sent = False
        for user in plateManager.users:
            if user.plate == args[1] and user.pin == hash(args[2] + user.salt): # Find the corresponding user
                if (user.balance - float(args[3]) >= 0):
                    user.balance -= float(args[3])
                    plateManager.balance += float(args[3])
                    print(
                        f"CHARGED {user.plate} ${args[3]}.\nNEW USER BALANCE: ${user.balance}.\nNEW BANK BALANCE: ${plateManager.balance}")
                    send(conn, "TRUE")
                    sent = True
                    break
                else:
                    send(conn, "ERROR1")
        if not sent:
            send(conn, "ERROR2")

    elif args[0] == "GETBANKBALANCE": # GETBANKBALANCE
        send(conn, plateManager.balance)

    elif args[0] == "GETPLATEINFO" and len(args) >= 2: # GETPLATEINFO:[PLATE]
        for user in plateManager.users:
            if user.plate == args[1]:
                send(conn, f"{user.pin}:{user.balance}")
                sent = True
                break
        if not sent:
            send(conn, "ERROR2")

    elif args[0] == "REGISTERPLATE" and len(args) >= 4: # TRYREGISTERPLATE:[PLATE]:[PIN]:[BALANCE]
        plateExists = False
        for user in plateManager.users:
            if user.plate == args[1]:
                send(conn, "ERROR3")
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
                send(conn, "ERROR4")
    elif args[0] == "GETPLATES":
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
