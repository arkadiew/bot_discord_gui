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

