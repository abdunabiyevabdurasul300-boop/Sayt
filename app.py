import os
import sqlite3
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps

import requests
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash


# =========================================================
# SETTINGS
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "shop.db")

FAZER_BASE = "https://api.fzr.cards/api/v2"
AKTIV_BASE = "https://ws2524.wineclo.com/AktivSimBot/api/v2/"

FAZER_API_KEY = os.getenv("FAZER_API_KEY", "").strip()
AKTIV_API_KEY = os.getenv("AKTIVSIM_API_KEY", "").strip()

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-this-password")

try:
    USD_UZS = Decimal(os.getenv("USD_UZS", "12500"))
except Exception:
    USD_UZS = Decimal("12500")

try:
    MARKUP_UZS = Decimal(os.getenv("MARKUP_UZS", "2000"))
except Exception:
    MARKUP_UZS = Decimal("2000")

PORT = int(os.getenv("PORT", "10000"))


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Login/sessionni saqlash uchun
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# HTTPS bo'lsa True
if os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true":
    app.config["SESSION_COOKIE_SECURE"] = True


# =========================================================
# DATABASE
# =========================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    conn = db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        balance INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        kind TEXT NOT NULL,
        provider_order_id TEXT,
        target TEXT,
        quantity INTEGER,
        months INTEGER,
        api_usd REAL DEFAULT 0,
        sell_uzs INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'processing',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        type TEXT NOT NULL,
        note TEXT,
        created_at TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()


# =========================================================
# USER
# =========================================================

def me():
    user_id = session.get("user_id")

    if not user_id:
        return None

    conn = db()

    try:
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
    finally:
        conn.close()

    return user


def user_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not me():
            flash("Avval akkauntga kiring.", "error")
            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))

        return func(*args, **kwargs)

    return wrapper


# =========================================================
# API - FAZERCARDS
# =========================================================

def fazer(method, path, **kwargs):

    if not FAZER_API_KEY:
        return {
            "ok": False,
            "error": "FAZER_API_KEY sozlanmagan."
        }

    headers = kwargs.pop("headers", {}) or {}

    headers["X-API-Key"] = FAZER_API_KEY
    headers["Accept"] = "application/json"

    try:

        response = requests.request(
            method,
            FAZER_BASE + path,
            headers=headers,
            timeout=25,
            **kwargs
        )

        try:
            data = response.json()
        except Exception:
            return {
                "ok": False,
                "error": (
                    f"FazerCards HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                )
            }

        if not isinstance(data, dict):
            return {
                "ok": False,
                "error": "API noto'g'ri javob qaytardi."
            }

        if response.status_code >= 400:

            if "ok" not in data:
                data["ok"] = False

            if "error" not in data:
                data["error"] = f"HTTP {response.status_code}"

        return data

    except requests.RequestException as e:

        return {
            "ok": False,
            "error": f"FazerCards ulanish xatosi: {e}"
        }

    except Exception as e:

        return {
            "ok": False,
            "error": f"FazerCards xatosi: {e}"
        }


# =========================================================
# API - AKTIVSIM
# =========================================================

def aktiv(action, **params):

    if not AKTIV_API_KEY:
        return {
            "ok": False,
            "error": "AKTIVSIM_API_KEY sozlanmagan."
        }

    params["action"] = action
    params["apikey"] = AKTIV_API_KEY

    try:

        response = requests.get(
            AKTIV_BASE,
            params=params,
            timeout=20
        )

        try:
            data = response.json()
        except Exception:
            return {
                "ok": False,
                "error": (
                    f"AktivSIM HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                )
            }

        if not isinstance(data, dict):
            return {
                "ok": False,
                "error": "AktivSIM noto'g'ri javob qaytardi."
            }

        return data

    except requests.RequestException as e:

        return {
            "ok": False,
            "error": f"AktivSIM ulanish xatosi: {e}"
        }

    except Exception as e:

        return {
            "ok": False,
            "error": f"AktivSIM xatosi: {e}"
        }


# =========================================================
# PRICE
# =========================================================

def price_usd_to_uzs(usd):

    result = (
        Decimal(str(usd)) * USD_UZS
        + MARKUP_UZS
    )

    return int(
        result.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )


def add_tx(conn, user_id, amount, tx_type, note):

    conn.execute(
        """
        INSERT INTO transactions
        (user_id, amount, type, note, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            amount,
            tx_type,
            note,
            now()
        )
    )


# =========================================================
# TEMPLATE GLOBALS
# =========================================================

@app.context_processor
def globals_ctx():

    return {
        "me": me(),
        "markup": int(MARKUP_UZS),
        "usd_uzs": USD_UZS
    }


# =========================================================
# HOME
# =========================================================

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


# =========================================================
# REGISTER
# =========================================================

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
                "Login 3-32 belgidan iborat bo'lsin.",
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

        conn = db()

        try:

            password_hash = generate_password_hash(
                password
            )

            conn.execute(
                """
                INSERT INTO users
                (username, password_hash, balance, created_at)
                VALUES (?, ?, 0, ?)
                """,
                (
                    username,
                    password_hash,
                    now()
                )
            )

            conn.commit()

            flash(
                "Akkaunt muvaffaqiyatli yaratildi.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except sqlite3.IntegrityError:

            flash(
                "Bu login allaqachon band.",
                "error"
            )

        except Exception as e:

            flash(
                f"Akkaunt yaratishda xato: {e}",
                "error"
            )

        finally:
            conn.close()

    return render_template(
        "register.html"
    )


# =========================================================
# LOGIN
# =========================================================

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

        conn = db()

        try:

            user = conn.execute(
                """
                SELECT *
                FROM users
                WHERE username = ?
                """,
                (username,)
            ).fetchone()

        finally:
            conn.close()

        if user:

            try:
                password_ok = check_password_hash(
                    user["password_hash"],
                    password
                )
            except Exception:
                password_ok = False

            if password_ok:

                session.clear()

                session["user_id"] = user["id"]

                session.permanent = True

                flash(
                    "Akkauntga muvaffaqiyatli kirdingiz.",
                    "success"
                )

                return redirect(
                    url_for("home")
                )

        flash(
            "Login yoki parol noto'g'ri.",
            "error"
        )

    return render_template(
        "login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
@user_required
def profile():

    user = me()

    conn = db()

    try:

        transactions = conn.execute(
            """
            SELECT *
            FROM transactions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (user["id"],)
        ).fetchall()

    finally:
        conn.close()

    return render_template(
        "profile.html",
        tx=transactions
    )


# =========================================================
# ORDERS
# =========================================================

@app.route("/orders")
@user_required
def orders():

    user = me()

    conn = db()

    try:

        rows = conn.execute(
            """
            SELECT *
            FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user["id"],)
        ).fetchall()

    finally:
        conn.close()

    return render_template(
        "orders.html",
        orders=rows
    )


@app.route("/order/<int:order_id>")
@user_required
def order(order_id):

    user = me()

    conn = db()

    try:

        order_data = conn.execute(
            """
            SELECT *
            FROM orders
            WHERE id = ?
            AND user_id = ?
            """,
            (
                order_id,
                user["id"]
            )
        ).fetchone()

    finally:
        conn.close()

    if not order_data:

        return (
            "Buyurtma topilmadi",
            404
        )

    return render_template(
        "order.html",
        o=order_data
    )


# =========================================================
# ORDER STATUS
# =========================================================

@app.route(
    "/api/order/<int:order_id>/status"
)
@user_required
def order_status(order_id):

    user = me()

    conn = db()

    try:

        order_data = conn.execute(
            """
            SELECT *
            FROM orders
            WHERE id = ?
            AND user_id = ?
            """,
            (
                order_id,
                user["id"]
            )
        ).fetchone()

    finally:
        conn.close()

    if not order_data:

        return jsonify(
            ok=False,
            error="Buyurtma topilmadi"
        ), 404

    # SIM
    if order_data["kind"] == "sim":

        result = aktiv(
            "getCode",
            order_id=order_data["provider_order_id"]
        )

        if (
            result.get("ok")
            and result.get("status") == "finished"
        ):

            conn = db()

            try:

                conn.execute(
                    """
                    UPDATE orders
                    SET status = 'finished'
                    WHERE id = ?
                    """,
                    (order_id,)
                )

                conn.commit()

            finally:
                conn.close()

        return jsonify(result)

    # FAZER
    provider_id = order_data[
        "provider_order_id"
    ]

    if not provider_id:

        return jsonify(
            ok=False,
            error="Provider order ID mavjud emas."
        )

    result = fazer(
        "GET",
        "/order/" + str(provider_id)
    )

    if result.get("ok"):

        order_info = (
            result.get("order")
            or result.get("result")
            or {}
        )

        if isinstance(order_info, dict):

            status = (
                order_info.get("status")
                or result.get("status")
            )

            if status:

                conn = db()

                try:

                    conn.execute(
                        """
                        UPDATE orders
                        SET status = ?
                        WHERE id = ?
                        """,
                        (
                            status,
                            order_id
                        )
                    )

                    conn.commit()

                finally:
                    conn.close()

    return jsonify(result)


# =========================================================
# BUY STARS
# =========================================================

@app.route(
    "/buy/stars",
    methods=["POST"]
)
@user_required
def buy_stars():

    target = request.form.get(
        "telegram_username",
        ""
    ).strip()

    try:
        quantity = int(
            request.form.get(
                "quantity",
                "0"
            )
        )
    except Exception:
        quantity = 0

    if not target or quantity <= 0:

        flash(
            "Username va Stars miqdorini kiriting.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    query = fazer(
        "GET",
        "/telegram/stars"
    )

    if not query.get("ok"):

        flash(
            query.get(
                "error",
                "Stars narxi olinmadi."
            ),
            "error"
        )

        return redirect(
            url_for("home")
        )

    try:

        min_quantity = int(
            query.get(
                "min_amount",
                50
            )
        )

        max_quantity = int(
            query.get(
                "max_amount",
                10000
            )
        )

    except Exception:

        min_quantity = 50
        max_quantity = 10000

    if (
        quantity < min_quantity
        or quantity > max_quantity
    ):

        flash(
            f"Stars {min_quantity}-{max_quantity} "
            "oralig'ida bo'lishi kerak.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    try:

        price_per_star = Decimal(
            str(query["price_per_star"])
        )

        total_usd = (
            price_per_star
            * quantity
        )

    except Exception:

        flash(
            "Stars narxi noto'g'ri.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    sell = price_usd_to_uzs(
        total_usd
    )

    user = me()

    if user["balance"] < sell:

        flash(
            f"Balans yetarli emas. "
            f"Kerak: {sell:,} so'm",
            "error"
        )

        return redirect(
            url_for("home")
        )

    payload = {
        "telegram_username": target,
        "quantity": quantity
    }

    result = fazer(
        "POST",
        "/telegram/stars/buy",
        json=payload,
        headers={
            "Idempotency-Key": str(
                uuid.uuid4()
            )
        }
    )

    if not result.get("ok"):

        flash(
            result.get(
                "error",
                "Stars buyurtmasi xatosi."
            ),
            "error"
        )

        return redirect(
            url_for("home")
        )

    provider_order = (
        result.get("order")
        or result.get("result")
        or {}
    )

    if not isinstance(
        provider_order,
        dict
    ):
        provider_order = {}

    provider_id = str(
        provider_order.get("id")
        or provider_order.get("order_id")
        or ""
    )

    status = provider_order.get(
        "status",
        result.get(
            "status",
            "processing"
        )
    )

    conn = db()

    try:

        conn.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE id = ?
            AND balance >= ?
            """,
            (
                sell,
                user["id"],
                sell
            )
        )

        add_tx(
            conn,
            user["id"],
            -sell,
            "purchase",
            f"Telegram Stars: {quantity}"
        )

        conn.execute(
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
                user["id"],
                "stars",
                provider_id,
                target,
                quantity,
                float(total_usd),
                sell,
                status,
                now()
            )
        )

        conn.commit()

        order_id = conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

    except Exception as e:

        conn.rollback()

        flash(
            f"Buyurtmani saqlashda xato: {e}",
            "error"
        )

        return redirect(
            url_for("home")
        )

    finally:
        conn.close()

    flash(
        "Stars buyurtmasi yuborildi.",
        "success"
    )

    return redirect(
        url_for(
            "order",
            order_id=order_id
        )
    )


# =========================================================
# BUY PREMIUM
# =========================================================

@app.route(
    "/buy/premium",
    methods=["POST"]
)
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
    except Exception:
        months = 0

    if (
        not target
        or months not in (3, 6, 12)
    ):

        flash(
            "Username yoki Premium muddati noto'g'ri.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    query = fazer(
        "GET",
        "/telegram/premium"
    )

    if not query.get("ok"):

        flash(
            query.get(
                "error",
                "Premium narxi olinmadi."
            ),
            "error"
        )

        return redirect(
            url_for("home")
        )

    plans = (
        query.get("plans")
        or query.get("result")
        or []
    )

    if not isinstance(
        plans,
        list
    ):
        plans = []

    selected_plan = None

    for plan in plans:

        try:

            if int(
                plan.get("months", 0)
            ) == months:

                selected_plan = plan
                break

        except Exception:
            continue

    if not selected_plan:

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
                selected_plan[
                    "price_usd"
                ]
            )
        )

    except Exception:

        flash(
            "Premium narxi noto'g'ri.",
            "error"
        )

        return redirect(
            url_for("home")
        )

    sell = price_usd_to_uzs(
        total_usd
    )

    user = me()

    if user["balance"] < sell:

        flash(
            f"Balans yetarli emas. "
            f"Kerak: {sell:,} so'm",
            "error"
        )

        return redirect(
            url_for("home")
        )

    result = fazer(
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

    if not result.get("ok"):

        flash(
            result.get(
                "error",
                "Premium buyurtmasi xatosi."
            ),
            "error"
        )

        return redirect(
            url_for("home")
        )

    provider_order = (
        result.get("order")
        or result.get("result")
        or {}
    )

    if not isinstance(
        provider_order,
        dict
    ):
        provider_order = {}

    provider_id = str(
        provider_order.get("id")
        or provider_order.get("order_id")
        or ""
    )

    status = provider_order.get(
        "status",
        result.get(
            "status",
            "processing"
        )
    )

    conn = db()

    try:

        conn.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE id = ?
            AND balance >= ?
            """,
            (
                sell,
                user["id"],
                sell
            )
        )

        add_tx(
            conn,
            user["id"],
            -sell,
            "purchase",
            f"Telegram Premium: {months} oy"
        )

        conn.execute(
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
                user["id"],
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

        conn.commit()

        order_id = conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

    except Exception as e:

        conn.rollback()

        flash(
            f"Buyurtmani saqlashda xato: {e}",
            "error"
        )

        return redirect(
            url_for("home")
        )

    finally:
        conn.close()

    flash(
        "Premium buyurtmasi yuborildi.",
        "success"
    )

    return redirect(
        url_for(
            "order",
            order_id=order_id
        )
    )


# =========================================================
# AKTIV SIM
# =========================================================

@app.route("/sim")
@user_required
def sim():

    result = aktiv(
        "getCountries"
    )

    countries = result.get(
        "result",
        []
    )

    if not isinstance(
        countries,
        list
    ):
        countries = []

    return render_template(
        "sim.html",
        countries=countries,
        error=result.get("error")
    )


@app.route(
    "/sim/buy/<country>",
    methods=["POST"]
)
@user_required
def sim_buy(country):

    country = country.upper()

    result = aktiv(
        "getCountries"
    )

    countries = result.get(
        "result",
        []
    )

    if not isinstance(
        countries,
        list
    ):
        countries = []

    item = next(
        (
            x for x in countries
            if str(
                x.get(
                    "country_code",
                    ""
                )
            ).upper() == country
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
        provider_price = int(
            item["price"]
        )
    except Exception:

        flash(
            "SIM narxi noto'g'ri.",
            "error"
        )

        return redirect(
            url_for("sim")
        )

    sell = (
        provider_price
        + int(MARKUP_UZS)
    )

    user = me()

    if user["balance"] < sell:

        flash(
            f"Balans yetarli emas. "
            f"Kerak: {sell:,} so'm",
            "error"
        )

        return redirect(
            url_for("sim")
        )

    buy_result = aktiv(
        "buyNumber",
        country_code=country
    )

    if not buy_result.get("ok"):

        flash(
            buy_result.get(
                "error",
                buy_result.get(
                    "msg",
                    "AktivSIM xatosi."
                )
            ),
            "error"
        )

        return redirect(
            url_for("sim")
        )

    data = buy_result.get(
        "result",
        {}
    )

    if not isinstance(
        data,
        dict
    ):
        data = {}

    provider_id = str(
        data.get(
            "order_id",
            ""
        )
    )

    phone = str(
        data.get(
            "phone",
            ""
        )
    )

    conn = db()

    try:

        conn.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE id = ?
            AND balance >= ?
            """,
            (
                sell,
                user["id"],
                sell
            )
        )

        add_tx(
            conn,
            user["id"],
            -sell,
            "purchase",
            f"SIM: {phone}"
        )

        conn.execute(
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
                user["id"],
                "sim",
                provider_id,
                phone,
                0,
                sell,
                "waiting",
                now()
            )
        )

        conn.commit()

        order_id = conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

    except Exception as e:

        conn.rollback()

        flash(
            f"Buyurtmani saqlashda xato: {e}",
            "error"
        )

        return redirect(
            url_for("sim")
        )

    finally:
        conn.close()

    return redirect(
        url_for(
            "order",
            order_id=order_id
        )
    )


# =========================================================
# TOP UP
# =========================================================

@app.route("/topup")
@user_required
def topup():

    return render_template(
        "topup.html"
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session.clear()

            session["admin"] = True

            session.permanent = True

            return redirect(
                url_for("admin")
            )

        flash(
            "Admin login yoki parol noto'g'ri.",
            "error"
        )

    return render_template(
        "admin_login.html"
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "admin",
        None
    )

    return redirect(
        url_for("admin_login")
    )


# =========================================================
# ADMIN
# =========================================================

@app.route("/admin")
@admin_required
def admin():

    conn = db()

    try:

        users = conn.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        orders_count = conn.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]

        sales = conn.execute(
            """
            SELECT COALESCE(
                SUM(-amount),
                0
            )
            FROM transactions
            WHERE type = 'purchase'
            """
        ).fetchone()[0]

        deposits = conn.execute(
            """
            SELECT COALESCE(
                SUM(amount),
                0
            )
            FROM transactions
            WHERE amount > 0
            """
        ).fetchone()[0]

        # Foydani xavfsiz hisoblash
        profit = conn.execute(
            """
            SELECT COALESCE(
                SUM(
                    sell_uzs
                    -
                    (api_usd * ?)
                ),
                0
            )
            FROM orders
            WHERE kind IN ('stars', 'premium')
            """,
            (
                float(USD_UZS),
            )
        ).fetchone()[0]

    except Exception as e:

        # Admin sahifasi API yoki DB sababli
        # yiqilib ketmasin
        users = 0
        orders_count = 0
        sales = 0
        deposits = 0
        profit = 0

        flash(
            f"Admin ma'lumotlarini olishda xato: {e}",
            "error"
        )

    finally:
        conn.close()

    # Fazer balansini olish
    fazer_balance = None
    fazer_error = None

    try:

        balance_result = fazer(
            "GET",
            "/balance"
        )

        fazer_balance = balance_result.get(
            "balance"
        )

        fazer_error = balance_result.get(
            "error"
        )

    except Exception as e:

        fazer_error = str(e)

    return render_template(
        "admin.html",
        users=users,
        orders_count=orders_count,
        sales=int(sales or 0),
        deposits=int(deposits or 0),
        profit=int(profit or 0),
        fazer_balance=fazer_balance,
        fazer_error=fazer_error
    )


# =========================================================
# ADMIN USERS
# =========================================================

@app.route("/admin/users")
@admin_required
def admin_users():

    conn = db()

    try:

        users = conn.execute(
            """
            SELECT *
            FROM users
            ORDER BY id DESC
            """
        ).fetchall()

    finally:
        conn.close()

    return render_template(
        "admin_users.html",
        users=users
    )


# =========================================================
# ADMIN BALANCE
# =========================================================

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

    except Exception:

        amount = 0

    note = request.form.get(
        "note",
        "Admin balans o'zgarishi"
    )

    conn = db()

    try:

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (uid,)
        ).fetchone()

        if not user:

            flash(
                "User topilmadi.",
                "error"
            )

            return redirect(
                url_for("admin_users")
            )

        new_balance = (
            user["balance"]
            + amount
        )

        if new_balance < 0:

            flash(
                "Balans manfiy bo'lishi mumkin emas.",
                "error"
            )

        elif amount == 0:

            flash(
                "Summa 0 bo'lmasin.",
                "error"
            )

        else:

            conn.execute(
                """
                UPDATE users
                SET balance = ?
                WHERE id = ?
                """,
                (
                    new_balance,
                    uid
                )
            )

            add_tx(
                conn,
                uid,
                amount,
                "admin",
                note
            )

            conn.commit()

            flash(
                "Balans muvaffaqiyatli yangilandi.",
                "success"
            )

    except Exception as e:

        conn.rollback()

        flash(
            f"Balans o'zgartirishda xato: {e}",
            "error"
        )

    finally:
        conn.close()

    return redirect(
        url_for("admin_users")
    )


# =========================================================
# HELP
# =========================================================

@app.route("/help")
def help_page():

    return render_template(
        "help.html"
    )


# =========================================================
# ROBOTS
# =========================================================

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


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return (
        "Sahifa topilmadi.",
        404
    )


@app.errorhandler(500)
def internal_error(error):

    # Hostingda 500 bo'lganda foydalanuvchiga
    # chiroyli xabar chiqadi.
    return (
        "Server xatosi. Iltimos keyinroq urinib ko'ring.",
        500
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    init_db()

    print("=" * 40)
    print("DONUZ SHOP ISHGA TUSHMOQDA")
    print("=" * 40)
    print("Database:", DB_PATH)
    print("Port:", PORT)
    print("Fazer API:", bool(FAZER_API_KEY))
    print("AktivSIM API:", bool(AKTIV_API_KEY))
    print("Admin:", ADMIN_USERNAME)
    print("=" * 40)

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
