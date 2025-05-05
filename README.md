# WiFi Direct Chat

A lightweight peer-to-peer chat application for local networks using a combined HTTP and socket server. Ideal for computer networks courses and demonstrations of WebSocket-style real-time messaging over raw sockets.

## Features

* **HTTP Server** serving a single-page chat UI
* **Socket Server** for real-time message broadcasting over TCP
* Simple **REST API** to post and poll messages
* Automatic **reconnection** logic and **polling fallback** for unsupported environments
* **No external dependencies**—built entirely with Python's standard library

## Prerequisites

* **Python 3.7+** installed on your machine
* A network interface with IP connectivity (e.g., Ethernet, WiFi Direct)
* A modern web browser (Chrome, Firefox, Edge, Safari)

## Installation

1. **Clone** this repository:

   ```bash
   git clone https://github.com/yourusername/wifi-direct-chat.git
   cd wifi-direct-chat
   ```

2. (Optional) **Create and activate** a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate    # Windows
   ```

3. **Install** any dependencies (none required beyond standard library).

## Configuration

At the top of `chat_server.py`, you can adjust two ports if needed:

```python
HTTP_PORT = 8000     # Port for the web UI and REST API
SOCKET_PORT = 9000   # Port for the raw TCP socket server
```

If your network restricts these ports, choose alternative free ports.

## Running the Server

Start the chat server by running:

```bash
python3 chat_server.py
```

* The script will automatically detect your machine's local IP address.
* The HTTP server will start on `http://<local_ip>:<HTTP_PORT>`.
* A browser window should open automatically. If it does not, open your browser and navigate to the address printed in the console.

Socket server logs and connection status will appear in the console.

## Using the Chat Client

1. **Set your username** in the input field and click **Set Name**.
2. **Type messages** and press **Send**, or hit **Enter**.
3. Messages are broadcast in real-time to all connected peers on the same local network.

> **Note:** Ensure all participants are connected to the same network and use the displayed IP and ports.

## Project Structure

```
├── chat_server.py    # Main server script
├── README.md         # Project documentation
└── (optional files)  # e.g., LICENSE, .gitignore
```


