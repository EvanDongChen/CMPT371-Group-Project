# Include Python's Socket Library
from socket import *

# Specify Server Port
serverPort = 12000

# Create TCP welcoming socket
serverSocket = socket(AF_INET,SOCK_STREAM)

# Bind the server port to the socket
serverSocket.bind(('',serverPort))

# Server begins listening for incoming TCP connections
serverSocket.listen(1)
print ('The server is ready to receive')

while True: # Loop forever
     # Server waits on accept for incoming requests.
     # New socket created on return
     connectionSocket, addr = serverSocket.accept()
     
     # Read from socket (but not address as in UDP)
     sentence = connectionSocket.recv(1024).decode()
     
     # Send the reply
     capitalizedSentence = sentence.upper()
     connectionSocket.send(capitalizedSentence.encode())
     
     # Close connection to client (but not welcoming socket)
     connectionSocket.close()
