import argparse
import os
import socket


def discover_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Run the camera web server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the web server to.")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the web server to.")
    parser.add_argument(
        "--pc-dev",
        action="store_true",
        help="Development mode for prototyping on PC without requiring Telegram or health monitor.",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Use simulated cameras instead of real RTSP/HTTP cameras.",
    )
    parser.add_argument(
        "--sim-cameras",
        type=int,
        default=3,
        help="Number of simulated cameras to create when using --simulate.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.pc_dev:
        os.environ["CONTROL_APP_DISABLE_TELEGRAM"] = "1"
        os.environ["CONTROL_APP_DISABLE_HEALTH_MONITOR"] = "1"
    if args.simulate:
        os.environ["CONTROL_APP_SIMULATE"] = "1"
        os.environ["CONTROL_APP_SIM_CAMERA_COUNT"] = str(max(1, args.sim_cameras))

    local_ip = discover_local_ip()
    print(f"Server listening on http://127.0.0.1:{args.port}/")
    print(f"Access from local network at http://{local_ip}:{args.port}/")
    if args.pc_dev:
        print("PC/dev mode active: Telegram and health monitor disabled.")
    if args.simulate:
        print(f"Simulation mode active: {max(1, args.sim_cameras)} simulated cameras.")

    try:
        import uvicorn
    except ModuleNotFoundError:
        print("Missing dependency 'uvicorn'. Run: pip install -r requirements.txt")
        raise

    uvicorn.run("app.web.server_api:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
