DONUZ tugma / static fayl tuzatishi

Bu paketda style.css va script.js mavjud; web_server.py endi /, /style.css va /script.js yo'llarini haqiqiy fayllardan beradi. API endpointlar bot.py dagi mavjud WebAPIHandler orqali ishlaydi.

Render WEB SERVICE:
- Root Directory: donuz_dual_service (agar repoga ichidagi fayllar to'g'ridan-to'g'ri yuklansa, bo'sh qoldiring)
- Build Command: pip install -r requirements.txt
- Start Command: python web_server.py
- DATABASE_URL: bot servisi bilan aynan bir xil PostgreSQL URL
- Bot token va kerakli API ENV qiymatlarini web servisga ham qo'shing, chunki web login kodi bot orqali yuboriladi.

Telegram bot polling faqat bitta servisda ishga tushsin. Bot servisi: python bot.py. Web servisi: python web_server.py.

Muhim: Telegram ID bilan kirish uchun foydalanuvchi avval botda /start bosgan va shu ID users jadvalida bo'lishi kerak. Bu paketdagi frontend kod olish/tasdiqlash, katalog, ID tekshirish va buyurtma tugmalarini API'ga ulaydi. Real deploydan so'ng /style.css va /script.js javoblari 200 bo'lishini tekshiring.
