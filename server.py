"""
Wake-on-LAN сервер
Запускать на устройстве в той же локальной сети, что и целевой ПК
(например, Raspberry Pi, всегда включённый ПК, или роутер)
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
import struct
import json
import os
from urllib.parse import urlparse, parse_qs

# ─── Настройки ────────────────────────────────────────────────────────────────
PORT = 8080          # порт сервера
SECRET_TOKEN = os.environ.get("WOL_TOKEN", "marsela")  # токен для защиты
# ──────────────────────────────────────────────────────────────────────────────

# Список компьютеров (можно добавить сколько угодно)
COMPUTERS = {
    "my_pc": {
        "name": "DESKTOP-8POS5D5",
        "mac": "00:E2:69:9A:6F:95",   # Realtek Gaming 2.5GbE
        "broadcast": "192.168.31.255",
    },
    # Добавьте ещё компьютеры при необходимости:
    # "pc2": {
    #     "name": "Второй ПК",
    #     "mac": "11:22:33:44:55:66",
    #     "broadcast": "192.168.31.255",
    # },
}


def send_magic_packet(mac: str, broadcast: str = "255.255.255.255", port: int = 9):
    """Отправляет Wake-on-LAN магический пакет"""
    # Убираем разделители из MAC-адреса
    mac_clean = mac.replace(":", "").replace("-", "").replace(".", "")
    if len(mac_clean) != 12:
        raise ValueError(f"Неверный MAC-адрес: {mac}")

    # Формируем магический пакет: 6 байт 0xFF + MAC повторённый 16 раз
    mac_bytes = bytes.fromhex(mac_clean)
    magic_packet = b"\xff" * 6 + mac_bytes * 16

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, (broadcast, port))

    print(f"[WoL] Магический пакет отправлен на {mac} ({broadcast})")


# HTML страница с интерфейсом
HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wake-on-LAN</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f0f1a;
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        h1 { font-size: 1.6rem; margin-bottom: 8px; color: #fff; }
        p.subtitle { color: #888; margin-bottom: 32px; font-size: 0.9rem; }

        .token-section {
            background: #1a1a2e;
            border: 1px solid #333;
            border-radius: 12px;
            padding: 20px;
            width: 100%;
            max-width: 400px;
            margin-bottom: 24px;
        }
        .token-section label { font-size: 0.85rem; color: #aaa; display: block; margin-bottom: 8px; }
        .token-section input {
            width: 100%;
            padding: 10px 14px;
            background: #0f0f1a;
            border: 1px solid #444;
            border-radius: 8px;
            color: #fff;
            font-size: 1rem;
        }

        .computers { width: 100%; max-width: 400px; display: flex; flex-direction: column; gap: 12px; }

        .pc-card {
            background: #1a1a2e;
            border: 1px solid #333;
            border-radius: 16px;
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
        }
        .pc-info h2 { font-size: 1.1rem; }
        .pc-info span { font-size: 0.8rem; color: #666; font-family: monospace; }

        .wake-btn {
            background: linear-gradient(135deg, #6c63ff, #3ecfcf);
            border: none;
            border-radius: 50px;
            color: #fff;
            font-size: 0.95rem;
            font-weight: 600;
            padding: 12px 22px;
            cursor: pointer;
            transition: opacity 0.2s, transform 0.1s;
            white-space: nowrap;
        }
        .wake-btn:active { transform: scale(0.96); opacity: 0.85; }
        .wake-btn:disabled { opacity: 0.4; cursor: not-allowed; }

        #status {
            margin-top: 20px;
            padding: 12px 20px;
            border-radius: 10px;
            font-size: 0.9rem;
            display: none;
            max-width: 400px;
            width: 100%;
            text-align: center;
        }
        .status-ok { background: #1a3a2a; border: 1px solid #2d6a4f; color: #52b788; display: block !important; }
        .status-err { background: #3a1a1a; border: 1px solid #6a2d2d; color: #e07070; display: block !important; }
    </style>
</head>
<body>
    <h1>⚡ Wake-on-LAN</h1>
    <p class="subtitle">Включите компьютер одним нажатием</p>

    <div class="token-section">
        <label>Токен доступа</label>
        <input type="password" id="token" placeholder="Введите токен..." />
    </div>

    <div class="computers" id="computers">
        <!-- Карточки компьютеров вставляются через JS -->
    </div>

    <div id="status"></div>

    <script>
        const computers = COMPUTERS_JSON;

        const container = document.getElementById("computers");
        const statusEl = document.getElementById("status");

        Object.entries(computers).forEach(([id, pc]) => {
            const card = document.createElement("div");
            card.className = "pc-card";
            card.innerHTML = `
                <div class="pc-info">
                    <h2>🖥️ ${pc.name}</h2>
                    <span>${pc.mac}</span>
                </div>
                <button class="wake-btn" onclick="wake('${id}', this)">Включить</button>
            `;
            container.appendChild(card);
        });

        async function wake(pcId, btn) {
            const token = document.getElementById("token").value.trim();
            if (!token) {
                showStatus("Введите токен доступа", false);
                return;
            }

            btn.disabled = true;
            btn.textContent = "Отправка...";
            statusEl.className = "";
            statusEl.style.display = "none";

            try {
                const res = await fetch("/wake", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ token, pc_id: pcId })
                });
                const data = await res.json();
                showStatus(data.message, res.ok);
            } catch (e) {
                showStatus("Ошибка соединения с сервером", false);
            } finally {
                btn.disabled = false;
                btn.textContent = "Включить";
            }
        }

        function showStatus(msg, ok) {
            statusEl.textContent = ok ? "✅ " + msg : "❌ " + msg;
            statusEl.className = ok ? "status-ok" : "status-err";
        }
    </script>
</body>
</html>
"""


class WoLHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

    def send_json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            # Подставляем список компьютеров в HTML (только имя и MAC, без токена)
            safe_computers = {
                k: {"name": v["name"], "mac": v["mac"]}
                for k, v in COMPUTERS.items()
            }
            page = HTML_PAGE.replace(
                "COMPUTERS_JSON", json.dumps(safe_computers, ensure_ascii=False)
            )
            body = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_json(404, {"message": "Не найдено"})

    def do_POST(self):
        if self.path == "/wake":
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length))
            except Exception:
                self.send_json(400, {"message": "Неверный JSON"})
                return

            token = body.get("token", "")
            pc_id = body.get("pc_id", "")

            # Проверка токена
            if token != SECRET_TOKEN:
                self.send_json(403, {"message": "Неверный токен доступа"})
                return

            # Проверка компьютера
            if pc_id not in COMPUTERS:
                self.send_json(404, {"message": f"Компьютер '{pc_id}' не найден"})
                return

            pc = COMPUTERS[pc_id]
            try:
                send_magic_packet(pc["mac"], pc["broadcast"])
                self.send_json(200, {"message": f"Пакет отправлен на {pc['name']}"})
            except Exception as e:
                self.send_json(500, {"message": f"Ошибка: {e}"})
        else:
            self.send_json(404, {"message": "Не найдено"})


if __name__ == "__main__":
    print(f"Wake-on-LAN сервер запущен на порту {PORT}")
    print(f"Откройте в браузере: http://<IP-устройства>:{PORT}")
    print(f"Токен: {SECRET_TOKEN}")
    print("Нажмите Ctrl+C для остановки")
    server = HTTPServer(("0.0.0.0", PORT), WoLHandler)
    server.serve_forever()
