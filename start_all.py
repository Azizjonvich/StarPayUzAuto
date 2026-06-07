#!/usr/bin/env python
import subprocess
import sys
import os

def main():
    """Start both bot and webhook server"""
    print("Starting StarPayUz bot...")
    
    # Start bot in background
    bot_process = subprocess.Popen([sys.executable, 'bot.py'])
    print(f"Bot started with PID: {bot_process.pid}")
    
    # Start webhook server in foreground
    print("Starting webhook server...")
    server_process = subprocess.Popen([sys.executable, 'webhook_server.py'])
    print(f"Webhook server started with PID: {server_process.pid}")
    
    try:
        # Wait for both processes
        bot_process.wait()
        server_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        bot_process.terminate()
        server_process.terminate()
        bot_process.wait()
        server_process.wait()

if __name__ == '__main__':
    main()
