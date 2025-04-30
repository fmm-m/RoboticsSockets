from PIL import Image
import pytesseract
import cv2
import os, sys, inspect #For dynamic filepaths
import numpy as np
import time
import socket
import threading
import math

connected = False
HEADER = 64
PORT = 5050
FORMAT = "utf-8"
DCMSG = "DISCONNECT"

SERVER = "10.76.15.226"

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER, PORT))
connected = True
minReenterTime = 3

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def receiveMsgs(client):
    global connected
    while True:
        msgLength = int(client.recv(HEADER).decode(FORMAT))
        msg = client.recv(msgLength).decode(FORMAT)
        print(SERVER, msg)
        if msg == "DISCONNECTED":
            sys.exit("Disconnected from server.")
            connected = False

def timeToString(specificTime):
    currTime = time.localtime(specificTime)
    return f"{currTime[2]}/{currTime[1]}/{currTime[0]} {currTime[3]}:{currTime[4]}:{currTime[5]}"
# [YYYY, MM, DD, HH, MM, SS]

def send(client, msg):
    msg = msg.encode(FORMAT)
    msgLength = f"{len(msg):<{HEADER}}".encode(FORMAT)
    client.send(msgLength)
    client.send(msg)

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

                

manager = PlateManagerObj(1, "output.txt")
receiver = threading.Thread(target=receiveMsgs, args=[client])
receiver.start()

def processText(text: str):
   processedText = ""
   for letter in text:
      if letter.isalnum() and (letter.isupper() or letter.isdigit):
         processedText = processedText + letter
   return processedText

#Find the execution path and join it with the direct referencene
newFile = open("output.txt", "w")
cap = cv2.VideoCapture(2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

lastXPlates = ["", "", "", ""]

if not cap.isOpened():
    print("Cannot open camera")
    exit()
while True:
   if not connected:
       break
   ret, frame = cap.read()
   if not ret:
      print("Failed :(")
      break
   gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   blurred = cv2.GaussianBlur(gray, (3, 3), 0)
   #edged = cv2.Canny(blurred, 100, 200)
   ret, thresh = cv2.threshold(blurred, 70, 255, cv2.THRESH_BINARY)
   #blurredThresh = cv2.GaussianBlur(thresh, (3, 3), 0)
   cv2.imshow("Otsu", thresh)
   if ret:
      img = np.array(thresh)
      text = pytesseract.image_to_string(img)

      text = processText(text)
      print(text)
      if len(text) == 6:
         #print(text)
         lastXPlates.append(text)
         #print(lastXPlates)
         if lastXPlates[0] == lastXPlates[1] == lastXPlates[2] == lastXPlates[3]:
            print(text)
            manager.tryRegister(text)
      if len(lastXPlates) >= 4:
         del(lastXPlates[0])

      if text == "DISCONNECT":
          send(client, "DISCONNECT")
  
   if cv2.waitKey(1) == ord('q'):
      break
newFile.close()
# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()

