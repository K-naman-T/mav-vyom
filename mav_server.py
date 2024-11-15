import socket
import json
import threading
import time
from datetime import datetime

class MAVServer:
    def __init__(self, host='localhost', port=5760):
        self.host = host
        self.port = port
        self.running = True
        self.setup_socket()

    def setup_socket(self):
        """Setup server socket"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind((self.host, self.port))
            print(f"Server started on {self.host}:{self.port}")
        except Exception as e:
            print(f"Socket binding failed: {e}")
            raise

    def handle_client(self, client_socket, addr):
        """Handle individual client connection"""
        print(f"New connection from {addr}")
        buffer = ""
        
        while self.running:
            try:
                # Receive data in chunks
                chunk = client_socket.recv(4096)
                if not chunk:
                    print(f"Client {addr} disconnected")
                    break

                # Decode and process the data
                data = chunk.decode('utf-8')
                buffer += data

                # Process complete JSON messages
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    try:
                        telemetry = json.loads(message)
                        self.display_telemetry(telemetry)
                    except json.JSONDecodeError:
                        print("Invalid JSON received")
                        continue

            except Exception as e:
                print(f"Error handling client {addr}: {e}")
                break

        client_socket.close()
        print(f"Connection closed for {addr}")

    def display_telemetry(self, data):
        """Display received telemetry data"""
        try:
            flight_data = data['liveFlightDashboard']['currentFlight']
            status = flight_data['flightStatus']
            
            print("\n=== SITL Telemetry ===")
            print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
            print(f"Mode: {flight_data['flightMode']}")
            print(f"Status: {status['status']}")
            print(f"Position: {status['location']['latitude']:.6f}, {status['location']['longitude']:.6f}")
            print(f"Altitude: {status['altitude']:.1f}m")
            print(f"Battery: {flight_data['battery']['level']}%")
            print("====================")
        except KeyError as e:
            print(f"Error parsing telemetry: {e}")

    def start(self):
        """Start the server"""
        self.sock.listen(5)
        print("Waiting for connections...")
        
        try:
            while self.running:
                try:
                    client, addr = self.sock.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client, addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except Exception as e:
                    print(f"Error accepting connection: {e}")
                    time.sleep(1)

        except KeyboardInterrupt:
            print("\nServer shutting down...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup server resources"""
        self.running = False
        if hasattr(self, 'sock'):
            self.sock.close()
        print("Server stopped")

if __name__ == "__main__":
    server = MAVServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Server error: {e}")
