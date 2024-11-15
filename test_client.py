import socket
import json
import time
from datetime import datetime
import subprocess
import signal
import os
import sys

class SITLClient:
    def __init__(self, host='localhost', port=5760):
        self.host = host
        self.port = port
        self.sitl_process = None
        self.mavproxy_process = None
        self.server_socket = None
        self.start_time = datetime.now()
        self.running = True

    def start_sitl(self):
        """Start ArduPilot SITL"""
        try:
            # Start SITL
            sitl_cmd = [
                'sim_vehicle.py',
                '-v', 'ArduCopter',  
                '--console',
                '--map',
                '--out=127.0.0.1:14550',
                '--out=127.0.0.1:14551'
            ]
            
            print("Starting SITL...")
            self.sitl_process = subprocess.Popen(
                sitl_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for SITL to initialize
            time.sleep(10)
            print("SITL started")
            return True

        except Exception as e:
            print(f"Error starting SITL: {e}")
            self.cleanup()
            return False

    def connect_to_server(self):
        """Connect to server with retry logic"""
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries and self.running:
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.connect((self.host, self.port))
                print(f"Connected to server at {self.host}:{self.port}")
                return True
            except socket.error as e:
                print(f"Server connection attempt {retry_count + 1} failed: {e}")
                retry_count += 1
                time.sleep(2)
                
        return False

    def get_vehicle_data(self):
        """Get vehicle data from SITL"""
        # Simulated data for now
        data = {
            "liveFlightDashboard": {
                "currentFlight": {
                    "flightName": f"SITL_FLIGHT_{self.start_time.strftime('%Y%m%d_%H%M')}",
                    "flightStatus": {
                        "status": "In Air",
                        "location": {
                            "latitude": -35.363261,
                            "longitude": 149.165230
                        },
                        "altitude": 50,
                        "speed": 15,
                        "angles": {
                            "pitch": 0,
                            "roll": 0,
                            "yaw": 0
                        }
                    },
                    "battery": {
                        "level": 100,
                        "estimatedTimeRemaining": 30
                    },
                    "flightMode": "GUIDED",
                    "alerts": {
                        "critical": [],
                        "warnings": []
                    }
                },
                "systemHealth": {
                    "overallStatus": "Good",
                    "components": {
                        "GPS": "Functional",
                        "communications": "Stable",
                        "propulsion": "Optimal"
                    }
                }
            }
        }
        return data

    def send_telemetry(self, data):
        """Send telemetry data with error handling"""
        try:
            message = json.dumps(data) + '\n'
            self.server_socket.sendall(message.encode('utf-8'))
            return True
        except socket.error as e:
            print(f"Error sending telemetry: {e}")
            return False

    def run(self):
        """Run the SITL client"""
        if not self.start_sitl():
            return

        try:
            if not self.connect_to_server():
                return

            print("\nStarting telemetry stream. Press Ctrl+C to stop.")
            while self.running:
                telemetry = self.get_vehicle_data()
                if not self.send_telemetry(telemetry):
                    print("Lost connection to server, attempting to reconnect...")
                    if not self.connect_to_server():
                        break
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nStopping SITL...")
        except Exception as e:
            print(f"\nError during operation: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources"""
        print("Starting cleanup...")
        
        if self.server_socket:
            try:
                self.server_socket.close()
                print("Server connection closed")
            except:
                pass

        if self.sitl_process:
            try:
                os.killpg(os.getpgid(self.sitl_process.pid), signal.SIGTERM)
                print("SITL process terminated")
            except:
                pass

        if self.mavproxy_process:
            try:
                os.killpg(os.getpgid(self.mavproxy_process.pid), signal.SIGTERM)
                print("MAVProxy process terminated")
            except:
                pass

        print("Cleanup complete")
        self.running = False

if __name__ == "__main__":
    client = SITLClient()
    try:
        client.run()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        client.cleanup()