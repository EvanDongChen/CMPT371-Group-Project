# Include Python's Socket Library
from socket import *

# Define Server IP Address and Port
serverName = 'localhost'
serverPort = 12000
# Build Server Address Using IP Address and Port
serverAddress=(serverName, serverPort)

# Create UDP Socket for Client
clientSocket = socket(AF_INET, SOCK_DGRAM)

# This is the message received from the keyboard
message = input('Input lowercase sentence:')

# Message sent to the Server
clientSocket.sendto(message.encode(), serverAddress)

# Read reply characters from socket into string
modifiedMessage, serverAddress = clientSocket.recvfrom(2048)

# Print received string
print(modifiedMessage.decode())

# Close the client socket
clientSocket.close()
