# Wake-on-LAN
Включайте компьютер с телефона одним нажатием.

---

## Как это работает

```
Телефон → HTTP запрос → Сервер (Raspberry Pi / роутер) → WoL пакет → ПК включается
```

Сервер должен находиться **в той же локальной сети**, что и целевой ПК.

---

## Шаг 1 — Включите Wake-on-LAN на ПК

### Windows:
1. Диспетчер устройств → Сетевые адаптеры → ваш адаптер → Свойства
2. Вкладка "Управление электропитанием" → включить "Разрешить этому устройству выводить компьютер из ждущего режима"
3. Вкладка "Дополнительно" → найти "Wake on Magic Packet" → включить

### BIOS/UEFI:
- Найдите опцию "Wake on LAN" или "Power On By PCI-E" и включите её

---

## Шаг 2 — Узнайте MAC-адрес ПК

**Windows** (в командной строке):
```
ipconfig /all
```
Ищите строку "Физический адрес" у вашего сетевого адаптера.
Пример: `AA-BB-CC-DD-EE-FF`

---

## Шаг 3 — Настройте сервер

Откройте `server.py` и измените:

```python
COMPUTERS = {
    "my_pc": {
        "name": "Мой компьютер",          # название (отображается на кнопке)
        "mac": "AA:BB:CC:DD:EE:FF",        # ← ВАШ MAC-адрес
        "broadcast": "192.168.1.255",      # ← широковещательный адрес сети
    },
}
```

Широковещательный адрес обычно — последний октет заменить на 255.
Если ваш IP `192.168.0.105`, то broadcast = `192.168.0.255`.

---

## Шаг 4 — Установите токен

Токен защищает сервер от посторонних. Задайте его через переменную окружения:

```bash
# Linux / macOS / Raspberry Pi
export WOL_TOKEN="придумайте_свой_токен"
python3 server.py

# Windows PowerShell
$env:WOL_TOKEN="придумайте_свой_токен"
python server.py
```

Или просто измените значение по умолчанию в коде:
```python
SECRET_TOKEN = os.environ.get("WOL_TOKEN", "придумайте_свой_токен")
```

---

## Шаг 5 — Запустите сервер

```bash
python3 server.py
```

Сервер запустится на порту `8080`.

---

## Шаг 6 — Откройте с телефона

1. Убедитесь, что телефон в той же Wi-Fi сети
2. Узнайте IP устройства где запущен сервер:
   - Linux: `hostname -I`
   - Windows: `ipconfig`
3. Откройте в браузере телефона: `http://192.168.1.XXX:8080`
4. Введите токен и нажмите "Включить"

---

## Автозапуск на Raspberry Pi (опционально)

Создайте systemd сервис `/etc/systemd/system/wol.service`:

```ini
[Unit]
Description=Wake-on-LAN Server
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/wol_server/server.py
Environment=WOL_TOKEN=ваш_токен
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable wol
sudo systemctl start wol
```

---


