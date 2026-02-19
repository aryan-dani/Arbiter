import uvicorn
import os
import sys
from pyngrok import ngrok
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def start_ngrok():
    # check for token
    token = os.getenv("NGROK_AUTH_TOKEN")
    if token:
        ngrok.set_auth_token(token)
    else:
        print("⚠️  WARNING: NGROK_AUTH_TOKEN not found in .env.")
        print("   You might get a session timeout. Sign up at ngrok.com for a free token.")

    # Open a HTTP tunnel on the default port 8000
    # http_tunnel = ngrok.connect(8000)
    # The pyngrok connect method returns a NgrokTunnel object
    try:
        public_url = ngrok.connect(8000).public_url
        print("=" * 60)
        print(f"🚀 PUBLIC BACKEND URL: {public_url}")
        print("=" * 60)
        print("Copy this URL and update your Frontend .env file:")
        print(f"VITE_API_URL={public_url}")
        print("=" * 60)
    except Exception as e:
        print(f"❌ Failed to start ngrok: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_ngrok()
    # Start the Uvicorn server
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
