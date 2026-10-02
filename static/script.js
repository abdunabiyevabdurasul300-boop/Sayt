let token = localStorage.getItem("donuz_token") || "";
let userId = localStorage.getItem("donuz_user_id") || "";
let catalog = [];
let selectedProduct = null;


async function api(url, options = {}) {
    options.headers = options.headers || {};

    options.headers["Content-Type"] = "application/json";

    if (token) {
        options.headers["Authorization"] = "Bearer " + token;
    }

    const response = await fetch(url, options);

    let data;

    try {
        data = await response.json();
    } catch {
        throw new Error("Server noto'g'ri javob qaytardi");
    }

    if (!response.ok || data.ok === false) {
        throw new Error(data.error || data.message || "Xatolik");
    }

    return data;
}


function showResult(id, text, type = "info") {
    const el = document.getElementById(id);

    if (!el) return;

    el.className = type;
    el.innerHTML = text;
}


function requestAuth() {

    const id = document.getElementById("userId").value.trim();

    if (!id) {
        showResult(
            "authResult",
            "❌ Telegram ID kiriting",
            "error"
        );
        return;
    }

    fetch("/api/auth/request", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            user_id: Number(id)
        })
    })
    .then(async r => {
        const data = await r.json();

        if (!r.ok || data.ok === false) {
            throw new Error(data.error || "Kod yuborilmadi");
        }

        userId = id;

        localStorage.setItem(
            "donuz_user_id",
            userId
        );

        document.getElementById("codeArea").style.display = "block";

        showResult(
            "authResult",
            "✅ Telegramingizga tasdiqlash kodi yuborildi.",
            "success"
        );
    })
    .catch(err => {
        showResult(
            "authResult",
            "❌ " + err.message,
            "error"
        );
    });
}


async function verifyAuth() {

    const code = document
        .getElementById("authCode")
        .value
        .trim();

    if (!code) {
        showResult(
            "authResult",
            "❌ Kodni kiriting",
            "error"
        );
        return;
    }

    try {

        const data = await api(
            "/api/auth/verify",
            {
                method: "POST",
                body: JSON.stringify({
                    user_id: Number(userId),
                    code: code
                })
            }
        );

        token = data.token || data.session_token;

        if (!token) {
            throw new Error(
                "Server token qaytarmadi"
            );
        }

        localStorage.setItem(
            "donuz_token",
            token
        );

        document.getElementById(
            "authSection"
        ).style.display = "none";

        document.getElementById(
            "userSection"
        ).style.display = "block";

        showResult(
            "authResult",
            "✅ Muvaffaqiyatli kirildi.",
            "success"
        );

        await loadMe();
        await loadCatalog();

    } catch (err) {

        showResult(
            "authResult",
            "❌ " + err.message,
            "error"
        );
    }
}


async function loadMe() {

    try {

        const data = await api("/api/me");

        const me = data.me || data.user || data;

        if (
            me &&
            me.balance !== undefined
        ) {
            document.getElementById(
                "balanceBox"
            ).textContent =
                "Balans: " +
                Number(me.balance).toLocaleString("uz-UZ") +
                " so'm";
        }

    } catch (err) {

        console.log(
            "ME:",
            err.message
        );
    }
}


async function loadCatalog() {

    try {

        const data = await api(
            "/api/catalog"
        );

        catalog =
            data.games ||
            data.catalog ||
            data.data ||
            [];

        const select =
            document.getElementById(
                "gameSelect"
            );

        select.innerHTML =
            '<option value="">O\'yinni tanlang</option>';

        catalog.forEach(game => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                game.id ||
                game.game_id;

            option.textContent =
                game.name ||
                game.title ||
                ("Game " + option.value);

            select.appendChild(option);
        });

    } catch (err) {

        showResult(
            "products",
            "❌ Katalog yuklanmadi: " +
            err.message,
            "error"
        );
    }
}


function getProducts(game) {

    return (
        game.products ||
        game.packages ||
        game.items ||
        []
    );
}


function loadProducts() {

    const gameId =
        document.getElementById(
            "gameSelect"
        ).value;

    const card =
        document.getElementById(
            "productsCard"
        );

    const products =
        document.getElementById(
            "products"
        );

    document.getElementById(
        "orderCard"
    ).style.display = "none";

    products.innerHTML = "";

    if (!gameId) {

        card.style.display = "none";

        return;
    }

    const game =
        catalog.find(g =>
            String(
                g.id ||
                g.game_id
            ) === String(gameId)
        );

    if (!game) return;

    const list =
        getProducts(game);

    if (!list.length) {

        products.innerHTML =
            '<div class="error">Bu o\'yinda paket topilmadi.</div>';

        card.style.display = "block";

        return;
    }

    list.forEach(product => {

        const id =
            product.id ||
            product.product_id;

        const name =
            product.name ||
            product.title ||
            product.package_name ||
            "Paket";

        const price =
            product.price ??
            product.sale_price ??
            product.amount ??
            0;

        const div =
            document.createElement(
                "div"
            );

        div.className = "product";

        div.innerHTML = `
            <div class="product-title">
                ${escapeHtml(name)}
            </div>

            <div class="product-price">
                💰 ${Number(price).toLocaleString("uz-UZ")} so'm
            </div>

            <button onclick="selectProduct('${String(id).replace(/'/g, "\\'")}')">
                🛒 Tanlash
            </button>
        `;

        products.appendChild(div);
    });

    card.style.display = "block";
}


function selectProduct(productId) {

    const gameId =
        document.getElementById(
            "gameSelect"
        ).value;

    const game =
        catalog.find(g =>
            String(
                g.id ||
                g.game_id
            ) === String(gameId)
        );

    if (!game) return;

    const products =
        getProducts(game);

    selectedProduct =
        products.find(p =>
            String(
                p.id ||
                p.product_id
            ) === String(productId)
        );

    if (!selectedProduct) {
        alert("Paket topilmadi");
        return;
    }

    document.getElementById(
        "orderCard"
    ).style.display = "block";

    document.getElementById(
        "playerId"
    ).value = "";

    document.getElementById(
        "serverId"
    ).value = "";

    document.getElementById(
        "playerResult"
    ).innerHTML = "";

    document.getElementById(
        "buyButton"
    ).style.display = "none";

    document.getElementById(
        "orderCard"
    ).scrollIntoView({
        behavior: "smooth"
    });
}


async function checkPlayer() {

    if (!selectedProduct) {

        showResult(
            "playerResult",
            "❌ Avval paket tanlang.",
            "error"
        );

        return;
    }

    const gameId =
        document.getElementById(
            "gameSelect"
        ).value;

    const playerId =
        document.getElementById(
            "playerId"
        ).value.trim();

    const serverId =
        document.getElementById(
            "serverId"
        ).value.trim();

    if (!playerId) {

        showResult(
            "playerResult",
            "❌ Player ID kiriting.",
            "error"
        );

        return;
    }

    try {

        showResult(
            "playerResult",
            "⏳ ID tekshirilmoqda...",
            "info"
        );

        const data =
            await api(
                "/api/check-id",
                {
                    method: "POST",
                    body: JSON.stringify({
                        game_id: Number(gameId),
                        player_id: playerId,
                        server_id: serverId
                    })
                }
            );

        const name =
            data.player_name ||
            data.nickname ||
            data.name ||
            data.username ||
            data.data?.player_name ||
            data.data?.nickname ||
            "Tasdiqlandi";

        showResult(
            "playerResult",
            "✅ Nickname: <b>" +
            escapeHtml(String(name)) +
            "</b>",
            "success"
        );

        document.getElementById(
            "buyButton"
        ).style.display = "block";

    } catch (err) {

        document.getElementById(
            "buyButton"
        ).style.display = "none";

        showResult(
            "playerResult",
            "❌ " + err.message,
            "error"
        );
    }
}


async function createOrder() {

    if (!selectedProduct) return;

    const gameId =
        document.getElementById(
            "gameSelect"
        ).value;

    const playerId =
        document.getElementById(
            "playerId"
        ).value.trim();

    const serverId =
        document.getElementById(
            "serverId"
        ).value.trim();

    const productId =
        selectedProduct.id ||
        selectedProduct.product_id;

    if (!playerId) {
        alert("Player ID kiriting");
        return;
    }

    if (
        !confirm(
            "Buyurtmani tasdiqlaysizmi?"
        )
    ) {
        return;
    }

    try {

        const data =
            await api(
                "/api/order",
                {
                    method: "POST",
                    body: JSON.stringify({
                        game_id: Number(gameId),
                        product_id: Number(productId),
                        player_id: playerId,
                        server_id: serverId
                    })
                }
            );

        showResult(
            "playerResult",
            "✅ Buyurtma qabul qilindi!",
            "success"
        );

        await loadMe();

        document.getElementById(
            "buyButton"
        ).style.display = "none";

    } catch (err) {

        showResult(
            "playerResult",
            "❌ " + err.message,
            "error"
        );
    }
}


function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


async function autoLogin() {

    if (!token || !userId) {
        return;
    }

    try {

        await loadMe();

        document.getElementById(
            "authSection"
        ).style.display = "none";

        document.getElementById(
            "userSection"
        ).style.display = "block";

        await loadCatalog();

    } catch {

        localStorage.removeItem(
            "donuz_token"
        );

        localStorage.removeItem(
            "donuz_user_id"
        );

        token = "";
        userId = "";
    }
}


autoLogin();
