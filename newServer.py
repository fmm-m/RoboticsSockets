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

class User:
    def __init__(self):
        self.plate = None
        self.pin = None
        self.balance = None

    def initialiseNewUser(self, plate, pin, balance):
        self.plate = plate
        self.pin = pin
        self.balance = balance

    def initialiseFromJson(self, plate, info):
        self.plate = plate
        self.pin = info["pin"]
        self.balance = info["balance"]

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
    def __init__(self, logFile):
        self.users = []
        self.logFile = logFile

    def load(self):
        f = open(self.logFile, "r")

        rawUserData = json.loads(f.read())


        self.users = []
        for plate, data in rawUserData.items():
            newUser = User()
            newUser.initialiseFromJson(plate, data)
            self.users.append(newUser)

        f.close()

    def save(self):
        f = open(self.logFile, "w")
        userDict = {}
        for user in self.users:
            print(user.toJSON())
            #f.write(f"{user.toJSON()}\n")

    def addUser(self, user):
        self.users.append(user)

    def __str__(self):

        returnStr = ""
        for user in self.users:
            returnStr = returnStr + f"{user.plate} || {user.pin} || {user.balance}\n"
        return returnStr




plateManager = PlateManager("data.json")
plateManager.load()

tobyOakes = User()
tobyOakes.initialiseNewUser("YIL90W", "8510", "930.13")
plateManager.addUser(tobyOakes)
print(plateManager)
plateManager.save()



HEADER = 64
FORMAT = "utf-8"
PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
DCMSG = "--DISCONNECT"
print(SERVER)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)


print("STARTING...")
start()