import os
import sqlite3
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps

import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "shop.db")

FAZER_BASE = "https://api.fzr.cards/api/v2"
AKTIV_BASE = "https://ws2524.wineclo.com/AktivSimBot/api/v2/"

FAZER_API_KEY = os.getenv("FAZER_API_KEY", "fc_e2a3d96eda3c7f0bd6b4a139").strip()
AKTIV_API_KEY = os.getenv("AKTIVSIM_API_KEY", "YTvijKX0w1FHVGTv19i54ahe").strip()

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-this-password")

USD_UZS = Decimal(os.getenv("USD_UZS", "11600"))
MARKUP_UZS = Decimal(os.getenv("MARKUP_UZS", "4000"))


app = Flask(__name__)
app.secret_key = SECRET_KEY


# =========================
# DATABASE
# =========================

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    c = db()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        balance INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        kind TEXT NOT NULL,
        provider_order_id TEXT,
        target TEXT,
        quantity INTEGER,
        months INTEGER,
        api_usd REAL DEFAULT 0,
        sell_uzs INTEGER NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        type TEXT NOT NULL,
        note TEXT,
        created_at TEXT NOT NULL
    );
    """)

    c.commit()
    c.close()


# MUHIM:
# Hosting/Gunicorn orqali ishga tushganda ham database yaratiladi.
try:
    init_db()
except Exception as e:
    print("DATABASE ERROR:", e)


# =========================
# USER
# =========================

def me():
    uid = session.get("user_id")

    if not uid:
        return None

    try:
        c = db()
        u = c.execute(
            "SELECT * FROM users WHERE id=?",
            (uid,)
        ).fetchone()
        c.close()
        return u

    except Exception as e:
        print("ME ERROR:", e)
        return None


def user_required(f):
    @wraps(f)
    def w(*a, **k):

        if not me():
            flash("Avval login qiling.", "error")
            return redirect(url_for("login"))

        return f(*a, **k)

    return w


def admin_required(f):
    @wraps(f)
    def w(*a, **k):

        if not session.get("admin"):
            return redirect(url_for("admin_login"))

        return f(*a, **k)

    return w


# =========================
# FAZERCARDS
# =========================

def fazer(method, path, **kwargs):

    if not FAZER_API_KEY:
        return {
            "ok": False,
            "error": "FAZER_API_KEY sozlanmagan"
        }

    headers = kwargs.pop("headers", {}) or {}

    headers["X-API-Key"] = FAZER_API_KEY
    headers["Accept"] = "application/json"

    try:

        r = requests.request(
            method,
            FAZER_BASE + path,
            headers=headers,
            timeout=25,
            **kwargs
        )

        try:
            data = r.json()
        except ValueError:
            return {
                "ok": False,
                "error": f"FazerCards HTTP {r.status_code}: {r.text[:300]}"
            }

        if not isinstance(data, dict):
            return {
                "ok": r.status_code < 400,
                "result": data
            }

        if r.status_code >= 400:
            data.setdefault("ok", False)
            data.setdefault(
                "error",
                f"FazerCards HTTP {r.status_code}"
            )

        return data

    except requests.RequestException as e:

        print("FAZER API ERROR:", e)

        return {
            "ok": False,
            "error": str(e)
        }

    except Exception as e:

        print("FAZER ERROR:", e)

        return {
            "ok": False,
            "error": str(e)
        }


# =========================
# AKTIVSIM
# =========================

def aktiv(action, **params):

    if not AKTIV_API_KEY:
        return {
            "ok": False,
            "error": "AKTIVSIM_API_KEY sozlanmagan"
        }

    params.update({
        "action": action,
        "apikey": AKTIV_API_KEY
    })

    try:

        r = requests.get(
            AKTIV_BASE,
            params=params,
            timeout=20
        )

        try:
            return r.json()
        except ValueError:
            return {
                "ok": False,
                "error": f"AktivSIM HTTP {r.status_code}: {r.text[:300]}"
            }

    except requests.RequestException as e:

        print("AKTIV API ERROR:", e)

        return {
            "ok": False,
            "error": str(e)
        }

    except Exception as e:

        print("AKTIV ERROR:", e)

        return {
            "ok": False,
            "error": str(e)
        }


# =========================
# PRICE
# =========================

def price_usd_to_uzs(usd):

    return int(
        (
            Decimal(str(usd)) * USD_UZS
            + MARKUP_UZS
        ).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )


def add_tx(c, user_id, amount, typ, note):

    c.execute(
        """
        INSERT INTO transactions
        (user_id, amount, type, note, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            amount,
            typ,
            note,
            now()
        )
    )


# =========================
# TEMPLATE GLOBALS
# =========================

@app.context_processor
def globals_ctx():

    return {
        "me": me(),
        "markup": int(MARKUP_UZS),
        "usd_uzs": USD_UZS
    }


# =========================
# HOME
# =========================

@app.route("/")
def home():

    stars = fazer(
        "GET",
        "/telegram/stars"
    )

    premium = fazer(
        "GET",
        "/telegram/premium"
    )

    return render_template(
        "home.html",
        stars=stars,
        premium=premium
    )


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if len(username) < 3 or len(username) > 32:

            flash(
                "Login 3-32 belgi bo'lsin.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if len(password) < 8:

            flash(
                "Parol kamida 8 belgi bo'lsin.",
                "error"
            )

            return render_template(
                "register.html"
            )

        c = None

        try:

            c = db()

            password_hash = generate_password_hash(
                password
            )

            c.execute(
                """
                INSERT INTO users
                (username, password_hash, balance, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    username,
                    password_hash,
                    0,
                    now()
                )
            )

            c.commit()

            flash(
                "Akkaunt yaratildi. Endi login qiling.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except sqlite3.IntegrityError:

            flash(
                "Bu login band.",
                "error"
            )

        except Exception as e:

            print("REGISTER ERROR:", e)

            flash(
                "Akkaunt yaratishda xatolik: " + str(e),
                "error"
            )

        finally:

            if c:
                c.close()

    return render_template(
        "register.html"
    )


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        try:

            c = db()

            u = c.execute(
                """
                SELECT *
                FROM users
                WHERE username=?
                """,
                (username,)
            ).fetchone()

            c.close()

            if u and check_password_hash(
                u["password_hash"],
                password
            ):

                session.clear()
                session["user_id"] = u["id"]

                return redirect(
                    url_for("home")
                )

            flash(
                "Login yoki parol noto'g'ri.",
                "error"
            )

        except Exception as e:

            print("LOGIN ERROR:", e)

            flash(
                "Login xatosi: " + str(e),
                "error"
            )

    return render_template(
        "login.html"
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================
# PROFILE
# =========================

@app.route("/profile")
@user_required
def profile():

    c = db()

    tx = c.execute(
        """
        SELECT *
        FROM transactions
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 50
        """,
        (me()["id"],)
    ).fetchall()

    c.close()

    return render_template(
        "profile.html",
        tx=tx
    )


# =========================
# ORDERS
# =========================

@app.route("/orders")
@user_required
def orders():

    c = db()

    rows = c.execute(
        """
        SELECT *
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (me()["id"],)
    ).fetchall()

    c.close()

    return render_template(
        "orders.html",
        orders=rows
    )


@app.route("/order/<int:order_id>")
@user_required
def order(order_id):

    c = db()

    o = c.execute(
        """
        SELECT *
        FROM orders
        WHERE id=? AND user_id=?
        """,
        (
            order_id,
            me()["id"]
        )
    ).fetchone()

    c.close()

    if not o:
        return "Buyurtma topilmadi", 404

    return render_template(
        "order.html",
        o=o
    )


# =========================
# ORDER STATUS
# =========================

@app.route("/api/order/<int:order_id>/status")
@user_required
def order_status(order_id):

    c = db()

    o = c.execute(
        """
        SELECT *
        FROM orders
        WHERE id=? AND user_id=?
        """,
        (
            order_id,
            me()["id"]
        )
    ).fetchone()

    c.close()

    if not o:

        return jsonify(
            ok=False,
            error="Buyurtma topilmadi"
        ), 404

    if o["kind"] == "sim":

        r = aktiv(
            "getCode",
            order_id=o["provider_order_id"]
        )

        if (
            r.get("ok")
            and r.get("status") == "finished"
        ):

            c = db()

            c.execute(
                """
                UPDATE orders
                SET status='finished'
                WHERE id=?
                """,
                (order_id,)
            )

            c.commit()
            c.close()

        return jsonify(r)

    r = fazer(
        "GET",
        "/order/" + str(
            o["provider_order_id"]
        )
    )

    if r.get("ok"):

        data = r.get("order") or {}

        status = (
            data.get("status")
            or r.get("status")
        )

        if status:

            c = db()

            c.execute(
                """
                UPDATE orders
                SET status=?
                WHERE id=?
                """,
                (
                    status,
                    order_id
                )
            )

            c.commit()
            c.close()

    return jsonify(r)


# =========================
# STARS
# =========================

@app.route("/buy/stars", methods=["POST"])
@user_required
def buy_stars():

    target = request.form.get(
        "telegram_username",
        ""
    ).strip()

    try:
        qty = int(
            request.form.get(
                "quantity",
                "0"
            )
        )
    except:
        qty = 0

    if not target or qty <= 0:

        flash(
            "Username va Stars miqdorini kiriting.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    q = fazer(
        "GET",
        "/telegram/stars"
    )

    if not q.get("ok"):

        flash(
            q.get(
                "error",
                "Stars narxi olinmadi"
            ),
            "error"
        )

        return redirect(
            url_for("home")
        )

    try:

        min_q = int(
            q.get(
                "min_amount",
                50
            )
        )

        max_q = int(
            q.get(
                "max_amount",
                10000
            )
        )

    except:

        min_q = 50
        max_q = 10000

    if qty < min_q or qty > max_q:

        flash(
            f"Stars {min_q}-{max_q} oralig'ida bo'lishi kerak.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    try:

        total_usd = (
            Decimal(
                str(
                    q["price_per_star"]
                )
            ) * qty
        )

    except:

        flash(
            "API Stars narxini noto'g'ri qaytardi.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    sell = price_usd_to_uzs(
        total_usd
    )

    u = me()

    if u["balance"] < sell:

        flash(
            f"Balans yetarli emas. Kerak: {sell:,} so'm",
            "error"
        )

        return redirect(
            url_for("home")
        )

    r = fazer(
        "POST",
        "/telegram/stars/buy",
        json={
            "telegram_username": target,
            "quantity": qty
        },
        headers={
            "Idempotency-Key": str(
                uuid.uuid4()
            )
        }
    )

    if not r.get("ok"):

        flash(
            r.get(
                "error",
                "Stars buyurtmasi xatosi"
            ),
            "error"
        )

        return redirect(
            url_for("home")
        )

    od = (
        r.get("order")
        or r.get("result")
        or {}
    )

    provider_id = str(
        od.get("id")
        or od.get("order_id")
        or ""
    )

    status = od.get(
        "status",
        "processing"
    )

    c = db()

    c.execute(
        """
        UPDATE users
        SET balance=balance-?
        WHERE id=?
        """,
        (
            sell,
            u["id"]
        )
    )

    add_tx(
        c,
        u["id"],
        -sell,
        "purchase",
        f"Telegram Stars: {qty}"
    )

    c.execute(
        """
        INSERT INTO orders
        (
            user_id,
            kind,
            provider_order_id,
            target,
            quantity,
            api_usd,
            sell_uzs,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            u["id"],
            "stars",
            provider_id,
            target,
            qty,
            float(total_usd),
            sell,
            status,
            now()
        )
    )

    c.commit()

    oid = c.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]

    c.close()

    flash(
        "Stars buyurtmasi yuborildi.",
        "success"
    )

    return redirect(
        url_for(
            "order",
            order_id=oid
        )
    )


# =========================
# PREMIUM
# =========================

@app.route("/buy/premium", methods=["POST"])
@user_required
def buy_premium():

    target = request.form.get(
        "telegram_username",
        ""
    ).strip()

    try:
        months = int(
            request.form.get(
                "months",
                "0"
            )
        )
    except:
        months = 0

    if not target or months not in (3, 6, 12):

        flash(
            "Username yoki Premium muddati noto'g'ri.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    q = fazer(
        "GET",
        "/telegram/premium"
    )

    if not q.get("ok"):

        flash(
            q.get(
                "error",
                "Premium narxi olinmadi"
            ),
            "error"
        )

        return redirect(
            url_for("home")
        )

    plans = (
        q.get("plans")
        or q.get("result")
        or []
    )

    try:

        plan = next(
            (
                p for p in plans
                if int(
                    p.get(
                        "months",
                        0
                    )
                ) == months
            ),
            None
        )

    except:

        plan = None

    if not plan:

        flash(
            "Bu Premium rejasi API'da yo'q.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    try:

        total_usd = Decimal(
            str(
                plan["price_usd"]
            )
        )

    except:

        flash(
            "Premium API narxini noto'g'ri qaytardi.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    sell = price_usd_to_uzs(
        total_usd
    )

    u = me()

    if u["balance"] < sell:

        flash(
            f"Balans yetarli emas. Kerak: {sell:,} so'm",
            "error"
        )

        return redirect(
            url_for("home")
        )

    r = fazer(
        "POST",
        "/telegram/premium/buy",
        json={
            "telegram_username": target,
            "months": months
        },
        headers={
            "Idempotency-Key": str(
                uuid.uuid4()
            )
        }
    )

    if not r.get("ok"):

        flash(
            r.get(
                "error",
                "Premium buyurtmasi xatosi"
            ),
            "error"
        )

        return redirect(
            url_for("home")
        )

    od = (
        r.get("order")
        or r.get("result")
        or {}
    )

    provider_id = str(
        od.get("id")
        or od.get("order_id")
        or ""
    )

    status = od.get(
        "status",
        "processing"
    )

    c = db()

    c.execute(
        """
        UPDATE users
        SET balance=balance-?
        WHERE id=?
        """,
        (
            sell,
            u["id"]
        )
    )

    add_tx(
        c,
        u["id"],
        -sell,
        "purchase",
        f"Telegram Premium: {months} oy"
    )

    c.execute(
        """
        INSERT INTO orders
        (
            user_id,
            kind,
            provider_order_id,
            target,
            months,
            api_usd,
            sell_uzs,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            u["id"],
            "premium",
            provider_id,
            target,
            months,
            float(total_usd),
            sell,
            status,
            now()
        )
    )

    c.commit()

    oid = c.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]

    c.close()

    flash(
        "Premium buyurtmasi yuborildi.",
        "success"
    )

    return redirect(
        url_for(
            "order",
            order_id=oid
        )
    )


# =========================
# AKTIVSIM
# =========================

@app.route("/sim")
@user_required
def sim():

    r = aktiv(
        "getCountries"
    )

    countries = r.get(
        "result",
        []
    )

    if not isinstance(countries, list):
        countries = []

    return render_template(
        "sim.html",
        countries=countries,
        error=r.get("error")
    )


@app.route("/sim/buy/<country>", methods=["POST"])
@user_required
def sim_buy(country):

    r = aktiv(
        "getCountries"
    )

    cs = r.get(
        "result",
        []
    )

    if not isinstance(cs, list):
        cs = []

    item = next(
        (
            x for x in cs
            if x.get("country_code")
            == country.upper()
        ),
        None
    )

    if not item:

        flash(
            "Davlat topilmadi.",
            "error"
        )

        return redirect(
            url_for("sim")
        )

    try:

        sell = (
            int(item["price"])
            + int(MARKUP_UZS)
        )

    except:

        flash(
            "SIM narxini API noto'g'ri qaytardi.",
            "error"
        )

        return redirect(
            url_for("sim")
        )

    u = me()

    if u["balance"] < sell:

        flash(
            f"Balans yetarli emas. Kerak: {sell:,} so'm",
            "error"
        )

        return redirect(
            url_for("sim")
        )

    b = aktiv(
        "buyNumber",
        country_code=country.upper()
    )

    if not b.get("ok"):

        flash(
            b.get(
                "error",
                b.get(
                    "msg",
                    "AktivSIM xatosi"
                )
            ),
            "error"
        )

        return redirect(
            url_for("sim")
        )

    x = b.get(
        "result",
        {}
    )

    if not isinstance(x, dict):
        x = {}

    c = db()

    c.execute(
        """
        UPDATE users
        SET balance=balance-?
        WHERE id=?
        """,
        (
            sell,
            u["id"]
        )
    )

    add_tx(
        c,
        u["id"],
        -sell,
        "purchase",
        f"SIM: {x.get('phone', '')}"
    )

    c.execute(
        """
        INSERT INTO orders
        (
            user_id,
            kind,
            provider_order_id,
            target,
            api_usd,
            sell_uzs,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            u["id"],
            "sim",
            str(
                x.get(
                    "order_id",
                    ""
                )
            ),
            x.get(
                "phone",
                ""
            ),
            0,
            sell,
            "waiting",
            now()
        )
    )

    c.commit()

    oid = c.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]

    c.close()

    return redirect(
        url_for(
            "order",
            order_id=oid
        )
    )


# =========================
# TOPUP
# =========================

@app.route("/topup")
@user_required
def topup():

    return render_template(
        "topup.html"
    )


# =========================
# ADMIN LOGIN
# =========================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        if (
            request.form.get("username")
            == ADMIN_USERNAME
            and
            request.form.get("password")
            == ADMIN_PASSWORD
        ):

            session["admin"] = True

            return redirect(
                url_for("admin")
            )

        flash(
            "Admin login/parol noto'g'ri.",
            "error"
        )

    return render_template(
        "admin_login.html"
    )


# =========================
# ADMIN LOGOUT
# =========================

@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "admin",
        None
    )

    return redirect(
        url_for("admin_login")
    )


# =========================
# ADMIN
# =========================

@app.route("/admin")
@admin_required
def admin():

    c = db()

    users = c.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    orders_count = c.execute(
        "SELECT COUNT(*) FROM orders"
    ).fetchone()[0]

    sales = c.execute(
        """
        SELECT COALESCE(
            SUM(-amount),
            0
        )
        FROM transactions
        WHERE type='purchase'
        """
    ).fetchone()[0]

    deposits = c.execute(
        """
        SELECT COALESCE(
            SUM(amount),
            0
        )
        FROM transactions
        WHERE amount > 0
        """
    ).fetchone()[0]

    profit = c.execute(
        """
        SELECT COALESCE(
            SUM(
                sell_uzs - api_usd * ?
            ),
            0
        )
        FROM orders
        WHERE kind IN ('stars','premium')
        """,
        (float(USD_UZS),)
    ).fetchone()[0]

    c.close()

    fb = fazer(
        "GET",
        "/balance"
    )

    return render_template(
        "admin.html",
        users=users,
        orders_count=orders_count,
        sales=sales,
        deposits=deposits,
        profit=int(profit),
        fazer_balance=fb.get("balance"),
        fazer_error=fb.get("error")
    )


# =========================
# ADMIN USERS
# =========================

@app.route("/admin/users")
@admin_required
def admin_users():

    c = db()

    rows = c.execute(
        """
        SELECT *
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    c.close()

    return render_template(
        "admin_users.html",
        users=rows
    )


# =========================
# ADMIN BALANCE
# =========================

@app.route(
    "/admin/users/<int:uid>/balance",
    methods=["POST"]
)
@admin_required
def admin_balance(uid):

    try:
        amount = int(
            request.form.get(
                "amount",
                "0"
            )
        )
    except:
        amount = 0

    c = db()

    u = c.execute(
        "SELECT * FROM users WHERE id=?",
        (uid,)
    ).fetchone()

    if not u:

        c.close()

        return "User topilmadi", 404

    if u["balance"] + amount < 0:

        flash(
            "Balans manfiy bo'lmaydi.",
            "error"
        )

    elif amount == 0:

        flash(
            "Summa 0 bo'lmasin.",
            "error"
        )

    else:

        c.execute(
            """
            UPDATE users
            SET balance=balance+?
            WHERE id=?
            """,
            (
                amount,
                uid
            )
        )

        add_tx(
            c,
            uid,
            amount,
            "admin",
            request.form.get(
                "note",
                "Admin balans o'zgarishi"
            )
        )

        c.commit()

        flash(
            "Balans yangilandi.",
            "success"
        )

    c.close()

    return redirect(
        url_for("admin_users")
    )


# =========================
# HELP
# =========================

@app.route("/help")
def help_page():

    return render_template(
        "help.html"
    )


# =========================
# ROBOTS
# =========================

@app.route("/robots.txt")
def robots():

    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /profile\n"
        "Disallow: /orders\n",
        200,
        {
            "Content-Type": "text/plain"
        }
    )


# =========================
# RUN
# =========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                "10000"
            )
        ),
        debug=False
    )
