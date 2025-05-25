import http.server
import ssl
import socketserver
import os

# --- Configuration ---
# Set the directory to serve files from (where your HTML, CSS, JS, and certs are)
DIRECTORY = "."  # "." means the current directory where the script is run
PORT = 8000
CERTFILE = "cert.pem"  # Your SSL certificate file (e.g., 'cert.pem')
KEYFILE = "key.pem"    # Your SSL private key file (e.g., 'key.pem')
# --------------------

class MyHandler(http.server.SimpleHTTPRequestHandler):
    """
    A custom handler to serve from a specific directory.
    This ensures files are served relative to the script's location.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def run_https_server():
    # Create an SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER) # Use PROTOCOL_TLS_SERVER for modern TLS

    # Check if certificate and key files exist
    if not os.path.exists(CERTFILE):
        print(f"ERROR: Certificate file '{CERTFILE}' not found in '{os.getcwd()}'.")
        print("Please ensure it is in the same directory as this script, or provide the correct path.")
        return
    if not os.path.exists(KEYFILE):
        print(f"ERROR: Key file '{KEYFILE}' not found in '{os.getcwd()}'.")
        print("Please ensure it is in the same directory as this script, or provide the correct path.")
        return

    try:
        context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
    except ssl.SSLError as e:
        print(f"ERROR: SSL certificate/key error: {e}")
        print("Ensure your certificate and key files are valid and correctly formatted.")
        return # Exit on SSL error

    # Create an HTTP server instance using socketserver.TCPServer
    # Binding to '0.0.0.0' makes it accessible from other devices on the network
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Serving HTTPS files on port {PORT} from directory '{DIRECTORY}'...")

        try:
            # Apply the SSL context to the server's socket
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

            print(f"Access your host page at: https://localhost:{PORT}/host.html")
            print(f"Access your viewer page at: https://localhost:{PORT}/viewer.html")
            print("\nTo access from your phone or another device:")
            print("1. Find your computer's local IP address (e.g., 192.168.1.100).")
            print("2. Ensure your phone is on the SAME Wi-Fi network.")
            print(f"3. Navigate to: https://YOUR_COMPUTERS_IP_ADDRESS:{PORT}/host.html")
            print(f"4. Navigate to: https://YOUR_COMPUTERS_IP_ADDRESS:{PORT}/viewer.html")
            print("\nRemember to bypass the self-signed certificate warning on your phone's browser.")
            print("Also, ensure your computer's firewall allows incoming connections on port 8000.")

            httpd.serve_forever()

        except ssl.SSLError as e:
            print(f"ERROR: SSL configuration error during serve: {e}")
            print("This can sometimes indicate issues with the client's SSL negotiation or invalid cert/key.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            print("HTTPS File Server stopped.")

if __name__ == "__main__":
    run_https_server()
