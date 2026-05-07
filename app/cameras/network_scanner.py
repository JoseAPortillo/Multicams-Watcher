import socket
import requests
import ipaddress
import threading
import time
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Assuming pytapo has discovery, but for now, basic implementation
try:
    import pytapo
except ImportError:
    pytapo = None

class NetworkScanner:
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self.local_ip = self._discover_local_ip()
        self.network = self._get_network()

    def _discover_local_ip(self) -> str:
        """Discover the local IP address."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
            if local_ip and not local_ip.startswith("127."):
                return local_ip
        except OSError:
            pass
        finally:
            sock.close()

        try:
            hostname = socket.gethostname()
            candidates = set()
            for result in socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_DGRAM):
                candidates.add(result[4][0])
            try:
                candidates.update(socket.gethostbyname_ex(hostname)[2])
            except socket.gaierror:
                pass

            for candidate in candidates:
                if candidate and not candidate.startswith("127."):
                    return candidate
        except OSError:
            pass

        return "127.0.0.1"

    def _get_network(self) -> ipaddress.IPv4Network:
        """Get the local network range."""
        ip = ipaddress.IPv4Address(self.local_ip)
        return ipaddress.IPv4Network(f"{ip}/24", strict=False)

    def scan_network(self, progress_callback: Optional[callable] = None) -> List[Dict]:
        """Scan the network for cameras asynchronously."""
        if self.local_ip.startswith("192.168.1."):
            hosts = [f"192.168.1.{i}" for i in range(100, 201)]
        else:
            hosts = [str(ip) for ip in self.network.hosts()]

        print(f"[DEBUG] Scanning {len(hosts)} hosts: {hosts[:5]}...{hosts[-5:]}")
        detected_cameras = []
        total = len(hosts)
        completed = 0

        def scan_host(ip: str) -> Optional[Dict]:
            camera = self._detect_camera_at_ip(ip)
            return camera

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(scan_host, ip) for ip in hosts]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    print(f"[DEBUG] Detected camera: {result}")
                    detected_cameras.append(result)
                completed += 1
                if progress_callback:
                    progress_callback(completed / total)

        print(f"[DEBUG] Scan complete. Detected {len(detected_cameras)} cameras.")
        return detected_cameras

    def _detect_camera_at_ip(self, ip: str) -> Optional[Dict]:
        """Detect camera type at given IP."""
        print(f"[DEBUG] Checking IP: {ip}")
        # Check ESP32
        esp32_url = self._check_esp32(ip)
        if esp32_url:
            print(f"[DEBUG] ESP32 found at {ip}: {esp32_url}")
            return {"ip": ip, "type": "ESP32", "url": esp32_url}

        # Check Tapo
        tapo = self._check_tapo(ip)
        if tapo:
            print(f"[DEBUG] Tapo found at {ip}")
            return {"ip": ip, "type": "Tapo", "url_template": f"rtsp://{{RTSP_USER}}:{{RTSP_PASS}}@{ip}:554/stream2"}

        print(f"[DEBUG] No camera found at {ip}")
        return None

    def _check_esp32(self, ip: str) -> Optional[str]:
        """Check if IP is an ESP32 camera."""
        for port in (81, 81):
            print(f"[DEBUG] Trying ESP32 at {ip}:{port}")
            url = f"http://{ip}:{port}/stream"
            try:
                response = requests.get(
                    url,
                    timeout=(3.0, 8.0),
                    headers={"User-Agent": "MulticamsWatcher/1.0", "Accept": "multipart/x-mixed-replace, image/jpeg, */*"},
                    stream=True,
                    allow_redirects=False,
                )

                print(f"[DEBUG] ESP32 {ip}:{port} status: {response.status_code}, content-type: {response.headers.get('Content-Type', 'N/A')}")
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if any(sub in content_type.lower() for sub in ('multipart/x-mixed-replace', 'mjpeg', 'image')):
                        print(f"[DEBUG] ESP32 confirmed at {ip}:{port}")
                        return url
                    print(f"[DEBUG] ESP32 {ip}:{port} returned 200 but content-type was unexpected; accepting as ESP32")
                    return url
                if response.status_code in {401, 403, 404, 500}:
                    print(f"[DEBUG] ESP32 {ip}:{port} responded with {response.status_code}; accepting as likely ESP32")
                    return url
            except requests.ReadTimeout as e:
                print(f"[DEBUG] ESP32 {ip}:{port} read timeout: {e}")
                if self._is_port_open(ip, port):
                    print(f"[DEBUG] ESP32 {ip}:{port} port open after timeout; accepting as ESP32")
                    return url
            except requests.RequestException as e:
                print(f"[DEBUG] ESP32 {ip}:{port} failed: {e}")
                continue
        print(f"[DEBUG] No ESP32 at {ip}")
        return None

    def _is_port_open(self, ip: str, port: int) -> bool:
        try:
            with socket.create_connection((ip, port), timeout=2.5):
                return True
        except Exception:
            return False

    def _check_tapo(self, ip: str) -> bool:
        """Check if IP is a Tapo camera by validating RTSP service."""
        print(f"[DEBUG] Checking Tapo at {ip}:554")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((ip, 554))
            request = (
                f"OPTIONS rtsp://{ip}:554/ RTSP/1.0\r\n"
                "CSeq: 1\r\n"
                "User-Agent: MulticamsWatcher/1.0\r\n"
                "\r\n"
            ).encode("utf-8")
            sock.sendall(request)
            response = sock.recv(1024)
            sock.close()

            print(f"[DEBUG] Tapo response from {ip}: {response[:100]}...")
            if response.startswith(b"RTSP/1.0") and b"CSeq: 1" in response:
                print(f"[DEBUG] Tapo confirmed at {ip}")
                if pytapo:
                    try:
                        # If pytapo is installed and can identify the device, prefer that
                        # Here we simply trust the RTSP response as a stronger indicator.
                        return True
                    except Exception:
                        pass
                return True
        except Exception as e:
            print(f"[DEBUG] Tapo check failed for {ip}: {e}")
            pass
        print(f"[DEBUG] No Tapo at {ip}")
        return False

def scan_cameras(progress_callback: Optional[callable] = None) -> List[Dict]:
    """Convenience function to scan for cameras."""
    print("[DEBUG] Starting camera scan...")
    scanner = NetworkScanner()
    result = scanner.scan_network(progress_callback)
    print(f"[DEBUG] Camera scan completed, found {len(result)} cameras")
    return result