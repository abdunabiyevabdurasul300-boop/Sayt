const API = window.location.origin;
let catalog = [];
let selected = null;
let sessionToken = localStorage.getItem("game_donat_session") || "";

const icons = {
  "PUBG Mobile":"🔫",
  "Free Fire":"🔥",
  "Grand Mobile":"🚗",
  "Telegram Premium":"⭐",
  "Mobile Legends":"⚔️"
};

function money(v){return Number(v||0).toLocaleString("uz-UZ")+" so'm";}
function showNotice(msg){const n=document.getElementById("notice");n.textContent=msg;n.classList.remove("hidden");setTimeout(()=>n.classList.add("hidden"),4500)}

async function api(path, options={}){
  const headers={"Content-Type":"application/json",...(options.headers||{})};
  if(sessionToken) headers.Authorization="Bearer "+sessionToken;
  const r=await fetch(API+path,{...options,headers});
  let d={};
  try{d=await r.json()}catch{}
  if(!r.ok && !d.error)d.error="Server xatosi";
  return d;
}

async function loadCatalog(){
  const d=await api("/api/catalog");
  if(!d.ok){document.getElementById("games").innerHTML=`<div class="loading">❌ Katalogni yuklab bo‘lmadi.</div>`;return}
  catalog=d.games||[];
  renderGames();
  refreshMe();
}

function renderGames(){
  const box=document.getElementById("games");
  if(!catalog.length){box.innerHTML='<div class="loading">O‘yinlar topilmadi.</div>';return}
  box.innerHTML=catalog.map((g,i)=>`
    <div class="game-card">
      <div class="game-icon">${icons[g.name]||"🎮"}</div>
      <h3>${esc(g.name)}</h3>
      <p>${g.manual?"Manual buyurtma":"API orqali donat"}</p>
      <div class="packages">
        ${(g.packages||[]).map((p)=>`
          <div class="package">
            <h3>${esc(p.name)}</h3>
            <div class="price">${money(p.price)}</div>
            <button onclick="openOrder(${i},${p.paket_id})">🛒 Xarid qilish</button>
          </div>`).join("")}
      </div>
    </div>`).join("");
}

function openOrder(gameIndex,paketId){
  const g=catalog[gameIndex], p=(g.packages||[]).find(x=>x.paket_id===paketId);
  if(!p)return;
  selected={game:g,package:p};
  document.getElementById("orderTitle").textContent="🛒 "+g.name;
  document.getElementById("orderPackage").textContent=`${p.name} — ${money(p.price)}`;
  document.getElementById("playerId").placeholder=g.id_label||"Player ID";
  document.getElementById("playerId").value="";
  document.getElementById("serverId").value="";
  document.getElementById("serverId").classList.toggle("hidden",!g.requires_server);
  document.getElementById("checkResult").textContent="";
  document.getElementById("orderBtn").classList.add("hidden");
  document.getElementById("orderModal").classList.remove("hidden");
}
function closeOrder(){document.getElementById("orderModal").classList.add("hidden")}
function openLogin(){document.getElementById("loginModal").classList.remove("hidden")}
function closeLogin(){document.getElementById("loginModal").classList.add("hidden")}

async function checkId(){
  if(!selected)return;
  const playerId=document.getElementById("playerId").value.trim();
  const serverId=document.getElementById("serverId").value.trim();
  if(!playerId){showNotice("❌ ID kiriting.");return}
  const box=document.getElementById("checkResult");
  box.textContent="⏳ Tekshirilmoqda...";
  const d=await api("/api/check-id",{method:"POST",body:JSON.stringify({
    game_id:selected.game.game_id,player_id:playerId,server_id:serverId
  })});
  if(d.ok){
    const name=d.player_name||d.nickname||d.charname||"ID tasdiqlandi";
    box.textContent="✅ "+name;
    document.getElementById("orderBtn").classList.remove("hidden");
  }else{
    box.textContent="❌ "+(d.error||"ID tekshirilmadi.");
    document.getElementById("orderBtn").classList.add("hidden");
  }
}

async function createOrder(){
  if(!sessionToken){openLogin();showNotice("🔐 Buyurtma berish uchun avval Telegram orqali kiring.");return}
  const playerId=document.getElementById("playerId").value.trim();
  const serverId=document.getElementById("serverId").value.trim();
  const d=await api("/api/order",{method:"POST",body:JSON.stringify({
    game_id:selected.game.game_id,
    paket_id:selected.package.paket_id,
    player_id:playerId,
    server_id:serverId
  })});
  if(d.ok){
    closeOrder();showNotice("✅ "+(d.message||"Buyurtma qabul qilindi."));
    refreshMe();
  }else{
    if(d.error&&d.error.includes("Avval Telegram"))openLogin();
    showNotice("❌ "+(d.error||"Buyurtma bajarilmadi."));
  }
}

async function requestCode(){
  const id=document.getElementById("telegramId").value.trim();
  if(!id){document.getElementById("loginStatus").textContent="Telegram ID kiriting.";return}
  const d=await api("/api/auth/request",{method:"POST",body:JSON.stringify({telegram_id:id})});
  document.getElementById("loginStatus").textContent=d.ok?"📨 Kod Telegram botga yuborildi.":"❌ "+(d.error||d.message);
  if(d.ok){
    document.getElementById("authCode").classList.remove("hidden");
    document.getElementById("verifyBtn").classList.remove("hidden");
  }
}

async function verifyCode(){
  const id=document.getElementById("telegramId").value.trim();
  const code=document.getElementById("authCode").value.trim();
  const d=await api("/api/auth/verify",{method:"POST",body:JSON.stringify({telegram_id:id,code})});
  if(!d.ok){document.getElementById("loginStatus").textContent="❌ "+(d.error||"Kod xato.");return}
  sessionToken=d.token;localStorage.setItem("game_donat_session",sessionToken);
  closeLogin();showNotice("✅ Saytga muvaffaqiyatli kirdingiz.");refreshMe();
}

async function refreshMe(){
  if(!sessionToken)return;
  const d=await api("/api/me");
  if(!d.ok){sessionToken="";localStorage.removeItem("game_donat_session");return}
  const box=document.getElementById("accountBox");
  box.textContent=`👤 Telegram ID: ${d.user_id}  •  💳 Balans: ${money(d.balance)}`;
  box.classList.remove("hidden");
  document.getElementById("loginBtn").textContent="👤 Akkount";
}

function esc(s){
  return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
}

loadCatalog();
