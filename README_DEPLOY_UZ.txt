DONUZ BAY2GAME — tuzatilgan loyiha

ZIP ichidagi papka: DONUZ_WEB_BOT_FIX

1) Render Bot servisi
   - Root Directory: DONUZ_WEB_BOT_FIX (yoki repoda shu papka ichidagi fayllarni rootga qo'ying)
   - Build Command: pip install -r requirements.txt
   - Start Command: python bot.py
   - Environment Variables:
     BOT_TOKEN = asosiy Telegram bot tokeni
     ADMIN_ID = admin Telegram raqami
     BAY2GAME_API_KEY = Bay2Game API kaliti
     DATABASE_URL = PostgreSQL connection URL
     RUN_MODE = bot
     BAY2GAME_USD_UZS = kurs (ixtiyoriy, default 13000)

2) Render Web Service — alohida servis
   - Xuddi shu repository va papka
   - Build Command: pip install -r requirements.txt
   - Start Command: python web_server.py
   - Environment Variables: aynan shu DATABASE_URL, BOT_TOKEN, ADMIN_ID, BAY2GAME_API_KEY
   - PORT Render tomonidan avtomatik beriladi.

MUHIM:
- Bitta BOT_TOKEN bilan faqat BIRTA servis polling qilishi mumkin. Bot servisida python bot.py va RUN_MODE=bot bo'lsin. Web servisning start command'i python web_server.py bo'lsin.
- Agar eski Render servis ham python bot.py ishlatayotgan bo'lsa, uni to'xtating yoki start command'ini o'zgartiring; aks holda Telegram Conflict xatosi qaytadi.
- Bot startupdan 15 soniya o'tib API katalogini sinxronlaydi va keyin har 6 soatda yangilaydi. Admin paneldagi Katalog tugmasi ham qoladi.
- Grand Mobile manual katalogi va narxlari API sinxronlashida o'zgartirilmaydi.
- ZIP'ni joylagandan so'ng Render logs'da "Avtomatik katalog yangilandi" yoki sababini ko'rsatuvchi xabarni tekshiring.
