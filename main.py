# bot developer @im_jisshu
# Koyeb Web Service health server + Telegram bot

import os
from threading import Thread

from app import app as health_app
from bot import Bot


def run_health_server():
    # Koyeb exposes the service port through PORT (normally 8080).
    port = int(os.environ.get("PORT", "8080"))
    health_app.run(host="0.0.0.0", port=port, use_reloader=False)


# Start the HTTP server first so Koyeb's TCP health check can connect.
Thread(target=run_health_server, daemon=True).start()

app = Bot()
app.run()
