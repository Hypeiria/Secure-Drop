"""
This will activate/deactivate the virutal enviornment
source .venv/bin/activate
deactivate

This will install a pip package
pip install <package_name>

This will save installed packages 
pip freeze > requirements.txt

This will install packages 
pip install -r requirements.txt
"""


import hashlib      # hashing the passwords, (apparently crypt module is depracated)
import getpass      # inputing password without echo
import os           # might chmod commands to "restrict database access"
from Crypto.Cipher import AES  # AES encryption for database files?
import json # for contacts
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization # these two imports are for private/public key generation upon registration
import threading # for multithreading
import time # for multithreading
import socket
import ssl # for tls
import sys # for UDP connection
import queue # for a queue of file transfer requests
import smtplib # for email verification
import random # for email verification code
from email.message import EmailMessage # for email sending
from datetime import datetime, timedelta # for email verification timeout
##########################
# For real use, these would be stored on a secure server
# Example: example@gmail.com
# app password = cvio osck jkkm smrm
from email_validator import validate_email, EmailNotValidError # for email validation

incomingFileTransferRequests = queue.Queue()

#################################
# MILESTONE 1 (User Registration)
# function takes user input to store in the database and register a new user
# returns 1 upon success, -1 for failure
def registerUser():
    inp1 = input("\nEnter Full Name: ")
    inp2 = get_valid_email() # will use the function to check if the email is actually valid
    verifyEmailAddressFlag = input("TESTING PURPOSES: Enter 0 to turn off email verification: ")
    if verifyEmailAddressFlag != "0":
        if verifyEmail(inp2) == False:
            print("Unable to Verify Your Email Address.")
            os._exit(0)
        else:
            print("Email verified!")
    inp3 = getpass.getpass(prompt = "Enter Password: ")
    inp4 = getpass.getpass(prompt = "Re-enter Password: ")  
    if (inp3 != inp4):
        print("\nPasswords do not match!")
        return -1

    print("\nPasswords Match!")
    if not os.path.exists("user.txt"):
        open("user.txt", "w").close()
    file = open("user.txt", "w")
    file.write(inp1 + "\n" + inp2 + "\n" + passHasher(inp3))
    file.close()

    # create/check for keys directory
    if not (os.path.exists("keys")):
        os.makedirs("keys")
    
    # generate a private key (2048)
    private_key = rsa.generate_private_key(
        public_exponent = 65537,
        key_size = 2048,
    )

    # write private key to ./keys/private.pem
    with open(f"keys/private.pem", "wb") as priv_file:
        priv_file.write(
            private_key.private_bytes(
                encoding = serialization.Encoding.PEM,
                format = serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        )
    
    # write public key to ./keys/public.pem
    public_key = private_key.public_key()
    with open(f"keys/public.pem", "wb") as pub_file:
        pub_file.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        )

    return 1
# end of registerUser()


def get_valid_email():
    while True:
        email = input("Enter Email Address: ")
        try:
            # Validate the email format and domain
            validate_email(email)
            return email
        except EmailNotValidError as e:
            print(f"Please enter a valid email: {e}")
            # Keep prompting until valid
# end of get_valid_email()

################################
# MILESTONE 1 EMAIL VERIFICATION
################################
def verifyEmail(emailAddress):
    code = str(random.randint(100000, 999999))
    secureDropEmail = "example@gmail.com"
    appPassword = "example"

    subject = "Verify Your SecureDrop Email Address"
    body = f"Here is your Verifcation Code (Valid for 15 minutes): {code}"

    # create the email
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = secureDropEmail
    msg["To"] = emailAddress

    try:
        # connect to gmail's SMTP server
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(secureDropEmail, appPassword)
            server.send_message(msg)
            #print(f"Verification email sent to {emailAddress}!")
    except Exception as e:
        print("Failed to send email:", e)

    # start clock
    startTime = datetime.now()
    # set to expire in 15 minutes
    expirationTime = startTime + timedelta(minutes=15)

    # test if user can verify code
    stillVerifying = True
    verificationAttempts = 0
    while(stillVerifying):
        verifyCode = input("Enter in Verification Code: ")
        verificationAttempts += 1
        if datetime.now() > expirationTime:
            print("Verification code expired!")
            return False
        elif verificationAttempts > 4:
            print("Too many failed attempts!")
            return False
        elif code == verifyCode:
            return True
        else:
            print("Wrong code. Please try again.")
    return False


#################################
# MILESTONE 2 (User Login)
# function allows a user to login
# return 1 upon success, -1 for failure
def userLogin():
    inp1 = input("\nEnter Email Address: ")
    inp2 = getpass.getpass(prompt = "Enter Password: ")

    file = open("user.txt", "r")
    userEmail = file.readline()
    userEmail = file.readline().strip() # strip needed to remove read newline
    userPass = file.readline().strip()

    file.close()

    if inp1 != userEmail:
        print("No Email Address Was Found")
        return -1
    if passHasher(inp2) == userPass:
        return 1 # successful user login
    return -1 # return -1 if user inputs wrong password
# end of userLogin()

def acceptRequest():
    senderEmail, senderIP, fileSizeGigs = incomingFileTransferRequests.get()
    print(f"Recieved file transfer request from {senderEmail}.")
    fileSizeGigs = float(fileSizeGigs)
    print(f"File size = {fileSizeGigs:.3f} GB")
    invalidInput = True
    messageType = ""
    while(invalidInput):
        userInput = input("Do you accept? [y/n]: ").strip().lower()
        if userInput == "y":
            messageType = "file-transfer-accept"
            invalidInput = False
        elif userInput == "n":
            messageType = "file-transfer-deny"
            invalidInput = False
        else:
            print("Invalid input. Please enter y or n.")
    if (messageType == "file-transfer-accept") == False:
        print("Denied file transfer request.")
        return
    else: # accepted request
        # start TCP connection with senderIP
        print("Accepted file transfer request.")
        acceptFileTransfer(senderIP)

def acceptFileTransfer(senderIP):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(('0.0.0.0', 5143))
    server_sock.listen(5)
    
    server_sock.settimeout(10)

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile='server.crt', keyfile='server.key')

    try:
        # Accept a connection
        client_sock, addr = server_sock.accept()
        # print("Connection from:", addr)

        # Wrap the plain socket with the SSL context to secure it
        with context.wrap_socket(client_sock, server_side=True) as tls_conn:
            # Now tls_conn is a secure SSL socket.
            outfile = f"received_{int(time.time())}.bin"
            with open(outfile, "wb") as f:
                for chunk in iter(lambda: tls_conn.recv(4096), b""):
                    f.write(chunk)
            #tls_conn.shutdown(socket.SHUT_RDWR)
            print(f"Saved file as {outfile}")
            # tls_conn.sendall(b"")
    except socket.timeout:
        print("No connection was established within 10 seconds.")
    finally:
        server_sock.close()


#################################
# MILESTONE 3 (Adding Contacts)
# some sort of loop that works as a secure drop terminal of sorts...?
# read and write to the contacts.json database
# no input, no returns
def terminalLoop():
    while True:
        if incomingFileTransferRequests.qsize() > 0:
            acceptRequest()
        userCommand = input("secure drop> ").strip().lower() # get in lowercase
        if userCommand == "help":
            print()
            print("add -> Add a new contact")
            print("list -> List all online contacts")
            print("send -> Transfer file to contact")
            print("exit -> Exit SecureDrop")
            print("Press enter to refresh to recieve a file.")
        elif userCommand == "add":
            addContact()
        elif userCommand == "exit":
            print("Exiting SecureDrop...")
            os._exit(0) # exit command for multithreading
        elif userCommand == "list":
            listContacts(True)
        elif userCommand == "send":
            sendFileRequest()
        elif userCommand == "":
            print("Refreshing...")
        else:
            print("Invalid command. Type help to see list of valid commands.")


def broadcastMessage(inputMessage, host):
    broadcastSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcastSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) # turn broadcast setting on
    port = int(5142) # chosen port number
    msg = inputMessage # the message you want to send to the server
    msg = msg.encode("utf-8")
    broadcastSocket.sendto(msg, (host,port)) ## the method transmits UDP message ##sendto(bytes, flags, address)
    broadcastSocket.close()

# MILESTONE 3 Add contacts
def addContact():
    print()
    name = input("\nEnter Full Name: ")
    email = input("Enter Email Address: ")
    active = 0

    contact = {"name": name, "email": email, "active": active}
    contacts = []
    # load contacts if file exists
    if os.path.exists("contacts.json"):
        if os.path.getsize("contacts.json") == 0:
            with open("contacts.json", "w") as f:
                f.write("[]") # if empty write [] to file
        with open("contacts.json", "r") as f:
            contacts = json.load(f)
    else: # if file does not exist
            with open("contacts.json", "w") as f:
                f.write("[]")
    
    # check if contact already exists,
    # so you can update contact 
    updated = False
    for i in range(len(contacts)):
        if contacts[i]["email"] == email:
            contacts[i] = contact
            updated = True
            break
    if not updated:
        contacts.append(contact)
        print("Contact added")
    else:
        print("Contact updated")
    
    with open("contacts.json", "w") as f:
        json.dump(contacts, f, indent = 2)

## Function will take an input string 
# returns a hashed sha256 string
def passHasher(input: str):
    sha256 = hashlib.sha256()
    sha256.update(input.encode())  # input str converted to byte stream before hashing
    return sha256.hexdigest()
# end of passHasher


def listenForBroadcast():
    while True: # change this while True in the future!
        # CREATE THE SOCKET HERE
        sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) ## AF_INET is family of protocols. SOCK_DGRAM is a type that for connectionless protocols
        host = ''  # localhost -> TEST THIS!! might break here
        port = int(5142) #port number
        sock.bind((host,port)) # binds address:(hostname,port#) to socket 

        # print("ready to receive message") # just for test here
        data,addr = sock.recvfrom(1024) # this method receives UDP message , 1024 means the # of bytes to be read from the udp socket.
        # print("message received") # just for test
        if data.decode() == "quit":
            return
        # print(data.decode("utf-8"), " is from ", addr) # this is for DEBUG?
        recievedMessage = data.decode("utf-8")
        lines = recievedMessage.splitlines() # create an array of lines
        messageType = lines[0]
        # print(f"Message type is: {messageType}")
        # respond back to message based on messageType
        if messageType == "listing": # verify that you are the user broadcaster is looking for
            with open("user.txt", "r") as userFile:
                username = userFile.readline().strip()
                userEmail = userFile.readline().strip() # get your own email
            if(lines[2] == userEmail): # check if I am that user they are looking for
                # print(f"recieved list request from: {lines[1]}") # DEBUG
                # check if contacts.json even exists
                if not os.path.exists("contacts.json"):
                    print("No contacts exist to be listed!")
                    return
                # load contacts from json file
                with open("contacts.json", "r") as f:
                    contacts = json.load(f)
                for contact in contacts:
                    contactEmail = contact["email"]
                    if(contactEmail == lines[1]): # you recieved a list request from someone in your contacts
                        # print("I recieved a listing request, and I am going to broadcast an accept!")  # DEBUG
                        listAcceptMessage = f"listing-accept\n{userEmail}\n"
                        broadcastMessage(listAcceptMessage, addr[0]) # send back to the original broadcaster
                
        elif messageType == "listing-accept": # original broadcaster found the person they are looking for
            # print("Listing Accepted!")
            # print(f"recieved listing confirmation from: {lines[1]}")
            # lines[1] will hold the email of the user who broadcasted a list-accept message
            with open("contacts.json", "r") as f:
                contacts = json.load(f)
            for contact in contacts:
                contactEmail = contact["email"]
                if(contactEmail == lines[1]): # this is the email you recieved a list accept from
                    contact["active"] = 1 # so now their contact is considered active, and you can send files to them
                    contact["ip"] = addr[0]
            with open("contacts.json", "w") as f:
                json.dump(contacts, f, indent=2)
        elif messageType == "file-transfer-request":
            # DEBUGGING print("I have recieved a file transfer request")
            senderEmail = lines[1]
            fileSizeGigs = lines[2]
            # add sendersEmail, their ip address, and file size in gigs to file transfer request
            incomingFileTransferRequests.put((senderEmail, addr[0], fileSizeGigs))
        else:
            print("Message Type is not regconized!\n")


#################################
# MILESTONE 4 (LISTING Contacts)
# Info is only displayed if user has added the contact, contact has accepted, and 
# contact is online and on the same network
def listContacts(printContacts):
    print()
    # check if contacts.json even exists
    if not os.path.exists("contacts.json"):
        print("No contacts exist to be listed!")
        return
    # load contacts from json file
    with open("contacts.json", "r") as f:
        contacts = json.load(f)
    # load email's user from user.txt file
    with open("user.txt", "r") as userFile:
        username = userFile.readline().strip()
        userEmail = userFile.readline().strip()
    # send out a broadcast for every contact in contacts

    # set every contact to inactive
    with open("contacts.json", "r") as f:
        contacts = json.load(f)
    for contact in contacts:
        contact["active"] = 0
    with open("contacts.json", "w") as f:
        json.dump(contacts, f, indent=2)

    for contact in contacts:
        time.sleep(0.03)
        contactEmail = contact["email"]
        messageString = f"listing\n{userEmail}\n{contactEmail}\n"
        broadcastMessage(messageString, '255.255.255.255') # broadcast to all computers on network

    # wait for a few seconds to receive responses
    if (printContacts == True):
        print("Doing magic... (Looking for contacts that are online.)")
    time.sleep(2) ## PLAY AROUND WITH THIS VALUE?

    # update contacts to check active status
    with open("contacts.json", "r") as f:
        contacts = json.load(f)
        
    # Read through contacs and print any with "online" status (value 1)
    # only run this if user needs contacts printed to terminal
    if (printContacts == True):
        print("The following contacts are online: ")
        print()
        for contact in contacts:
            if contact["active"] == 1:
                print(f"Contact: {contact['name']}, Email: {contact['email']}")
        print()
        # Part below is slightly inneficient, but for a small list of contacts this should be ok...
        if not any(contact["active"] == 1 for contact in contacts):
            print("Its lonely out here... (No contacts are online.)")
            print()

# end of listContacts()



#################################
# MILESTONE 5 (SENDING a file)
# Part 1: Requesting a file transfer
def sendFileRequest():
    # Alice wants to send a message to Bob
    recieverEmail = input("Enter email of contact: ").strip()
    fileToBeSent = input("Enter file path: ").strip()
    if not os.path.isfile(fileToBeSent):
        print("File could not be found")
        return
    fileSize = os.path.getsize(fileToBeSent)
    fileSizeGigabytes = fileSize/1e9

    # Check if Bob is in contacts and active/online
    # Could potentially check for active status again here
    # open and load contacts.json
    with open("contacts.json", "r") as f:
        contacts = json.load(f)
    
    listContacts(False) # update contacts.json without printing to terminal
    
    for contact in contacts:
        if contact["email"] == recieverEmail and contact["active"] == 1:
            # then bob is ready to be requested for a file transfer
            sender_email = ""
            with open("user.txt", "r") as f:
                f.readline()  # skip name
                sender_email = f.readline().strip()
            # send broadcast <file-transfer-request> <sender's email> <reciever's email>
            message = f"file-transfer-request\n{sender_email}\n{fileSizeGigabytes}"
            recieverIP = contact["ip"]

            # broadcast file-transfer-request to ip address of contact only
            broadcastMessage(message, contact["ip"]) 

            client_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            client_context.load_verify_locations('server.crt')

            ###############
            # DISABLES CERTIFICATE CHECKING - good for testing self signed certs
            client_context = ssl.create_default_context()
            client_context.check_hostname = False
            client_context.verify_mode = ssl.CERT_NONE
            print("Waiting for user to accept file transfer request. They must refresh their I/O")
            attempts = 0
            connected = False
            while attempts < 40 and not connected:
                try:
                    # Set timeout in seconds
                    with socket.create_connection((recieverIP, 5143), timeout=2) as sock:
                        with client_context.wrap_socket(sock, server_hostname=recieverIP) as tls_sock:
                            with open(fileToBeSent, "rb") as f:
                                while True:
                                    chunk = f.read(4096)
                                    if not chunk:
                                        break
                                    tls_sock.sendall(chunk)
                            #data = tls_sock.recv(1024)
                            

                            print(contact["name"] + " thanks you for the file. ")
                            tls_sock.shutdown(socket.SHUT_WR)
                            connected = True  # Mark success to exit loop
                except socket.timeout:
                    print("ERROR: Something bad happened.")
                except Exception as e:
                    print(f"Waiting on reciever..")
                finally:
                    attempts += 1
                    if not connected:
                        time.sleep(1)
            if connected == False:
                print ("User ignored/denied the transfer request. Ask them to refresh and accept.")
            return
    
    print("Contact does not exist or is offline. Please list again to check online status.")
# end of sendFileRequest()



#####################################
#####      MAIN DRIVER CODE    ######
#####################################
#print ("For current purposes, make sure a cerificate is available.")
#print ("If not available, generate a self-signed with the following command: ")
#print("openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout server.key -out server.crt")


file = open("user.txt", "r")
userEmail = file.readline()
file.close()

## checks if user is registered on device
if not userEmail:
    print("No users are registered with this client.")
    inp = input("Do you want to register a new user (y/n)?")
    if inp == 'y':
        print("YES was selected...")
        if registerUser() == 1:
            print("User Registered.")
            print("Exiting SecureDrop")
            exit()  # exit secure_drop
        else:
            exit()  # wrong input combo, still exit
    else:
        exit()  # exit secure_drop

## LOGIN part here
while (userLogin() == -1):
    print("Email and Password Combination Invalid.")

print("Welcome to SecureDrop.")
print("Type 'help' For Commands.")


# create thread to listen for broadcasts (another user wants to list us as their contact)
listenThread = threading.Thread(target=listenForBroadcast)
listenThread.start()

# start terminalLoop (essentially the user interface/actual program)
terminalLoop()
## 

