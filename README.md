# 🤖 Discord Bot GUI 

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![py-cord](https://img.shields.io/badge/py--cord-2.x-blueviolet?logo=discord)
![License](https://img.shields.io/badge/License-GPLv3-green)

Графический лаунчер (**pygame**) для Discord-бота на **py-cord** с поддержкой **динамической загрузки контроллеров**.  
Контроллеры — это модули команд, которые можно подключать и настраивать прямо через GUI.  


## ✨ Возможности
- 🎮 **GUI (pygame)** для запуска/остановки бота  
- 🔑 Хранение токена в `.env` (автосохранение)  
- ⚙️ Редактирование настроек контроллеров через интерфейс  
- 📂 Автопоиск и загрузка файлов `controller_*.py`  
- 📌 Примеры контроллеров:  
  - 🏓 `controller_ping.py` — простая команда `!ping`  
  - 🛡 `controller_admin.py` — админ-команды (`ban`, `kick`, `mute`)  

## 📂 Структура проекта
```
project/
│  main.py                 # GUI (pygame)
│  bot.py                  # Основной класс бота
│  controllers.py          # Загрузчик контроллеров
│  settings.json           # Автоматически создается
│  .env                    # Хранит токен DISCORD_TOKEN
└─ controller/
   └─ modals/
      ├─ controller_ping.py     # Пример: команда !ping
      └─ controller_admin.py    # Пример: админ-команды
```
> [!IMPORTANT]  
> Без корректного `DISCORD_TOKEN` бот не запустится. Получите токен в [Discord Developer Portal](https://discord.com/developers/applications).  

## 🛠 Создание своего контроллера
Все контроллеры находятся в `controller/modals/`.  

📌 Шаблон контроллера:

```python
# controller/modals/controller_hello.py
from discord.ext import commands
import json, os

class ControllerHello:
    def __init__(self, bot, register_commands=True, load_settings_flag=True):
        self.bot = bot
        self.settings = self.get_default_settings()
        if load_settings_flag:
            self.load_settings()
        if register_commands:
            self.register_commands()

    @staticmethod
    def get_default_settings():
        return {"enabled": True, "greeting": "Hello, world!"}

    def load_settings(self):
        # Загружаем настройки из settings.json
        ...

    def save_settings(self):
        # Сохраняем настройки в settings.json
        ...

    def register_commands(self):
        if not self.settings.get("enabled", True):
            return

        @self.bot.command(name="hello")
        async def hello(ctx):
            await ctx.send(self.settings["greeting"])
```

> [!TIP]  
> Используйте `type(self).__name__` при сохранении/загрузке настроек, чтобы не дублировать название класса вручную.

## 📌 Примеры
- 🏓 **Ping** — `!ping` → бот отвечает "Pong!"  
- 🛡 **Admin** — `!ban`, `!kick`, `!mute` (только для админов)  

> [!NOTE]  
> Примеры (`controller_ping.py`, `controller_admin.py`) можно использовать как **шаблоны** для собственных контроллеров.  

> [!CAUTION]  
> Если не включить **Message Content Intent**, бот не сможет читать сообщения и реагировать на команды.  

> [!WARNING]  
> Никогда не публикуйте свой `DISCORD_TOKEN` публично! Это даст полный доступ к вашему боту.  
