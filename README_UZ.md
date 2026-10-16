# DONUZ — PostgreSQL + Telegram bot + website

## Muhim ogohlantirish
Bu paketdagi `bot.py` mavjud `bot_supabase_draft.py` asosidagi PostgreSQL-ga moslashtirilgan kod. Uni ishlab turgan loyihaga birdan almashtirmang. Eski bazani o‘zgartirmang va Render Disk fayllarini o‘chirmang. Avval PostgreSQL bazangizni zaxiralang, jadvallar va balanslar sonini solishtiring. Bu paket mavjud SQLite ma’lumotlarini avtomatik ko‘chirmaydi.

## GitHub fayl tuzilishi
- `bot.py` — Telegram bot va umumiy API biznes-logikasi
- `web_server.py` — alohida Render Web Service uchun sayt/API
- `static/index.html`, `static/style.css`, `static/script.js` — sayt
- `templates/` — ushbu oddiy statik sahifa uchun shart emas
- `requirements.txt` — Python kutubxonalari

## Render sozlamalari
1. PostgreSQL provayderida yangi baza oching yoki mavjud bazangizning backupini oling.
2. `bot.py` ishlaydigan servis: Start Command `python bot.py`.
3. Sayt uchun alohida **Web Service** yarating: Start Command `python web_server.py`.
4. Ikkala servisda bir xil `DATABASE_URL` bo‘lsin (PostgreSQL connection string, parolni chatga yubormang).
5. Bot servisida `BOT_TOKEN` va koddagi boshqa kerakli environment variable’larni o‘rnating. Admin ID/servis API kalitlarini ham Environment Variables’da kiriting.
6. Build Command: `pip install -r requirements.txt`.
7. Sayt servisining `PORT` qiymatini Render o‘zi beradi; kod undan foydalanadi.
8. Deploy’dan keyin sayt `/` sahifasini, `/api/catalog` endpointini tekshiring. Botda `/start` yuborib, keyin Telegram ID bilan loginni sinang.

## Ma’lumotlarni saqlash
`DATABASE_URL`ni o‘zgartirishdan oldin eski DB backup qiling. Eski SQLite faylni yangi PostgreSQL deb ko‘rsatib bo‘lmaydi: alohida migratsiya kerak. Jadvallar nomi, ustunlari va ma’lumot turlarini solishtirmasdan eski bazani o‘chirmang.

## Eslatma
Sayt katalogi botdagi `web_catalog()` funksiyasi qaytargan ma’lumotga tayanadi. Agar katalog bo‘sh bo‘lsa, bot bazasida o‘yin/paketlar sozlanganini tekshiring. Provider API bilan real top-up ishlashi provider sozlamalari va mavjud bot funksiyalariga bog‘liq; deploydan oldin test buyurtma bilan tekshiring.
