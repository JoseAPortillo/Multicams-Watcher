"""
Camera health monitoring and status notifications.
Runs in background thread.
"""
import time
import telepot


def monitor_cameras_health(streams: list, bot: telepot.Bot, chat_id_tg: str, interval: int = 2):
    """
    Background monitor: checks all camera states and notifies status changes.
    
    Args:
        streams: List of camera stream objects
        bot: Telepot bot instance
        chat_id_tg: Telegram chat ID for notifications
        interval: Check interval in seconds (default: 2)
    """
    while True:
        for cam in streams:
            try:
                cam.check_health()
                changes = cam.get_state_changes()
                now = time.time()

                for msg in changes:
                    # Avoid repeated notifications too frequently per camera.
                    if now - cam.last_status_message < cam.status_cooldown:
                        continue
                    cam.last_status_message = now

                    print(msg)
                    try:
                        bot.sendMessage(chat_id_tg, f"📡 {msg}")
                    except Exception as e:
                        print(f"Telegram monitor error ({cam.nombre}): {e}")
            except Exception as e:
                print(f"Health monitor error ({cam.nombre}): {e}")
        
        time.sleep(interval)
