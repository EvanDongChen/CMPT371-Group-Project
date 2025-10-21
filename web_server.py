# Simple web server for CMPT 371 Mini-Project
# Handles basic HTTP GET requests and returns appropriate status codes
# Evan Chen, 301591219
# Keira Liu, [INSERT STUDENT NUMBER]
from socket import *  # Import socket library for networking
import threading  # For handling multiple clients in parallel
import os  # For file and path operations

# Port number for the web server
serverPort = 8080

WEB_ROOT = os.path.dirname(os.path.abspath(__file__))  # Root directory for web files
# List of forbidden filepaths 
FORBIDDEN_PATHS = [
    'secret.txt',
    'private.html',
    'config.json',
]
SUPPORTED_HTTP_VERSION = 'HTTP/1.1'  # Only support HTTP/1.1

# Dictionary of HTTP status codes and their messages
STATUS_CODES = {
    200: 'OK',
    304: 'Not Modified',
    403: 'Forbidden',
    404: 'Not Found',
    505: 'HTTP Version Not Supported',
}

"""
Builds an HTTP response string based on status code and body.
"""
def build_response(status_code, body='', content_type='text/html'):
    reason = STATUS_CODES.get(status_code, 'Unknown')
    response = f"{SUPPORTED_HTTP_VERSION} {status_code} {reason}\r\n"
    if status_code == 200:
        response += f"Content-Type: {content_type}\r\n"
        response += f"Content-Length: {len(body)}\r\n"
    response += "Connection: close\r\n\r\n"
    if status_code == 200:
        response += body
    return response

"""
Handles a single client connection: parses request, checks file, returns response.
"""
def handle_client(connectionSocket, addr):
    try:
        # Receive HTTP request from client
        request = connectionSocket.recv(1024).decode()
        if not request:
            connectionSocket.close()
            return  # No request received
        # Split request into lines
        lines = request.split('\r\n')
        request_line = lines[0]  # First line: method, path, version
        parts = request_line.split()
        if len(parts) != 3:
            # Malformed request line
            connectionSocket.send(build_response(400, 'Bad Request').encode())
            connectionSocket.close()
            return
        method, path, version = parts
        # Only allow GET requests
        if method != 'GET':
            connectionSocket.send(build_response(403, 'Forbidden').encode())
            connectionSocket.close()
            return
        # Only allow HTTP/1.1
        if version != SUPPORTED_HTTP_VERSION:
            connectionSocket.send(build_response(505, 'HTTP Version Not Supported').encode())
            connectionSocket.close()
            return
        # Get requested file path
        file_path = path.lstrip('/')
        if not file_path:
            file_path = 'test.html'  # Default file if none specified
        # Prevent directory traversal
        normalized_path = os.path.normpath(os.path.join(WEB_ROOT, file_path))
        if not normalized_path.startswith(WEB_ROOT):
            connectionSocket.send(build_response(403, 'Forbidden').encode())
            connectionSocket.close()
            return
        # Check if file is forbidden
        rel_path = os.path.relpath(normalized_path, WEB_ROOT)
        if rel_path in FORBIDDEN_PATHS:
            connectionSocket.send(build_response(403, 'Forbidden').encode())
            connectionSocket.close()
            return
        abs_path = normalized_path
        # Check if file exists
        if not os.path.isfile(abs_path):
            connectionSocket.send(build_response(404, 'Not Found').encode())
            connectionSocket.close()
            return
        # Parse headers
        headers = {line.split(': ', 1)[0]: line.split(': ', 1)[1] for line in lines[1:] if ': ' in line}
        # Handle If-Modified-Since header
        if 'If-Modified-Since' in headers:
            connectionSocket.send(build_response(304).encode())
            connectionSocket.close()
            return
        # Read and send file contents
        with open(abs_path, 'r', encoding='utf-8') as f:
            body = f.read()
        connectionSocket.send(build_response(200, body).encode())
    except Exception as e:
        # Internal server error
        connectionSocket.send(build_response(500, f'Internal Server Error: {e}').encode())
    finally:
        connectionSocket.close()
        
# Start the server and listen for incoming connections.
def start_server():
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    serverSocket.bind(('', serverPort))
    serverSocket.listen(5)
    print('The web server is ready to receive on port', serverPort)
    while True:
        # Accept new client and handle in a thread
        connectionSocket, addr = serverSocket.accept()
        threading.Thread(target=handle_client, args=(connectionSocket, addr), daemon=True).start()

if __name__ == '__main__':
    # Start the server when running this file
    start_server()
