import socket
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import time
from urllib.parse import parse_qs, urlparse

# Global variables
connected_clients = []
message_history = []
host_ip = None

def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to a public address (doesn't actually send data)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"  # Fallback to localhost

class ChatHandler(BaseHTTPRequestHandler):
    """HTTP handler for serving the web UI and handling API requests"""
    
    def _set_headers(self, content_type="text/html"):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
    
    def _set_cors_headers(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_OPTIONS(self):
        self._set_cors_headers()
    
    def do_GET(self):
        global message_history, host_ip
        
        # Serve the main page
        if self.path == "/" or self.path == "":
            self._set_headers()
            self.wfile.write(HTML_CONTENT.encode())
        
        # API endpoint to get messages
        elif self.path.startswith("/api/messages"):
            self._set_headers("application/json")
            
            # Get the last_id parameter if present
            query_params = urlparse(self.path).query
            params = parse_qs(query_params)
            last_id = int(params.get('last_id', ['-1'])[0])
            
            # Return only new messages
            new_messages = message_history[last_id+1:] if last_id >= -1 else message_history
            
            response = {
                "messages": new_messages,
                "last_id": len(message_history) - 1
            }
            
            self.wfile.write(json.dumps(response).encode())
        
        # API endpoint to get server info
        elif self.path == "/api/info":
            self._set_headers("application/json")
            server_info = {
                "host_ip": host_ip,
                "http_port": HTTP_PORT,
                "socket_port": SOCKET_PORT
            }
            self.wfile.write(json.dumps(server_info).encode())
    
    def do_POST(self):
        global message_history
        
        # API endpoint to send a message
        if self.path == "/api/send":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode())
                username = data.get("username", "Anonymous")
                message = data.get("message", "")
                
                if message:
                    timestamp = time.strftime("%H:%M:%S")
                    new_message = {
                        "username": username,
                        "message": message,
                        "timestamp": timestamp
                    }
                    message_history.append(new_message)
                    
                    # Broadcast to all connected socket clients
                    broadcast_message(json.dumps(new_message))
                    
                    self._set_headers("application/json")
                    self.wfile.write(json.dumps({"status": "success"}).encode())
                else:
                    self._set_headers("application/json")
                    self.wfile.write(json.dumps({"status": "error", "message": "Empty message"}).encode())
            
            except Exception as e:
                self._set_headers("application/json")
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())

def handle_client(client_socket, addr):
    """Handle a connected client socket"""
    global connected_clients, message_history
    print(f"New connection from {addr}")
    
    try:
        while True:
            # Receive data from client
            data = client_socket.recv(4096)
            if not data:
                break
            
            # Parse the message
            try:
                message = json.loads(data.decode())
                message_history.append(message)
                
                # Broadcast to all other clients
                for client in connected_clients:
                    if client != client_socket:
                        try:
                            client.send(data)
                        except:
                            pass
            except:
                pass
    
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    
    finally:
        # Remove the client from the list
        if client_socket in connected_clients:
            connected_clients.remove(client_socket)
        client_socket.close()
        print(f"Connection from {addr} closed")

def broadcast_message(message):
    """Broadcast a message to all connected clients"""
    global connected_clients
    for client in connected_clients[:]:  # Copy the list to avoid modification issues
        try:
            client.send(message.encode())
        except:
            # If sending fails, remove the client
            if client in connected_clients:
                connected_clients.remove(client)

def start_socket_server():
    """Start the socket server for real-time communication"""
    global host_ip, connected_clients
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host_ip, SOCKET_PORT))
    server.listen(10)
    print(f"Socket server started on {host_ip}:{SOCKET_PORT}")
    
    while True:
        client_socket, addr = server.accept()
        connected_clients.append(client_socket)
        client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
        client_thread.daemon = True
        client_thread.start()

# Define the HTML content with embedded CSS and JavaScript
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WiFi Direct Chat</title>
    <style>
        :root {
            --primary-color: #4a6fa5;
            --secondary-color: #166088;
            --accent-color: #4fc3dc;
            --bg-color: #051923;
            --text-color: #e6f3f7;
            --message-bg: #203647;
            --own-message-bg: #2e5077;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        html, body {
            height: 100%;
            width: 100%;
            overflow: hidden;
            background-color: var(--bg-color);
            color: var(--text-color);
        }
        
        .container {
            display: flex;
            flex-direction: column;
            height: 100vh;
            width: 100vw;
            padding: 0;
            margin: 0;
            overflow: hidden;
        }
        
        .header {
            background-color: var(--secondary-color);
            padding: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
        }
        
        .title {
            color: white;
            font-size: 1.5rem;
            font-weight: bold;
        }
        
        .server-info {
            font-size: 0.9rem;
            opacity: 0.9;
        }
        
        .username-form {
            display: flex;
            gap: 10px;
            align-items: center;
            padding: 0.8rem;
            background-color: rgba(32, 54, 71, 0.4);
        }
        
        input {
            padding: 10px 15px;
            border-radius: 20px;
            border: none;
            background-color: #2a475e;
            color: var(--text-color);
            flex-grow: 1;
            outline: none;
            transition: all 0.3s ease;
        }
        
        input:focus {
            background-color: #344e6c;
            box-shadow: 0 0 0 2px var(--accent-color);
        }
        
        button {
            padding: 10px 20px;
            border-radius: 20px;
            border: none;
            background-color: var(--primary-color);
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: bold;
        }
        
        button:hover {
            background-color: var(--accent-color);
            transform: translateY(-2px);
        }
        
        .chat-container {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
        }
        
        .messages {
            flex-grow: 1;
            padding: 1rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
            background-color: rgba(5, 25, 35, 0.7);
        }
        
        .message {
            max-width: 80%;
            padding: 10px 15px;
            border-radius: 18px;
            line-height: 1.4;
            position: relative;
            animation: fadeIn 0.3s ease;
            word-wrap: break-word;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.received {
            background-color: var(--message-bg);
            align-self: flex-start;
            border-bottom-left-radius: 5px;
        }
        
        .message.sent {
            background-color: var(--own-message-bg);
            align-self: flex-end;
            border-bottom-right-radius: 5px;
        }
        
        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 0.85rem;
            opacity: 0.8;
        }
        
        .message-sender {
            font-weight: bold;
            color: var(--accent-color);
        }
        
        .message-time {
            font-size: 0.75rem;
        }
        
        .input-area {
            display: flex;
            gap: 10px;
            padding: 1rem;
            background-color: rgba(32, 54, 71, 0.8);
            border-top: 1px solid #2a475e;
        }
        
        .message-input {
            flex-grow: 1;
        }
        
        /* Connection status indicator */
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            background-color: #ff4d4d; /* Red for disconnected */
            transition: background-color 0.3s ease;
        }
        
        .status-indicator.connected {
            background-color: #4dff4d; /* Green for connected */
        }
        
        /* Loading animation */
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 2rem;
        }
        
        .loading-dots {
            display: flex;
            gap: 5px;
        }
        
        .loading-dots span {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: var(--accent-color);
            animation: loadingDots 1.4s infinite ease-in-out both;
        }
        
        .loading-dots span:nth-child(1) {
            animation-delay: -0.32s;
        }
        
        .loading-dots span:nth-child(2) {
            animation-delay: -0.16s;
        }
        
        @keyframes loadingDots {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        
        /* System message */
        .message.system {
            background-color: rgba(74, 111, 165, 0.3);
            align-self: center;
            padding: 8px 12px;
            border-radius: 10px;
            font-size: 0.9rem;
            opacity: 0.8;
            max-width: 90%;
            text-align: center;
        }
        
        /* Responsiveness */
        @media (max-width: 600px) {
            .message {
                max-width: 90%;
            }
            
            .header {
                padding: 0.8rem;
            }
            
            .title {
                font-size: 1.3rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 class="title">
                    <span class="status-indicator" id="connectionStatus"></span>
                    WiFi Direct Chat
                </h1>
                <div class="server-info" id="serverInfo">Connecting...</div>
            </div>
        </div>
        
        <div class="username-form">
            <input type="text" id="usernameInput" placeholder="Your username" maxlength="20">
            <button id="setUsername">Set Name</button>
        </div>
        
        <div class="chat-container">
            <div class="messages" id="messagesContainer">
                <div class="loading">
                    <div class="loading-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
            
            <div class="input-area">
                <input type="text" id="messageInput" class="message-input" placeholder="Type your message..." disabled>
                <button id="sendButton" disabled>Send</button>
            </div>
        </div>
    </div>

    <script>
        // Global variables
        let username = 'Anonymous';
        let socket = null;
        let isSocketConnected = false;
        let lastMessageId = -1;
        let isInitialLoad = true;
        let pollingTimeoutId = null;
        
        // DOM Elements
        const messagesContainer = document.getElementById('messagesContainer');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const usernameInput = document.getElementById('usernameInput');
        const setUsernameButton = document.getElementById('setUsername');
        const serverInfoEl = document.getElementById('serverInfo');
        const connectionStatusEl = document.getElementById('connectionStatus');
        
        // Set username
        setUsernameButton.addEventListener('click', () => {
            const newUsername = usernameInput.value.trim();
            if (newUsername) {
                username = newUsername;
                messageInput.disabled = false;
                sendButton.disabled = false;
                usernameInput.disabled = true;
                setUsernameButton.disabled = true;
                
                // Add a system message
                addSystemMessage(`You joined as "${username}"`);
                messageInput.focus();
            }
        });
        
        // Handle send message
        function sendMessage() {
            const message = messageInput.value.trim();
            if (message && username) {
                // Send via HTTP API
                fetch('/api/send', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        username: username,
                        message: message
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        messageInput.value = '';
                        messageInput.focus();
                    }
                })
                .catch(error => {
                    console.error('Error sending message:', error);
                    addSystemMessage('Failed to send message. Please try again.');
                });
            }
        }
        
        // Send message on button click
        sendButton.addEventListener('click', sendMessage);
        
        // Send message on Enter key
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        // Add a message to the chat
        function addMessage(message) {
            const isOwnMessage = message.username === username;
            
            const messageEl = document.createElement('div');
            messageEl.className = `message ${isOwnMessage ? 'sent' : 'received'}`;
            
            const headerEl = document.createElement('div');
            headerEl.className = 'message-header';
            
            const senderEl = document.createElement('span');
            senderEl.className = 'message-sender';
            senderEl.textContent = message.username;
            
            const timeEl = document.createElement('span');
            timeEl.className = 'message-time';
            timeEl.textContent = message.timestamp;
            
            headerEl.appendChild(senderEl);
            headerEl.appendChild(timeEl);
            
            const contentEl = document.createElement('div');
            contentEl.className = 'message-content';
            contentEl.textContent = message.message;
            
            messageEl.appendChild(headerEl);
            messageEl.appendChild(contentEl);
            
            messagesContainer.appendChild(messageEl);
            scrollToBottom();
        }
        
        // Add a system message
        function addSystemMessage(text) {
            const messageEl = document.createElement('div');
            messageEl.className = 'message system';
            messageEl.textContent = text;
            
            messagesContainer.appendChild(messageEl);
            scrollToBottom();
        }
        
        // Scroll to the bottom of the messages container
        function scrollToBottom() {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        // Connect to WebSocket server
        function connectWebSocket(host, port) {
            if (socket) {
                socket.close();
            }
            
            try {
                socket = new WebSocket(`ws://${host}:${port}`);
                
                socket.onopen = () => {
                    console.log('WebSocket connected');
                    isSocketConnected = true;
                    updateConnectionStatus(true);
                    addSystemMessage('Connected to chat server');
                };
                
                socket.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        addMessage(message);
                    } catch (e) {
                        console.error('Error parsing message:', e);
                    }
                };
                
                socket.onclose = () => {
                    console.log('WebSocket disconnected');
                    isSocketConnected = false;
                    updateConnectionStatus(false);
                    
                    // Try to reconnect after a delay
                    setTimeout(() => {
                        if (!isSocketConnected) {
                            connectWebSocket(host, port);
                        }
                    }, 5000);
                };
                
                socket.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    isSocketConnected = false;
                    updateConnectionStatus(false);
                };
                
            } catch (error) {
                console.error('Failed to create WebSocket:', error);
                updateConnectionStatus(false);
            }
        }
        
        // Update connection status indicator
        function updateConnectionStatus(connected) {
            if (connected) {
                connectionStatusEl.classList.add('connected');
            } else {
                connectionStatusEl.classList.remove('connected');
            }
        }
        
        // Fetch initial server info
        function fetchServerInfo() {
            fetch('/api/info')
                .then(response => response.json())
                .then(data => {
                    const { host_ip, http_port, socket_port } = data;
                    serverInfoEl.textContent = `Server: ${host_ip}:${http_port}`;
                    
                    // Connect to WebSocket
                    connectWebSocket(host_ip, socket_port);
                })
                .catch(error => {
                    console.error('Error fetching server info:', error);
                    serverInfoEl.textContent = 'Failed to connect to server';
                });
        }
        
        // Fetch messages with intelligent polling
        function fetchMessages() {
            // Clear any existing timeout
            if (pollingTimeoutId) {
                clearTimeout(pollingTimeoutId);
            }
            
            // Only show loading on initial load
            if (isInitialLoad) {
                messagesContainer.innerHTML = `
                    <div class="loading">
                        <div class="loading-dots">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                `;
            }
            
            fetch(`/api/messages?last_id=${lastMessageId}`)
                .then(response => response.json())
                .then(data => {
                    // Clear the loading indicator on first load
                    if (isInitialLoad) {
                        messagesContainer.innerHTML = '';
                        isInitialLoad = false;
                    }
                    
                    // Add new messages
                    if (data.messages && data.messages.length) {
                        data.messages.forEach(message => {
                            addMessage(message);
                        });
                        
                        // Update last message ID
                        lastMessageId = data.last_id;
                    } else if (lastMessageId === -1) {
                        // If no messages and first load
                        addSystemMessage('No messages yet. Be the first to say hello!');
                    }
                    
                    // Schedule next polling with intelligent timing
                    // Poll more frequently when there's activity
                    const pollingDelay = data.messages && data.messages.length > 0 ? 1000 : 3000;
                    pollingTimeoutId = setTimeout(fetchMessages, pollingDelay);
                })
                .catch(error => {
                    console.error('Error fetching messages:', error);
                    
                    if (isInitialLoad) {
                        messagesContainer.innerHTML = '';
                        addSystemMessage('Failed to load messages');
                        isInitialLoad = false;
                    }
                    
                    // Try again after a delay
                    pollingTimeoutId = setTimeout(fetchMessages, 5000);
                });
        }
        
        // Adjust height on window resize
        function adjustHeight() {
            const vh = window.innerHeight * 0.01;
            document.documentElement.style.setProperty('--vh', `${vh}px`);
        }
        
        // Initialize
        window.addEventListener('load', () => {
            adjustHeight();
            fetchServerInfo();
            fetchMessages();
            
            // Focus username input on load
            usernameInput.focus();
        });
        
        // Handle window resize
        window.addEventListener('resize', adjustHeight);
    </script>
</body>
</html>
"""

# Configuration
HTTP_PORT = 8000  # HTTP server port
SOCKET_PORT = 9000  # Socket server port

def main():
    global host_ip
    
    # Get the local IP address
    host_ip = get_local_ip()
    print(f"Starting WiFi Direct Chat Server on {host_ip}")
    
    # Start the socket server in a separate thread
    socket_thread = threading.Thread(target=start_socket_server)
    socket_thread.daemon = True
    socket_thread.start()
    
    # Start the HTTP server
    http_server = HTTPServer((host_ip, HTTP_PORT), ChatHandler)
    print(f"HTTP server started on http://{host_ip}:{HTTP_PORT}")
    
    # Open the browser
    webbrowser.open(f"http://{host_ip}:{HTTP_PORT}")
    
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("Server shutting down...")
        http_server.server_close()

if __name__ == "__main__":
    main()