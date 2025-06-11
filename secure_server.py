import http.server
import ssl
import os

# Server settings
PORT = 8000
CERTFILE = os.path.join(os.getcwd(), 'cert.pem')
KEYFILE = os.path.join(os.getcwd(), 'key.pem')

# Create a basic request handler
Handler = http.server.SimpleHTTPRequestHandler

# Create an HTTP server
httpd = http.server.HTTPServer(('0.0.0.0', PORT), Handler)

# Wrap the server with an SSL context
try:
    httpd.socket = ssl.wrap_socket(
        httpd.socket,
        server_side=True,
        certfile=CERTFILE,
        keyfile=KEYFILE,
        ssl_version=ssl.PROTOCOL_TLS
    )
    print(f"✅ Secure server started on https://0.0.0.0:{PORT}")
    print("   - You can access this from another device using your computer's local IP address.")
    print(f"   - Certificate: {CERTFILE}")
    print(f"   - Key: {KEYFILE}")
    print("\n   When you access this in your browser, you will likely see a privacy warning.")
    print("   This is expected. You must click 'Advanced' and 'Proceed to...' to continue.")
    
    httpd.serve_forever()

except FileNotFoundError:
    print("\n❌ ERROR: Could not find cert.pem or key.pem.")
    print("   Please run the following command to generate them first:")
    print('   openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/C=US/ST=CA/L=SF/O=Demo/CN=localhost"')
    
except Exception as e:
    print(f"\n❌ An unexpected error occurred: {e}") 