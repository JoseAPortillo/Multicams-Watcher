"""
Telegram bot command handlers.
All commands receive 'streams' as a parameter to avoid globals.
"""
import telepot


def send_help(bot: telepot.Bot, target_chat_id: str):
    """Send help menu with all available commands."""
    menu = ("🤖 Available commands:\n"
            "/foto - See what's happening right now\n"
            "/alarma_on - Activate AI alerts\n"
            "/alarma_off - Silence alerts\n"
            "/status - View system status\n"
            "/arriba /abajo /izquierda /derecha - Move camera\n"
            "/reset - Recenter/calibrate (if supported)")
    bot.sendMessage(target_chat_id, menu)


def cmd_foto(bot: telepot.Bot, target_chat_id: str, streams: list):
    """Capture and send current frame from all cameras."""
    bot.sendMessage(target_chat_id, "📸 Capturing images...")
    for s in streams:
        if s.frame is not None:
            s.send_telegram_alert(s.frame)


def cmd_alarma(bot: telepot.Bot, target_chat_id: str, streams: list, enabled: bool):
    """Enable or disable alarm notifications."""
    for s in streams:
        s.alarm_enabled = enabled
    bot.sendMessage(
        target_chat_id,
        "🔔 Surveillance system ACTIVATED." if enabled else "🔕 Surveillance system DEACTIVATED.",
    )


def cmd_status(bot: telepot.Bot, target_chat_id: str, streams: list):
    """Send system status report."""
    estado = "ENABLED" if streams and streams[0].alarm_enabled else "DISABLED"
    bot.sendMessage(
        target_chat_id,
        f"📊 System status:\nOnline cameras: {len(streams)}\nAlarm: {estado}",
    )


def cmd_move(bot: telepot.Bot, target_chat_id: str, streams: list, dx: int, dy: int, message: str):
    """Move all cameras by (dx, dy) offset."""
    for s in streams:
        s.move(dx, dy)
    bot.sendMessage(target_chat_id, message)


def cmd_reset(bot: telepot.Bot, target_chat_id: str, streams: list):
    """Reset all cameras to center position."""
    for s in streams:
        if getattr(s, "tapo_client", None):
            s.tapo_client.uncalibrate()
    bot.sendMessage(target_chat_id, "🔄 Resetting position...")


def build_handlers(bot: telepot.Bot, target_chat_id: str, streams: list) -> dict:
    """
    Build command handlers dict.
    handlers[command] = lambda to execute.
    """
    return {
        "/foto": lambda: cmd_foto(bot, target_chat_id, streams),
        "/alarma_on": lambda: cmd_alarma(bot, target_chat_id, streams, True),
        "/alarma_off": lambda: cmd_alarma(bot, target_chat_id, streams, False),
        "/ayuda": lambda: send_help(bot, target_chat_id),
        "/status": lambda: cmd_status(bot, target_chat_id, streams),
        "/arriba": lambda: cmd_move(bot, target_chat_id, streams, 0, 15, "🔼 Moving up"),
        "/abajo": lambda: cmd_move(bot, target_chat_id, streams, 0, -15, "🔽 Moving down"),
        "/izquierda": lambda: cmd_move(bot, target_chat_id, streams, -15, 0, "◀️ Turning left"),
        "/derecha": lambda: cmd_move(bot, target_chat_id, streams, 15, 0, "▶️ Turning right"),
        "/reset": lambda: cmd_reset(bot, target_chat_id, streams),
    }


def handle_telegram_message(msg: dict, bot: telepot.Bot, streams: list, chat_id_tg: str):
    """
    Telegram message handler.
    Parses command and routes to appropriate handler.
    """
    print(f"DEBUG: Received something from Telegram: {msg}")
    content_type, chat_type, chat_id = telepot.glance(msg)

    if content_type != 'text':
        return

    command = msg['text'].strip().lower()
    print(f"Received command: {command}")

    # Build handlers for this chat
    handlers = build_handlers(bot, chat_id, streams)
    
    # Execute handler if exists
    handler = handlers.get(command)
    if handler:
        handler()
        return

    bot.sendMessage(chat_id, "Unrecognized command. Type /ayuda.")
