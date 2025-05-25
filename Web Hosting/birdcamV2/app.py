import http.server
import ssl
import socketserver
import os
import cgi # For parsing multipart/form-data
import datetime # For timestamping filenames
import logging # For server-side logging

# Configure logging for the server
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
DIRECTORY = "."  # "." means the current directory where the script is run
PORT = 8000
CERTFILE = "cert.pem"  # Your SSL certificate file (e.g., 'cert.pem')
KEYFILE = "key.pem"    # Your SSL private key file (e.g., 'key.pem')
CLIPS_DIR = "clips"    # Directory to save recorded clips
# --------------------

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    A custom handler to serve files and handle video uploads.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        """
        Handles POST requests, specifically for video clip uploads.
        """
        if self.path == '/upload_clip':
            self.handle_upload_clip()
        else:
            self.send_error(404, "Not Found")

    def handle_upload_clip(self):
        """
        Processes the uploaded video clip and saves it to the CLIPS_DIR.
        """
        logging.info("Received POST request for /upload_clip")
        content_type = self.headers.get('Content-Type')

        if not content_type:
            self.send_error(400, "Content-Type header is missing")
            return

        # Use cgi.FieldStorage to parse multipart/form-data
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': content_type},
            keep_blank_values=True
        )

        try:
            if 'video_clip' in form:
                file_item = form['video_clip']
                if file_item.file:
                    # Ensure the clips directory exists
                    os.makedirs(CLIPS_DIR, exist_ok=True)

                    # Generate a timestamped filename
                    now = datetime.datetime.now()
                    timestamp = now.strftime("%Y%m%d_%H%M%S")
                    # Get file extension from the original filename or infer from Content-Type
                    # For MediaRecorder, it's often video/webm or video/mp4
                    file_extension = ".webm" # Default to webm, adjust if your MediaRecorder uses mp4
                    if file_item.type == 'video/mp4':
                        file_extension = ".mp4"
                    elif file_item.type == 'video/webm':
                        file_extension = ".webm"
                    
                    filename = f"clip_{timestamp}{file_extension}"
                    file_path = os.path.join(CLIPS_DIR, filename)

                    # Save the file
                    with open(file_path, 'wb') as f:
                        f.write(file_item.file.read())
                    
                    logging.info(f"Successfully saved clip: {file_path}")
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response_data = json.dumps({"status": "success", "message": f"Clip saved as {filename}"})
                    self.wfile.write(response_data.encode('utf-8'))
                else:
                    self.send_error(400, "No file uploaded or file is empty")
            else:
                self.send_error(400, "Missing 'video_clip' field in form data")
        except Exception as e:
            logging.error(f"Error processing upload: {e}", exc_info=True)
            self.send_error(500, f"Internal Server Error: {e}")

def run_https_server():
    # Create an SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # Check if certificate and key files exist
    if not os.path.exists(CERTFILE):
        logging.critical(f"Certificate file '{CERTFILE}' not found in '{os.getcwd()}'.")
        logging.critical("Please ensure it is in the same directory as this script, or provide the correct path.")
        return
    if not os.path.exists(KEYFILE):
        logging.critical(f"Key file '{KEYFILE}' not found in '{os.getcwd()}'.")
        logging.critical("Please ensure it is in the same directory as this script, or provide the correct path.")
        return

    try:
        context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
    except ssl.SSLError as e:
        logging.critical(f"SSL certificate/key error: {e}")
        logging.critical("Ensure your certificate and key files are valid and correctly formatted.")
        return

    # Create an HTTP server instance using socketserver.TCPServer
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd: # Use CustomHTTPRequestHandler
        logging.info(f"Serving HTTPS files on port {PORT} from directory '{DIRECTORY}'...")
        logging.info(f"Video clips will be saved to: {os.path.abspath(CLIPS_DIR)}")

        try:
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

            logging.info(f"Access your host page at: https://localhost:{PORT}/host.html")
            logging.info(f"Access your viewer page at: https://localhost:{PORT}/viewer.html")
            logging.info("\nTo access from your phone or another device:")
            logging.info("1. Find your computer's local IP address (e.g., 192.168.1.100).")
            logging.info("2. Ensure your phone is on the SAME Wi-Fi network.")
            logging.info(f"3. Navigate to: https://YOUR_COMPUTERS_IP_ADDRESS:{PORT}/host.html")
            logging.info(f"4. Navigate to: https://YOUR_COMPUTERS_IP_ADDRESS:{PORT}/viewer.html")
            logging.info("\nRemember to bypass the self-signed certificate warning on your phone's browser.")
            logging.info("Also, ensure your computer's firewall allows incoming connections on port 8000.")

            httpd.serve_forever()

        except ssl.SSLError as e:
            logging.critical(f"SSL configuration error during serve: {e}")
        except Exception as e:
            logging.critical(f"An unexpected error occurred: {e}", exc_info=True)
        finally:
            logging.info("HTTPS File Server stopped.")

if __name__ == "__main__":
    run_https_server()
