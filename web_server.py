# Simple web server and proxy server for CMPT 371 Mini-Project
# Web server: Handles basic HTTP GET requests and returns appropriate status codes
# Proxy server: Handles basic HTTP Get requests from clients with cache and uses conditional GET
# Evan Chen, 301591219
# Keira Liu, 301580572
from socket import *  # Import socket library for networking
import threading  # For handling multiple clients in parallel
import os  # For file and path operations
import time # For adding last modified time
import calendar # For adding last modified time

# Port numbers
serverPort = 8080
proxyServerPort = 8888

# Directories
WEB_ROOT = os.path.dirname(os.path.abspath(__file__))  # Root directory for web files
CACHE_DIR = './cache'
os.makedirs(CACHE_DIR, exist_ok=True)

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
    400: 'Bad Request',
    403: 'Forbidden',
    404: 'Not Found',
    500: 'Internal Server Error',
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
            client_time = calendar.timegm(time.strptime(headers['If-Modified-Since'], "%a, %d %b %Y %H:%M:%S GMT"))
            file_time = os.path.getmtime(abs_path)

            if file_time <= client_time:
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

def handle_proxy_client(connectionSocket, addr):
    try:
        # Receive HTTP request from client
        request = connectionSocket.recv(1024).decode()
        if not request:
            connectionSocket.close()
            return  # No request received

        # Split request into lines
        lines = request.split('\r\n')
        request_line = lines[0]
        parts = request_line.split()

        if len(parts) != 3:
            # Deformed request line
            connectionSocket.send(build_response(400, 'Bad Request').encode())
            connectionSocket.close()
            return

        # Extract parts in the request line
        method, url, version = parts

        if url.startswith('http://') or url.startswith('https://'):
            # Remove scheme and host in path
            url_parts = url.split('/', 3)
            if len(url_parts) >= 4:
                path = '/' + url_parts[3]
            else:
                path = '/'
        

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
        
        # Normalize path and prepare cache file
        file_name = path.lstrip('/').replace('/', '_')
        if not file_name:
            file_name = 'test.html' # default file if none
        cache_path = os.path.join(CACHE_DIR, file_name)

        # Extract host name
        host_name = None
        for line in lines[1:]:  # skip request line
            if ':' in line:
                header_name, header_value = line.split(':', 1)
                if header_name.strip().lower() == 'host':
                    host_name = header_value.strip()
                    break

        if host_name is None:
            connectionSocket.send(build_response(400, 'Bad Request: missing Host header').encode())
            connectionSocket.close()
            return

        # If the host header has a port, split it
        if ':' in host_name:
            host, port_str = host_name.rsplit(':', 1)
            port = int(port_str)
        else:
            host = host_name
            port = serverPort

        # Check if file exists in cache
        headers = {} # Store headers to add to request to host server
        if os.path.exists(cache_path):
            # Add If-Modified-Since header
            mtime = os.path.getmtime(cache_path)
            last_modified = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(mtime))
            headers['If-Modified-Since'] = last_modified

        # Build request for host server
        forward_req = f"GET {path} {SUPPORTED_HTTP_VERSION}\r\nHost: {host_name}\r\nConnection: close\r\n"
        if 'If-Modified-Since' in headers:
            forward_req += f"If-Modified-Since: {headers['If-Modified-Since']}\r\n"
        forward_req += "\r\n"

        # Connect to host
        host_socket = socket(AF_INET, SOCK_STREAM)
        host_socket.connect((host.strip(), port))
        host_socket.send(forward_req.encode())

        # Receive host response
        response_data = b''
        while True:
            chunk = host_socket.recv(1024)
            if not chunk:
                break
            response_data += chunk
        host_socket.close()

        response_text = response_data.decode(errors='ignore')
        status_line = response_text.split('\r\n')[0]
        status_code = int(status_line.split()[1])

        # Respond to client
        if status_code == 304:
            # Cache file is up to date, so send from cache
            with open(cache_path, 'r', encoding='utf-8') as f:
                body = f.read()
            connectionSocket.send(build_response(200, body).encode())
        elif status_code == 200:
            # File has been updated, so send response from host and save in cache
            header_end = response_text.find('\r\n\r\n')
            body = response_text[header_end+4:]
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(body)
            connectionSocket.send(build_response(200, body).encode())
        else:
            # Error message, so just forward the message
            connectionSocket.send(response_data)

    except Exception as e:
        # Internal server error
        connectionSocket.send(build_response(500, f'Internal Server Error: {e}').encode())
    finally:
        connectionSocket.close()
        
# Start the servers and listen for incoming connections
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

def start_proxy_server():
    proxyServerSocket = socket(AF_INET, SOCK_STREAM)
    proxyServerSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    proxyServerSocket.bind(('', proxyServerPort))
    proxyServerSocket.listen(5)
    print('The proxy server is ready to receive on port', proxyServerPort)
    while True:
        # Accept new client and handle in a thread
        connectionSocket, addr = proxyServerSocket.accept()
        threading.Thread(target=handle_proxy_client, args=(connectionSocket, addr), daemon=True).start()

if __name__ == '__main__':
    # Start the servers in seperate threads when running this file
    threading.Thread(target=start_server, daemon=True).start()
    threading.Thread(target=start_proxy_server, daemon=True).start()

    # Keep main thread alive, unless keyboard interrupt
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nKeyboard Interrupt Detected: Servers shutting down")
