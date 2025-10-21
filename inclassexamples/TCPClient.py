# Include Python's Socket Library
from socket import *

# Specify Server Address
serverName = 'localhost'
serverPort = 12000

# Create TCP Socket for Client
clientSocket = socket(AF_INET, SOCK_STREAM)

# Connect to TCP Server Socket
clientSocket.connect((serverName,serverPort))

# Recieve user input from keyboard
sentence = input('Input lowercase sentence:')

# Send! No need to specify Server Name and Server Port! Why?
clientSocket.send(sentence.encode())

# Read reply characters! No need to read address! Why?
modifiedSentence = clientSocket.recv(1024)

# Print out the received string
print ('From Server:', modifiedSentence.decode())

# Close the socket
clientSocket.close()
