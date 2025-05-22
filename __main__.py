import ecies
from PIL import Image
import pytesseract
import cv2
import os, sys, inspect #For dynamic filepaths
import numpy as np
import time
import socket
import threading
import math
import binascii
import mfrc522
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
reader = mfrc522.SimpleMFRC522()

HEADER = 64
PORT = 50512
FORMAT = "utf-8"
DCMSG = "DISCONNECT"
publicKey = b""

SERVER = "10.76.95.177"
#SERVER = "10.1.1.156"

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER, PORT))
connected = True
minReenterTime = 3

font = cv2.FONT_HERSHEY_SIMPLEX

ROW1 = 27
ROW2 = 4
ROW3 = 22
ROW4 = 5

COL1 = 23
COL2 = 24
COL3 = 25


GPIO.setwarnings(False)

GPIO.setup(ROW1, GPIO.OUT)
GPIO.setup(ROW2, GPIO.OUT)
GPIO.setup(ROW3, GPIO.OUT)
GPIO.setup(ROW4, GPIO.OUT)

GPIO.setup(COL1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(COL2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(COL3, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def readRow(line, characters):
    pressedChars = []
    GPIO.output(line, GPIO.LOW)
    if GPIO.input(COL1) == GPIO.LOW:
        pressedChars.append(characters[0])
    if GPIO.input(COL2) == GPIO.LOW:
        pressedChars.append(characters[1])
    if GPIO.input(COL3) == GPIO.LOW:
        pressedChars.append(characters[2])
    GPIO.output(line, GPIO.HIGH)
    return pressedChars

def readKeypad():
    pressedChars = []
    pressedChars.append(readRow(ROW1, ["1", "2", "3"]))
    pressedChars.append(readRow(ROW2, ["4", "5", "6"]))
    pressedChars.append(readRow(ROW3, ["7", "8", "9"]))
    pressedChars.append(readRow(ROW4, ["*", "0", "#"]))
    filteredChars = []
    for char in pressedChars:
        for charKey in char:
            filteredChars.append(charKey)
    return filteredChars
    
def nextKeypadChar():
    pressedChars = readKeypad()
    while pressedChars == []:
        
        pressedChars = readKeypad()
        print(pressedChars)
    print(pressedChars)
    return pressedChars



#pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
serverHappy = False
serverResponse = ""
def receiveMsgs(client):
    global connected, publicKey, serverHappy, serverResponse
    while True:
        msgLength = client.recv(HEADER).decode(FORMAT)
        if msgLength != "":
            msgLength = int(msgLength)
            msg = client.recv(msgLength).decode(FORMAT)
            
            if msg == "DISCONNECTED":
                print(SERVER, msg)
                connected = False
                sys.exit("Disconnected from server.")
            msgArgs = msg.split(":")
            if msgArgs[0] == "PUBLICKEY":
                publicKey = binascii.unhexlify(msgArgs[1])
            else:
                serverResponse = msg
                print(SERVER, msg)
            if msgArgs[0] == "TRUE":
                serverHappy = True
            elif msgArgs[0] == "FALSE":
                serverHappy = False
           

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
    def __init__(self, plate, balance):
        self.plate = plate
        self.registrationDate = time.time()
        self.parked = False
        self.timeEntered = time.time()
        self.timeLeft = 0
        self.paymentHistory = []
        self.balance = balance


def getPin():
    pressedKeys = []
    pin = ""
    while True:
        keys = readKeypad()
        
        for i, key in enumerate(keys):
            if key == "#" and len(pressedKeys) >= 2:
                if pressedKeys[-2] not in ["#", "*"]:
                    pin += str(pressedKeys[-2])
                    pressedKeys = []
            else:
                pressedKeys.append(key)
        if len(pin) >= 4:
            break

    return pin




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

        
        self.users.append(User(plate, 100.0))
        self.log(f"Registered {plate}")
        self.processPlate(plate)
        
    
    def processPlate(self, plate):
        global serverHappy, serverResponse
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

                print("Please scan your card.")
                try:
                    
                    cardID = reader.read_id()
                    
                    print("Scanned")
                except Exception as e:
                    print(e)
                serverHappy = False
                print("Please enter your pin.")
                pin = getPin()
                
                
                print(pin)
                serverResponse = ""
                send(client, f"GETCARDINFO:{cardID}")
                time.sleep(3)
                print(serverResponse)
                if serverResponse == "ERROR2":
                    self.log("Card not yet registered. Registering...")
                    send(client, f"REGISTERCARD:{cardID}:{pin}:{100}")
                    time.sleep(1)
                
                send(client, f"TRYCHARGE:{cardID}:{pin}:{cost}")
                time.sleep(3)
                if serverHappy:
                    
                    self.log(f"Charged {currUser.plate} {cost} @ {timeToString(time.time())}")

                else:
                    self.log("Invalid Pin or balance too low :(. We'll let you through this time...")
                
                
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


manager = PlateManagerObj(1, r"/home/tobyfm/Desktop/output.txt")
receiver = threading.Thread(target=receiveMsgs, args=[client])
receiver.start()

def processText(text: str):
   processedText = ""
   for letter in text:
      if letter.isalnum() and (letter.isupper() or letter.isdigit):
         processedText = processedText + letter
   return processedText

#Find the execution path and join it with the direct referencene
newFile = open(r"/home/tobyfm/Desktop/output.txt", "w")
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

lastXPlates = ["", "", "", ""]
m = 120
lower = np.array([20, 0, 0])
upper = np.array([120, 80, 80])

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
   #hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
   #mask = cv2.inRange(frame, lower, upper)
   #frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)
   #masked = cv2.bitwise_and(frame, frame, mask=mask)
   
#    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
#    edged = cv2.Canny(blurred, 100, 200)
#    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, 20)
#    blurredThresh = cv2.GaussianBlur(thresh, (5, 5), 0)
#    ret, thresh2 = cv2.threshold(blurredThresh, 254, 255, cv2.THRESH_BINARY)   
#    output = edged

#    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
#    countourArea = []
#    approxes = []
#    for i,cnt in enumerate(contours):
#       area = cv2.contourArea(cnt)
#       approx = cv2.approxPolyDP(cnt, 0.02*cv2.arcLength(cnt, True),True)
#       #coordinate
#       x = approx.ravel()[0]
#       y = approx.ravel()[1]
#       #print(x)
#       if len(approx) == 4:
#         countourArea.append((i, area))
#       approxes.append(approx)


#    approx = approxes[sorted(countourArea, key=lambda x: x[1])[-1][0]]

#    cv2.drawContours(frame,[approx],0,(0,0,0),2) #5 is thickness
#    cv2.putText(frame,"Rectangle",(x,y),font,1,(0,0,0))
#    approx = np.array(approx)
#    #print(approx)
#    #for i, coords in enumerate(approx):
#         #   cv2.circle(frame, coords[0], 5, [255- i * 64, 64 * i, 0])
#    perspectiveTransform = cv2.getPerspectiveTransform(np.float32(approx), np.float32([(320, 20),(0, 20), (0, 220), (320, 220)]))
#    output = cv2.warpPerspective(thresh, perspectiveTransform, (320, 240))
         
#    cv2.imshow("Output", output)
#    cv2.imshow("BlurredThresh", blurredThresh)
#    cv2.imshow("Frame", frame)

   gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian Blur to remove noise
   blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Edge detection (Canny) to highlight plate contours
   edges = cv2.Canny(blurred, 100, 200)

    # Find contours to locate the license plate
   contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sort contours based on area (descending order)
   contours = sorted(contours, key=cv2.contourArea, reverse=True)

   plate_contour = None
   for contour in contours:
        # Approximate the contour to a polygon
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Check if the contour has 4 vertices (which may be a rectangle, typical for plates)
        if len(approx) == 4:
            plate_contour = approx
            break

   if plate_contour is not None:
        # Draw a bounding box around the detected license plate
        x, y, w, h = cv2.boundingRect(plate_contour)
        plate_image = gray[y:y + h, x:x + w]

        # Apply thresholding to binarize the plate area
        _, thresh = cv2.threshold(plate_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Perform OCR on the detected plate area
        text = pytesseract.image_to_string(thresh, config='--psm 8 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')  # Treat it as a single word
   cv2.imshow("Output", thresh)
   if ret:
      

      text = processText(text)

      if len(text) == 6:
         print(text)
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
GPIO.cleanup()

newFile.close()
# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()

