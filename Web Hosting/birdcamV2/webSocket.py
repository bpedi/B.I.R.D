import asyncio
import websockets
import json
import logging
import ssl # Import the ssl module
import os # Import os for path checking

# Configure logging for better visibility
logging.basicConfig(level=logging.INFO)

# --- Configuration ---
WS_PORT = 8001
CERTFILE = "cert.pem"  # Your SSL certificate file
KEYFILE = "key.pem"    # Your SSL private key file
# --------------------

# Set to store all currently connected WebSocket clients
connected_clients = set()

async def handler(websocket, path=None): # <--- MODIFIED: Made 'path' optional
    """
    Handles incoming WebSocket connections and messages.
    It simply relays messages to all other connected clients.
    """
    client_address = websocket.remote_address
    logging.info(f"Client connected: {client_address}")
    connected_clients.add(websocket)

    try:
        async for message in websocket:
            logging.info(f"Received from {client_address}: {message[:100]}...") # Log first 100 chars
            # Broadcast message to all other connected clients
            for client in connected_clients:
                if client != websocket: # Don't send the message back to the sender
                    try:
                        await client.send(message)
                    except websockets.exceptions.ConnectionClosed:
                        logging.warning(f"Attempted to send to a closed client: {client.remote_address}")
                        # Client will be removed from set in its own finally block
                    except Exception as e:
                        logging.error(f"Error sending message to client {client.remote_address}: {e}")
    except websockets.exceptions.ConnectionClosedOK:
        logging.info(f"Client disconnected gracefully: {client_address}")
    except websockets.exceptions.ConnectionClosedError as e:
        logging.error(f"Client disconnected with error {e.code}: {client_address} - {e.reason}")
    except Exception as e:
        logging.error(f"Unexpected error with client {client_address}: {e}")
    finally:
        # Ensure the client is removed from the set when its connection closes
        if websocket in connected_clients:
            connected_clients.remove(websocket)
            logging.info(f"Client removed from active connections: {client_address}")

async def main():
    """
    Starts the WebSocket signaling server with WSS (SSL/TLS).
    """
    # Create an SSL context
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER) # Use PROTOCOL_TLS_SERVER for modern TLS

    # Check if certificate and key files exist
    if not os.path.exists(CERTFILE):
        logging.critical(f"ERROR: Certificate file '{CERTFILE}' not found in '{os.getcwd()}'.")
        logging.critical("Please ensure it is in the same directory as this script, or provide the correct path.")
        return
    if not os.path.exists(KEYFILE):
        logging.critical(f"ERROR: Key file '{KEYFILE}' not found in '{os.getcwd()}'.")
        logging.critical("Please ensure it is in the same directory as this script, or provide the correct path.")
        return

    try:
        ssl_context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
    except ssl.SSLError as e:
        logging.critical(f"ERROR: SSL certificate/key error loading for WebSocket server: {e}")
        logging.critical("Ensure your certificate and key files are valid and correctly formatted.")
        return # Exit on SSL error

    # Start the WebSocket server with the SSL context
    # Binding to '0.0.0.0' to make the server accessible from other devices on the network
    # IMPORTANT FIX: 'await' the websockets.serve() call directly
    server = await websockets.serve(
        handler,
        "0.0.0.0",
        WS_PORT,
        ssl=ssl_context # Pass the SSL context here
    )

    logging.info(f"WebSocket Signaling Server started with WSS on wss://0.0.0.0:{WS_PORT}")
    logging.info("Waiting for clients to connect...")
    await server.wait_closed() # Call wait_closed on the actual server object

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("WebSocket Signaling Server stopped by user.")
    except Exception as e:
        logging.critical(f"Failed to start WebSocket server: {e}")
