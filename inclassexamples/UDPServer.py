# Include Python's Socket Library
from socket import *

# Define Server Port
serverPort = 12000

# Create UDP Socket
serverSocket = socket(AF_INET, SOCK_DGRAM)

# Bind the socket to local port 12000
serverSocket.bind(('', serverPort))

print ("The server is ready to receive")
while True: # Forever Loop
    # Read from UDP Socket into message & client address
    message, clientAddress = serverSocket.recvfrom(2048)
    
    # Uppder Case (as the simple function intended)
    modifiedMessage = message.decode().upper()
    
    # Send the upper case string back to the same client
    serverSocket.sendto(modifiedMessage.encode(), clientAddress)

