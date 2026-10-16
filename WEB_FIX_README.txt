DONUZ - Render tuzatish

MUHIM: Bu arxiv bot.py ichidagi Web API root yo'lini tuzatadi, shunda eski saytingizdagi templates/index.html (yoki templates/home.html/templates/main.html) asosiy sahifa bo'lib ochiladi va /static/... fayllari beriladi.

Eski GitHub Sayt loyihangizdagi static/ va templates/ papkalarini o'chirmang. Ularni shu loyiha papkasiga qaytaring/ko'chiring. Ushbu ZIP ularning original HTML/CSS/JS fayllarini o'z ichiga olmaydi.

Render Start Command (agar shu servis bot + API ni birga ishga tushirayotgan bo'lsa):
python bot.py

Build Command:
pip install -r requirements.txt

API health check: /health
API catalog: /api/catalog

Bu arxiv original saytning static/templates fayllarisiz mustaqil sayt dizaynini tiklay olmaydi. Ularni eski GitHub repository'dan saqlab qolish kerak.
