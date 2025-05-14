import socket
import threading
import json
import hashlib
import random
import ecies
import binascii


# Stores our clients and their respective keys. addr: keyobject
addressKeyPairs = {}
clients = []


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
            addressKeyPairs[addr] = ecies.generate_key() # add a new keyobject to the clients dict
            thread = threading.Thread(target=handleClient, args=(conn, addr, plateManager))
            clients.append(conn)
            thread.start()
            print(f"ACTIVE CONNECTIONS: {threading.active_count() - 2}") # -2 because of the console thread and the start thread
        except OSError:
            break

# ERRORS:
# ERROR0 - Pin is wrong (TRYCHARGE)
# ERROR1 - User does not have sufficient balance to make the transaction (TRYCHARGE)
# ERROR2 - User does not exist (GETPLATEINFO, TRYCHARGE)
# ERROR3 - User already exists (REGISTERPLATE)
# ERROR4 - Invalid Authcode (SHUTDOWN)
# ERROR5 - Supplied a negative value (TRYCHARGE, REGISTERPLATE)

def handleClient(conn, addr, plateManager):
    global running
    print(f"NEW CONNECTION: {addr} connected\n")
    
    connected = True
    # Send the initial public key
    send(conn, f"PUBLICKEY:{binascii.hexlify(addressKeyPairs[addr].public_key.format(True)).decode('utf-8')}")
    while connected:
        if not running:
            send(conn, DCMSG)
            break
        try:
            msgLength = conn.recv(HEADER) # Receive incoming headers from clients
            if msgLength:
                msgLength = int(msgLength)
                msg = conn.recv(msgLength)

                msg = ecies.decrypt(addressKeyPairs[addr].secret, msg).decode(FORMAT) # Receive X bytes specified by msgLength
                print(msg)

                if msg == DCMSG:
                    send(conn, "DISCONNECTED")
                    connected = False
                    print(f"{addr} Disconnected.")

                else:

                    handleArgs(conn, msg, plateManager)

                # Create new key pair and send to the client
                addressKeyPairs[addr] = ecies.generate_key()
                send(conn, f"PUBLICKEY:{binascii.hexlify(addressKeyPairs[addr].public_key.format(True)).decode('utf-8')}")
        except ConnectionResetError:
            connected = False
    print(f"{addr} disconnected.")
    del(addressKeyPairs[addr])

def broadcast(msg):
    for client in clients:
        try:
            send(client, msg)
        except:
            pass


def handleArgs(conn, msg, plateManager):
    global running
    args = msg.split(":")
    sent = False
    if conn == "BANK":
        if args[0] == "BROADCAST" and len(args) >= 2:
            broadcast("Bank of Micah Says: " + args[1])

    if args[0] == "TRYCHARGE" and len(args) >= 3: # TRYCHARGE:[PLATE]:[PIN]:[AMOUNT]
        sent = False
        userCheck = False
        for user in plateManager.users:
            if user.plate == args[1]: # Find the corresponding user
                userCheck = True
                if user.pin == hash(args[2] + user.salt):
                    if (user.balance - float(args[3]) >= 0):
                        if !(args[3] > 0):
                            send(conn, "ERROR5")
                        else:
                            user.balance -= float(args[3])
                            plateManager.balance += float(args[3])
                            print(
                                f"CHARGED {user.plate} ${args[3]}.\nNEW USER BALANCE: ${user.balance}.\nNEW BANK BALANCE: ${plateManager.balance}")
                            send(conn, "TRUE")
                            sent = True
                            plateManager.save()
                            break
                    else:
                        send(conn, "ERROR1")
                        break
        if not sent:
            if not userCheck:
                send(conn, "ERROR2")
            else:
                send(conn, "ERROR0")

    elif args[0] == "GETBANKBALANCE": # GETBANKBALANCE
        send(conn, plateManager.balance)

    elif args[0] == "GETCARDINFO" and len(args) >= 2: # GETPLATEINFO:[PLATE]
        for user in plateManager.users:
            if user.plate == args[1]:
                send(conn, f"{user.pin}:{user.balance}")
                sent = True
                break
        if not sent:
            send(conn, "ERROR2")

    elif args[0] == "REGISTERCARD" and len(args) >= 4: # TRYREGISTERPLATE:[PLATE]:[PIN]:[BALANCE]
        plateExists = False
        for user in plateManager.users:
            if user.plate == args[1]:
                send(conn, "ERROR3")
                plateExists = True
                break

        if not plateExists:
            if !(args[3] > 0):
                send(conn, "ERROR5")
            else:
                newUser = User()
                newUser.initialiseNewUser(args[1], int(args[2]), float(args[3]))
                plateManager.users.append(newUser)
                plateManager.save()
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
    elif args[0] == "GETCARDS":
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
#SERVER = socket.gethostbyname(socket.gethostname())
SERVER = "10.76.95.177"
ADDR = (SERVER, PORT)
DCMSG = "DISCONNECT"
AUTHCODE = "a0f3285b07c26c0dcd2191447f391170d06035e8d57e31a048ba87074f3a9a15"
# AUTHCODE = "Password1234"
running = True
print(SERVER)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

plateManager = PlateManager("/home/micah/programming/sockets/data.json", 0.0, "/home/micah/programming/sockets/bankData.txt")
plateManager.load()
print(plateManager)

print("STARTING...")
handleConsole = threading.Thread(target=getConsoleInput,args=[plateManager])
handleConsole.start()

start(plateManager)
