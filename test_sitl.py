from collections.abc import MutableMapping
import collections
collections.MutableMapping = MutableMapping

import dronekit_sitl
from dronekit import connect, VehicleMode
import json
import time
from datetime import datetime
import socket
import sys

class SITLTelemetryClient:
    def __init__(self, server_host='localhost', server_port=5760):
        self.server_host = server_host
        self.server_port = server_port
        self.sitl = None
        self.vehicle = None
        self.server_socket = None
        self.start_time = datetime.now()
        self.running = True

    def start_sitl(self):
        """Initialize SITL and connect vehicle"""
        try:
            print("Starting SITL...")
            self.sitl = dronekit_sitl.start_default()
            print("SITL started successfully")

            print("\nConnecting to vehicle...")
            self.vehicle = connect(self.sitl.connection_string(), wait_ready=True)
            print("Vehicle connected!")
            return True

        except Exception as e:
            print(f"SITL setup failed: {e}")
            self.cleanup()
            return False

    def connect_to_server(self):
        """Connect to telemetry server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.connect((self.server_host, self.server_port))
            print(f"Connected to server at {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"Server connection failed: {e}")
            return False

    def get_telemetry_data(self):
        """Get real vehicle telemetry data"""
        location = self.vehicle.location.global_relative_frame
        attitude = self.vehicle.attitude

        telemetry = {
            "liveFlightDashboard": {
                "currentFlight": {
                    "flightName": f"SITL_FLIGHT_{self.start_time.strftime('%Y%m%d_%H%M')}",
                    "flightStatus": {
                        "status": "In Air" if self.vehicle.armed else "On Ground",
                        "location": {
                            "latitude": location.lat,
                            "longitude": location.lon
                        },
                        "altitude": location.alt,
                        "speed": self.vehicle.groundspeed,
                        "angles": {
                            "pitch": attitude.pitch,
                            "roll": attitude.roll,
                            "yaw": attitude.yaw
                        }
                    },
                    "battery": {
                        "level": self.vehicle.battery.level if self.vehicle.battery.level else 100,
                        "voltage": self.vehicle.battery.voltage,
                        "current": self.vehicle.battery.current
                    },
                    "flightMode": self.vehicle.mode.name,
                    "alerts": {
                        "critical": [],
                        "warnings": []
                    }
                },
                "systemHealth": {
                    "overallStatus": "Good",
                    "components": {
                        "GPS": "Functional" if self.vehicle.gps_0.fix_type >= 3 else "No Fix",
                        "battery": "Good" if self.vehicle.battery.level > 20 else "Low",
                        "communications": "Stable"
                    }
                }
            }
        }
        return telemetry

    def send_telemetry(self, data):
        """Send telemetry data to server"""
        try:
            message = json.dumps(data) + '\n'
            self.server_socket.sendall(message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Failed to send telemetry: {e}")
            return False

    def run(self):
        """Run the SITL telemetry client"""
        if not self.start_sitl():
            return

        if not self.connect_to_server():
            self.cleanup()
            return

        print("\nStarting telemetry stream. Press Ctrl+C to stop.")
        try:
            while self.running:
                telemetry = self.get_telemetry_data()
                if not self.send_telemetry(telemetry):
                    print("Lost connection to server")
                    break
                print(".", end="", flush=True)
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nStopping gracefully...")
        except Exception as e:
            print(f"\nError during operation: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources"""
        print("\nCleaning up...")
        if self.vehicle:
            self.vehicle.close()
            print("Vehicle connection closed")
        if self.sitl:
            self.sitl.stop()
            print("SITL stopped")
        if self.server_socket:
            self.server_socket.close()
            print("Server connection closed")
        self.running = False
        print("Cleanup complete")

if __name__ == "__main__":
    # Get server details from command line or use defaults
    server_host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    server_port = int(sys.argv[2]) if len(sys.argv) > 2 else 5760

    client = SITLTelemetryClient(server_host, server_port)
    try:
        client.run()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        client.cleanup()
