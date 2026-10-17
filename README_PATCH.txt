DONUZ web/bot patch

Tuzatishlar: static papka yoki loyiha ildizidan sayt fayllarini topish; login tasdiqlangach forma yashirilishi; o‘yin va paket kartalarida lokal SVG rasmlar; mobil dizayn. bot.py dagi buyurtma, narx va API logikasi o‘zgartirilmadi.

Render: bot servisi Start Command: python bot.py va RUN_MODE=bot. Web servisi Start Command: python web_server.py. Har ikkala servisda DATABASE_URL bir xil PostgreSQL bazaga ulangan bo‘lsin. BOT_TOKEN, ADMIN_ID, BAY2GAME_API_KEY mavjud qiymatlaringizni saqlang.
