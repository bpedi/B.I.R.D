import asyncio
from aiohttp import web
import ssl
import os
import datetime
import logging
import json

# Configure logging for the server
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
DIRECTORY = "."  # "." means the current directory where the script is run
PORT = 8000
CERTFILE = "cert.pem"  # Your SSL certificate file (e.g., 'cert.pem')
KEYFILE = "key.pem"    # Your SSL private key file (e.g., 'key.pem')
CLIPS_DIR = "clips"    # Directory to save recorded clips
# --------------------

async def handle_static(request):
    """
    Handles serving static files (HTML, JS, CSS).
    """
    filepath = os.path.join(DIRECTORY, request.path.lstrip('/'))
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        # Fallback to index.html for root or if file not found directly
        if request.path == '/' or not os.path.exists(filepath):
            filepath = os.path.join(DIRECTORY, 'host.html') # Or index.html if you have one
            if not os.path.exists(filepath):
                raise web.HTTPNotFound()
        else:
            raise web.HTTPNotFound()

    return web.FileResponse(filepath)

async def upload_clip(request):
    """
    Handles POST requests for video clip uploads.
    """
    logging.info("Received POST request for /upload_clip")
    
    # Check if the request content type is multipart/form-data
    if not request.content_type.startswith('multipart/form-data'):
        logging.warning(f"Unsupported Content-Type for upload: {request.content_type}")
        raise web.HTTPUnsupportedMediaType(reason="Content-Type must be multipart/form-data")

    reader = await request.multipart() # Get the multipart reader

    # 'video_clip' is the field name used in host.html's FormData
    field = await reader.next()
    if field is None or field.name != 'video_clip':
        logging.warning("Missing 'video_clip' field in multipart form data.")
        raise web.HTTPBadRequest(reason="Missing 'video_clip' field")

    if not field.filename:
        logging.warning("No filename provided for uploaded clip.")
        raise web.HTTPBadRequest(reason="No filename provided for clip")

    # Ensure the clips directory exists
    os.makedirs(CLIPS_DIR, exist_ok=True)

    # Generate a timestamped filename
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    
    # Infer file extension from Content-Type or original filename
    file_extension = ".webm" # Default
    if field.headers.get('Content-Type') == 'video/mp4':
        file_extension = ".mp4"
    elif field.headers.get('Content-Type') == 'video/webm':
        file_extension = ".webm"
    elif '.' in field.filename: # Try to get from original filename if available
        ext = os.path.splitext(field.filename)[1]
        if ext:
            file_extension = ext

    filename = f"clip_{timestamp}{file_extension}"
    file_path = os.path.join(CLIPS_DIR, filename)

    size = 0
    with open(file_path, 'wb') as f:
        while True:
            chunk = await field.read_chunk() # Read chunks of the file
            if not chunk:
                break
            f.write(chunk)
            size += len(chunk)

    logging.info(f"Successfully saved clip: {file_path} ({size} bytes)")
    
    response_data = {"status": "success", "message": f"Clip saved as {filename}"}
    return web.json_response(response_data)

async def main():
    """
    Sets up and runs the aiohttp HTTPS server.
    """
    app = web.Application()

    # Define routes
    app.router.add_get('/', handle_static) # Serve host.html by default
    app.router.add_get('/{name}', handle_static) # Serve other static files (e.g., host.html, viewer.html)
    app.router.add_post('/upload_clip', upload_clip) # Handle video uploads

    # Create SSL context
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

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
        ssl_context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
    except ssl.SSLError as e:
        logging.critical(f"SSL certificate/key error: {e}")
        logging.critical("Ensure your certificate and key files are valid and correctly formatted.")
        return

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT, ssl_context=ssl_context)

    logging.info(f"Serving HTTPS files with aiohttp on port {PORT} from directory '{DIRECTORY}'...")
    logging.info(f"Video clips will be saved to: {os.path.abspath(CLIPS_DIR)}")
    logging.info(f"Access your host page at: https://localhost:{PORT}/host.html")
    logging.info(f"Access your viewer page at: https://localhost:{PORT}/viewer.html")
    logging.info("\nTo access from your phone or another device:")
    logging.info("1. Find your computer's local IP address (e.g., 192.168.1.100).")
    logging.info("2. Ensure your phone is on the SAME Wi-Fi network.")
    logging.info(f"3. Navigate to: https://YOUR_COMPUTERS_IP_ADDRESS:{PORT}/host.html")
    logging.info(f"4. Navigate to: https://YOUR_COMPUTERS_IP_ADDRESS:{PORT}/viewer.html")
    logging.info("\nRemember to bypass the self-signed certificate warning on your phone's browser.")
    logging.info("Also, ensure your computer's firewall allows incoming connections on port 8000.")

    try:
        await site.start()
        # Keep the server running indefinitely
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logging.info("Server shutdown initiated.")
    except Exception as e:
        logging.critical(f"An unexpected error occurred during server startup: {e}", exc_info=True)
    finally:
        await runner.cleanup()
        logging.info("aiohttp HTTPS File Server stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("aiohttp HTTPS File Server stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logging.critical(f"Failed to start aiohttp HTTPS server: {e}", exc_info=True)
