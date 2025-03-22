import socket
import threading
import json


def handleClient(conn, addr, plateManager):
    global running
    print(f"NEW CONNECTION: {addr} connected")
    
    connected = True
    while connected:
        if not running:
            send(conn, DCMSG)
            break
        try:
            msgLength = conn.recv(HEADER)
            if msgLength:
                msgLength = int(msgLength)
                msg = str(conn.recv(msgLength).decode(FORMAT))

                if msg == DCMSG:
                    connected = False
                    print(f"{addr} Disconnected.")
                else:
                    print(msg)
                    handleArgs(conn, msg, plateManager)
        except ConnectionResetError:
            connected = False


def send(conn, msg):
    if conn == "BANK":
        print(str(msg))
    else:
        print("Sending...")
        msg = str(msg).encode(FORMAT)

        msgLength = str(len(msg)).encode(FORMAT)
        print(msgLength)
        conn.send(msgLength)
        print("Sent Header")
        conn.send(msg)
        print("Sent Message")

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
            print(f"ACTIVE CONNECTIONS: {threading.active_count() - 1}")
        except OSError:
            break


def handleArgs(conn, msg, plateManager):
    global running
    args = msg.split(":")
    sent = False

    if args[0] == "TRYCHARGE" and len(args) >= 3: # TRYCHARGE:[PLATE]:[PIN]:[AMOUNT]

        for user in plateManager.users:
            if user.plate == args[1] and user.pin == int(args[2]):
                if (user.balance - float(args[3]) >= 0):
                    user.balance -= float(args[3])
                    plateManager.balance += float(args[3])
                    print(
                        f"CHARGED {user.plate} ${args[3]}.\nNEW USER BALANCE: ${user.balance}.\nNEW BANK BALANCE: ${plateManager.balance}")
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

    elif args[0] == "SHUTDOWN": # SHUTDOWN:[AUTHCODE]
        if len(args) == 2:
            if args[1] == AUTHCODE:
                plateManager.save()
                running = False
                server.close()




def getConsoleInput(plateManager):
    global running
    while running:
        msg = input("")
        handleArgs("BANK", msg, plateManager)


class User:
    def __init__(self):
        self.plate = None
        self.pin = None
        self.balance = None

    def initialiseNewUser(self, plate, pin, balance):
        self.plate = plate
        self.pin = int(pin)
        self.balance = float(balance)

    def initialiseFromJson(self, plate, info):
        self.plate = plate
        self.pin = int(info["pin"])
        self.balance = float(info["balance"])

    def toJSON(self):

        return json.dumps({
            self.plate : {
                "pin" : self.pin,
                "balance" : self.balance
            }
        })

    def setPin(self, oldPin, newPin):
        if oldPin == self.pin:
            self.pin = newPin


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

        try:
            rawUserData = json.loads(f.read())
        except:
            print("No pre-existing data")
            rawUserData = {}

        self.users = []
        for plate, data in rawUserData.items():
            newUser = User()
            newUser.initialiseFromJson(plate, data)
            self.users.append(newUser)

        f.close()

    def save(self):
        fb = open(self.bankFile, "w")
        fb.write(str(self.balance))
        f = open(self.logFile, "w")
        userDict = {}
        for user in self.users:
            print(user.toJSON())

            f.write(f"{user.toJSON()}\n")

    def addUser(self, user):
        self.users.append(user)

    def __str__(self):

        returnStr = f"BANK OF MICAH:\nBALANCE: {self.balance}\n"
        for user in self.users:
            returnStr = returnStr + f"{user.plate} || {user.pin} || {user.balance}\n"
        return returnStr


HEADER = 64
FORMAT = "utf-8"
PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
DCMSG = "DISCONNECT"
AUTHCODE = "ELMO"
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

