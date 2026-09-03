from flask import Flask, jsonify, render_template_string, request, session
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "novalex-local-admin-key"

PRODUCTS = [
    {"id":1,"name":"NovaLex Classic Tee","price":799,"category":"T-Shirts","image":"/static/images/tshirt.jpg","icon":"👕"},
    {"id":2,"name":"NovaLex Oversized Tee","price":999,"category":"T-Shirts","image":"/static/images/tshirt.jpg","icon":"👕"},
    {"id":3,"name":"NovaLex Premium Hoodie","price":1499,"category":"Hoodies","image":"/static/images/hoodie.jpg","icon":"🧥"},
    {"id":4,"name":"NovaLex Street Cap","price":499,"category":"Caps","image":"/static/images/cap.jpg","icon":"🧢"},
]

ORDERS = []

class DBWrapper:
    def __init__(self, con, postgres=False):
        self.con = con
        self.postgres = postgres

    def execute(self, query, params=()):
        if self.postgres:
            query = query.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
            query = query.replace("?", "%s")
        return self.con.cursor().execute(query, params)

    def commit(self):
        self.con.commit()

    def close(self):
        self.con.close()


def db():
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        import psycopg2
        from psycopg2.extras import DictCursor

        con = psycopg2.connect(database_url)
        return DBWrapper(con, postgres=True)

    con = sqlite3.connect("novalex.db")
    con.row_factory = sqlite3.Row
    return DBWrapper(con)


def init_db():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            address TEXT,
            payment TEXT,
            items TEXT,
            total INTEGER,
            status TEXT DEFAULT 'Pending'
        )
    """)

    try:
        con.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'Pending'")
    except sqlite3.OperationalError:
        pass

    con.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price INTEGER,
            category TEXT,
            image TEXT,
            icon TEXT
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            product_id INTEGER
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT UNIQUE,
            address TEXT
        )
    """)

    count = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    if count == 0:
        for product in PRODUCTS:
            con.execute("""
                INSERT INTO products(name,price,category,image,icon)
                VALUES(?,?,?,?,?)
            """, (
                product["name"],
                product["price"],
                product["category"],
                product["image"],
                product["icon"]
            ))

    con.commit()
    con.close()

init_db()

def load_products():
    con = db()
    rows = con.execute("SELECT * FROM products ORDER BY id").fetchall()
    con.close()

    return [dict(row) for row in rows]

PRODUCTS = load_products()

PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>NOVALEX - Wear Your Identity</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;background:#f5f5f5;color:#111}
header{background:#111;color:#fff;padding:16px 5%;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
.logo{font-size:26px;font-weight:900;letter-spacing:2px}
.cartBtn{background:#fff;color:#111;border:0;padding:11px 16px;border-radius:25px;font-weight:bold;cursor:pointer}
.hero{background:#111;color:#fff;text-align:center;padding:65px 20px}
.hero h1{font-size:48px;margin:0 0 12px}
.hero p{font-size:18px;color:#ccc}
.shop{padding:35px 5%;max-width:1200px;margin:auto}
.categoryBar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}
.categoryBtn{padding:11px 20px;border:1px solid #ddd;background:#fff;color:#111;border-radius:25px;font-weight:bold;cursor:pointer}
.categoryBtn:hover{background:#111;color:#fff}
.search{width:100%;padding:15px;border:1px solid #ddd;border-radius:12px;font-size:16px;margin-bottom:28px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}
.card{background:#fff;border-radius:20px;padding:15px;text-align:center;box-shadow:0 5px 20px #00000012;transition:.25s;overflow:hidden;cursor:pointer}
.card:hover{transform:translateY(-6px);box-shadow:0 12px 30px #00000020}
.pic{height:210px;background:#eee;border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:80px;overflow:hidden}
.pic img{width:100%;height:100%;object-fit:cover}
.card h3{margin:16px 0 8px}
.price{font-size:21px;font-weight:800;margin:10px}
.add,.buy,.checkout{width:100%;padding:13px;border-radius:12px;font-weight:bold;cursor:pointer}
.add,.checkout{background:#111;color:#fff;border:0}
.buy{margin-top:9px;background:#fff;color:#111;border:2px solid #111}
.buy:hover{background:#111;color:#fff}
#cart,#details,#checkoutBox{display:none;position:fixed;z-index:30}
#cart{right:0;top:0;width:350px;max-width:90%;height:100%;background:#fff;padding:25px;box-shadow:-5px 0 25px #0004;overflow:auto}
.cartHead{display:flex;justify-content:space-between;align-items:center}
.close{border:0;background:#eee;border-radius:50%;width:35px;height:35px}
.item{border-bottom:1px solid #ddd;padding:15px 0}
.qty button{padding:7px 11px;margin:4px;border:1px solid #ddd;background:#fff;border-radius:8px;font-weight:bold;cursor:pointer}
.modal{inset:0;background:#0008;align-items:center;justify-content:center;padding:20px}
.modalBox{background:#fff;border-radius:20px;padding:25px;max-width:480px;width:100%;max-height:90vh;overflow:auto;text-align:center;position:relative}
.modalImg{width:100%;height:280px;object-fit:cover;border-radius:15px}
.sizeBtn{padding:9px 15px;border:1px solid #ddd;background:#fff;border-radius:8px;font-weight:bold;cursor:pointer}
.sizeBtn.selected{background:#111;color:#fff}
.formInput{width:100%;padding:13px;margin:7px 0;border:1px solid #ddd;border-radius:10px}
@media(max-width:800px){.grid{grid-template-columns:repeat(2,1fr)}.hero h1{font-size:36px}}
@media(max-width:500px){.grid{grid-template-columns:1fr}.hero{padding:45px 15px}.hero h1{font-size:32px}}


/* NOVALEX PREMIUM ANIMATIONS */
@keyframes novaFadeUp{
    from{opacity:0;transform:translateY(25px)}
    to{opacity:1;transform:translateY(0)}
}

@keyframes novaFadeIn{
    from{opacity:0}
    to{opacity:1}
}

@keyframes novaGlow{
    0%,100%{box-shadow:0 0 0 rgba(255,255,255,0)}
    50%{box-shadow:0 0 25px rgba(255,255,255,.12)}
}

header{
    animation:novaFadeIn .7s ease both;
}

.hero{
    animation:novaFadeUp .8s ease both;
}

.product{
    animation:novaFadeUp .7s ease both;
    transition:transform .25s ease,box-shadow .25s ease;
}

.product:hover{
    transform:translateY(-8px) scale(1.02);
    box-shadow:0 15px 35px rgba(0,0,0,.35);
}

.product img{
    transition:transform .35s ease;
}

.product:hover img{
    transform:scale(1.06);
}

button{
    transition:transform .18s ease,opacity .18s ease;
}

button:active{
    transform:scale(.95);
}

.cartBtn{
    animation:novaGlow 2.5s ease-in-out infinite;
}


/* NOVALEX ORDER SUCCESS */
.novaSuccess{
    position:fixed;
    inset:0;
    background:rgba(0,0,0,.78);
    display:none;
    align-items:center;
    justify-content:center;
    z-index:9999;
    animation:novaFadeIn .25s ease;
}

.novaSuccessBox{
    width:min(90%,380px);
    background:#1d1d1d;
    border:1px solid #444;
    border-radius:24px;
    padding:30px 22px;
    text-align:center;
    box-shadow:0 20px 60px rgba(0,0,0,.5);
    animation:novaSuccessPop .45s cubic-bezier(.2,.8,.2,1);
}

.novaCheck{
    width:78px;
    height:78px;
    margin:0 auto 18px;
    border-radius:50%;
    background:#25d366;
    color:white;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:42px;
    font-weight:bold;
    animation:novaCheckPop .55s ease;
}

@keyframes novaSuccessPop{
    from{opacity:0;transform:scale(.75) translateY(20px)}
    to{opacity:1;transform:scale(1) translateY(0)}
}

@keyframes novaCheckPop{
    0%{transform:scale(0)}
    70%{transform:scale(1.15)}
    100%{transform:scale(1)}
}


/* NOVALEX LOADING ANIMATION */
.novaLoader{
    position:fixed;
    inset:0;
    background:rgba(0,0,0,.82);
    display:none;
    align-items:center;
    justify-content:center;
    flex-direction:column;
    z-index:10000;
}

.novaSpinner{
    width:48px;
    height:48px;
    border:4px solid #444;
    border-top-color:#fff;
    border-radius:50%;
    animation:novaSpin .8s linear infinite;
}

.novaLoaderText{
    margin-top:15px;
    font-weight:bold;
    letter-spacing:.5px;
}

@keyframes novaSpin{
    to{transform:rotate(360deg)}
}


.wish{
    width:100%;
    margin-top:8px;
    padding:10px;
    border:1px solid #444;
    border-radius:10px;
    background:#181818;
    color:white;
    font-weight:bold;
    cursor:pointer;
    transition:.2s;
}

.wish:hover{
    background:#2a2a2a;
    transform:scale(1.02);
}

.wish:active{
    transform:scale(.96);
}

/* NOVALEX WISHLIST ANIMATION */
.wish{
    position:relative;
    overflow:hidden;
}
.wish:active{
    transform:scale(.9);
}
.wish{
    transition:transform .2s ease, background .2s ease, box-shadow .2s ease;
}

/* NOVALEX PREMIUM RESPONSIVE */
*{
    box-sizing:border-box;
}

html,body{
    width:100%;
    max-width:100%;
    overflow-x:hidden;
}

header{
    flex-wrap:wrap !important;
    gap:12px !important;
}

header > div:last-child{
    display:flex !important;
    flex-wrap:wrap !important;
    justify-content:flex-end;
    gap:8px !important;
    max-width:100%;
}

header a,
header button{
    white-space:nowrap;
}

@media(max-width:700px){
    body{
        padding:12px !important;
    }

    header{
        padding:12px !important;
        border-radius:18px;
        justify-content:center;
    }

    header .logo{
        width:100%;
        text-align:center;
        font-size:26px;
    }

    header > div:last-child{
        width:100%;
        justify-content:center;
    }

    header a,
    header button{
        flex:1 1 calc(50% - 8px);
        min-width:135px;
        text-align:center;
        font-size:13px !important;
        padding:10px 8px !important;
    }

    .hero{
        padding:28px 18px !important;
        border-radius:20px;
    }

    .grid{
        grid-template-columns:repeat(2,minmax(0,1fr)) !important;
        gap:10px !important;
    }

    .card{
        min-width:0 !important;
        padding:10px !important;
    }

    .card h3{
        font-size:14px !important;
        line-height:1.3;
    }

    .price{
        font-size:17px !important;
    }

    .add,.buy,.wish{
        font-size:11px !important;
        padding:9px 5px !important;
    }

    .statsGrid{
        grid-template-columns:1fr !important;
    }

    .adminWrap{
        width:100% !important;
    }

    .adminTitle{
        font-size:25px !important;
    }
}

@media(max-width:380px){
    .grid{
        grid-template-columns:1fr !important;
    }

    header a,
    header button{
        flex:1 1 100%;
        min-width:0;
    }
}

/* NOVALEX PREMIUM UI */
body{
    background:
        radial-gradient(circle at 10% 0%,rgba(255,255,255,.07),transparent 30%),
        radial-gradient(circle at 90% 20%,rgba(255,255,255,.05),transparent 30%),
        #0b0b0b !important;
}

.card{
    background:linear-gradient(145deg,#202020,#121212) !important;
    border:1px solid rgba(255,255,255,.08) !important;
    border-radius:20px !important;
    box-shadow:0 10px 30px rgba(0,0,0,.3) !important;
    transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease !important;
}

.card:hover{
    transform:translateY(-6px) !important;
    box-shadow:0 18px 40px rgba(0,0,0,.5) !important;
    border-color:rgba(255,255,255,.2) !important;
}

.hero{
    background:linear-gradient(135deg,#242424,#101010) !important;
    border:1px solid rgba(255,255,255,.08);
    box-shadow:0 15px 40px rgba(0,0,0,.35);
}

.statCard{
    transition:transform .25s ease,box-shadow .25s ease;
}

.statCard:hover{
    transform:translateY(-5px);
    box-shadow:0 15px 35px rgba(0,0,0,.45);
}

button,a{
    transition:transform .18s ease,opacity .18s ease,box-shadow .18s ease;
}

button:hover,a:hover{
    opacity:.92;
}

button:active,a:active{
    transform:scale(.96);
}

/* NOVALEX LOGO GLOW */
.logo{
    letter-spacing:2px;
    font-weight:900;
    text-shadow:0 0 8px rgba(255,255,255,.15);
    animation:novaLogoGlow 2.5s ease-in-out infinite;
}

@keyframes novaLogoGlow{
    0%,100%{text-shadow:0 0 8px rgba(255,255,255,.12)}
    50%{text-shadow:0 0 22px rgba(255,255,255,.4)}
}

/* PREMIUM HERO TEXT */
.hero h1{
    animation:novaFadeUp .8s ease both;
}

.hero p{
    animation:novaFadeUp 1s ease both;
}

/* PREMIUM ADMIN DASHBOARD */
.adminWrap{
    animation:novaFadeUp .7s ease both;
}

.adminTitle{
    letter-spacing:1px;
    text-shadow:0 0 18px rgba(255,255,255,.12);
}

.adminSub{
    font-size:14px;
}

.statsGrid{
    gap:14px !important;
}

.statCard{
    position:relative;
    overflow:hidden;
    background:linear-gradient(145deg,#262626,#111) !important;
    border:1px solid rgba(255,255,255,.08) !important;
}

.statCard::after{
    content:"";
    position:absolute;
    width:100px;
    height:100px;
    right:-35px;
    top:-35px;
    border-radius:50%;
    background:rgba(255,255,255,.04);
}

.statIcon{
    position:relative;
    z-index:1;
}

.statValue{
    position:relative;
    z-index:1;
    letter-spacing:.5px;
}

@media(max-width:700px){
    .statsGrid{
        grid-template-columns:repeat(3,minmax(0,1fr)) !important;
        gap:8px !important;
    }

    .statCard{
        padding:13px 8px !important;
        border-radius:15px !important;
    }

    .statIcon{
        font-size:23px !important;
    }

    .statLabel{
        font-size:10px !important;
    }

    .statValue{
        font-size:21px !important;
    }
}

@media(max-width:420px){
    .statsGrid{
        grid-template-columns:1fr !important;
    }

    .statCard{
        padding:16px !important;
    }
}
</style>
</style>
</head>
<body>
<div id="novaLoader" class="novaLoader">
    <div class="novaSpinner"></div>
    <div class="novaLoaderText">NOVALEX Loading...</div>
</div>


<div id="novaSuccess" class="novaSuccess">
<div class="novaSuccessBox">
<div class="novaCheck">✓</div>
<h2>Order Placed! 🎉</h2>
<p id="novaOrderText">Your order has been placed successfully.</p>
<button onclick="closeNovaSuccess()" style="padding:12px 22px;border:0;border-radius:12px;font-weight:bold;cursor:pointer">
CONTINUE
</button>
</div>
</div>



<header>
<div class="logo">NOVALEX</div>
<div style="display:flex;gap:8px;align-items:center">
<a href="/my-orders" style="background:#fff;color:#111;padding:11px 14px;border-radius:25px;font-weight:bold;text-decoration:none">📦 My Orders</a>
<a href="/profile" style="background:#fff;color:#111;padding:11px 14px;border-radius:25px;font-weight:bold;text-decoration:none">👤 Profile</a>
<a href="/wishlist" style="background:#fff;color:#111;padding:11px 14px;border-radius:25px;font-weight:bold;text-decoration:none">❤️ Wishlist</a>
<a href="/track" style="background:#fff;color:#111;padding:11px 14px;border-radius:25px;font-weight:bold;text-decoration:none">📦 Track Order</a>
<button class="cartBtn" onclick="openCart()">🛒 Cart (<span id="count">0</span>)</button>
</div>
</header>

<section class="hero">
<h1>Wear Your Identity.</h1>
<p>Premium fashion by NOVALEX.</p>
</section>

<main class="shop">
<h2>Featured Collection</h2>

<div class="categoryBar">
<button class="categoryBtn" onclick="setCategory('All')">ALL</button>
<button class="categoryBtn" onclick="setCategory('T-Shirts')">T-SHIRTS</button>
<button class="categoryBtn" onclick="setCategory('Hoodies')">HOODIES</button>
<button class="categoryBtn" onclick="setCategory('Caps')">CAPS</button>
</div>

<input class="search" id="search" placeholder="🔎 Search products..." oninput="showProducts()">
<div class="grid" id="products"></div>
</main>

<div id="cart">
<div class="cartHead">
<h2>Your Cart</h2>
<button class="close" onclick="closeCart()">✕</button>
</div>
<div id="cartItems"></div>
<h2>Total: ₹<span id="total">0</span></h2>
<button class="checkout" onclick="openCheckout()">CHECKOUT</button>
</div>

<div id="details" class="modal">
<div class="modalBox">
<button class="close" onclick="closeDetails()" style="position:absolute;right:15px;top:15px">✕</button>
<img id="detailImg" class="modalImg">
<h2 id="detailName"></h2>
<h3>₹<span id="detailPrice"></span></h3>
<div>
<b>Select Size</b>
<div style="display:flex;gap:8px;justify-content:center;margin:10px">
<button class="sizeBtn" onclick="selectSize(this)">S</button>
<button class="sizeBtn" onclick="selectSize(this)">M</button>
<button class="sizeBtn" onclick="selectSize(this)">L</button>
<button class="sizeBtn" onclick="selectSize(this)">XL</button>
</div>
</div>
<button id="detailAdd" class="add">ADD TO CART</button>
</div>
</div>

<div id="checkoutBox" class="modal">
<div class="modalBox">
<button class="close" onclick="closeCheckout()" style="position:absolute;right:15px;top:15px">✕</button>
<h2>Checkout</h2>
<input id="customerName" class="formInput" placeholder="Full Name">
<input id="customerPhone" class="formInput" placeholder="Mobile Number" type="tel">
<textarea id="customerAddress" class="formInput" placeholder="Delivery Address" style="height:100px"></textarea>
<select id="payment" class="formInput">
<option value="COD">Cash on Delivery</option>
<option value="ONLINE">Online Payment</option>
</select>
<button onclick="placeOrder()" class="checkout">PLACE ORDER</button>
</div>
</div>

<script>
const products={{products|tojson}};
let cart=JSON.parse(localStorage.getItem("novalex_cart")||"[]");
let category="All";

function save(){
 localStorage.setItem("novalex_cart",JSON.stringify(cart));
 updateCount();
}

function updateCount(){
 document.getElementById("count").innerText=cart.reduce((a,b)=>a+b.qty,0);
}

function setCategory(c){
 category=c;
 showProducts();
}

function showProducts(){
 const q=document.getElementById("search").value.toLowerCase();
 const box=document.getElementById("products");
 box.innerHTML="";
 products.filter(p=>(category==="All"||p.category===category)&&p.name.toLowerCase().includes(q)).forEach(p=>{
  box.innerHTML+=`
  <div class="card" onclick="showDetails(${p.id})">
   <div class="pic"><img src="${p.image}" onerror="this.style.display='none';this.parentElement.innerHTML=p.icon"></div>
   <h3>${p.name}</h3>
   <div class="price">₹${p.price}</div>
   <button class="add" onclick="event.stopPropagation();add(${p.id})">ADD TO CART</button>
   <button class="buy" onclick="event.stopPropagation();buyNow(${p.id})">BUY NOW</button>
   <button class="wish" id="wish-${p.id}" onclick="event.stopPropagation();toggleWishlist(${p.id})">♡ WISHLIST</button>
  </div>`;
 });
}

function add(id){
 const p=products.find(x=>x.id===id);
 if(!p)return;
 const x=cart.find(x=>x.id===id);
 if(x)x.qty++;
 else cart.push({...p,qty:1});
 save();
 alert("Added to cart!");
}

function buyNow(id){
 add(id);
 openCart();
}

function openCart(){
 document.getElementById("cart").style.display="block";
 renderCart();
}

function closeCart(){
 document.getElementById("cart").style.display="none";
}

function renderCart(){
 const box=document.getElementById("cartItems");
 box.innerHTML="";
 let total=0;
 cart.forEach((x,i)=>{
  total+=x.price*x.qty;
  box.innerHTML+=`
  <div class="item">
   <b>${x.name}</b>
   <p>₹${x.price}</p>
   <div class="qty">
    <button onclick="changeQty(${i},-1)">−</button>
    ${x.qty}
    <button onclick="changeQty(${i},1)">+</button>
    <button onclick="removeItem(${i})">REMOVE</button>
   </div>
  </div>`;
 });
 document.getElementById("total").innerText=total;
 updateCount();
}

function changeQty(i,d){
 cart[i].qty+=d;
 if(cart[i].qty<=0)cart.splice(i,1);
 save();
 renderCart();
}

function removeItem(i){
 cart.splice(i,1);
 save();
 renderCart();
}

function showDetails(id){
 showNovaLoader();
 const p=products.find(x=>x.id===id);
 document.getElementById("detailImg").src=p.image;
 document.getElementById("detailName").innerText=p.name;
 document.getElementById("detailPrice").innerText=p.price;
 document.getElementById("detailAdd").onclick=function(){add(p.id);closeDetails();};
 document.getElementById("details").style.display="flex";
}

function closeDetails(){
 document.getElementById("details").style.display="none";
}

function selectSize(btn){
 document.querySelectorAll(".sizeBtn").forEach(b=>b.classList.remove("selected"));
 btn.classList.add("selected");
}

function openCheckout(){
 if(cart.length===0){alert("Your cart is empty!");return;}
 document.getElementById("checkoutBox").style.display="flex";
}

function closeCheckout(){
 document.getElementById("checkoutBox").style.display="none";
}

function showNovaSuccess(orderId){
    document.getElementById("novaOrderText").innerText =
        "Order #"+orderId+" placed successfully!";
    document.getElementById("novaSuccess").style.display="flex";
}

function closeNovaSuccess(){
    document.getElementById("novaSuccess").style.display="none";
}

function showNovaLoader(){
    const loader=document.getElementById("novaLoader");
    if(loader) loader.style.display="flex";
}

function hideNovaLoader(){
    const loader=document.getElementById("novaLoader");
    if(loader) loader.style.display="none";
}



function toggleWishlist(productId){
    let phone=localStorage.getItem("novaPhone") || prompt("Wishlist ke liye mobile number enter karo:");
    if(!phone) return;

    phone=phone.replace(/[\\s-]/g,"");
    localStorage.setItem("novaPhone",phone);

    fetch("/api/wishlist",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            phone:phone,
            product_id:Number(productId)
        })
    })
    .then(r=>r.json())
    .then(data=>{
        const btn=document.getElementById("wish-"+productId);
if(btn && data.success){
    if(data.message && data.message.includes("Already")){
        btn.innerText="❤️ WISHLISTED";
    }else{
        btn.innerText="❤️ WISHLISTED";
    }
}
alert(data.message || "Wishlist updated!");
    });
}

function placeOrder(){
 const name=document.getElementById("customerName").value.trim();
 const phone=document.getElementById("customerPhone").value.trim();
 const address=document.getElementById("customerAddress").value.trim();

 if(!name||!phone||!address){
  alert("Please fill all delivery details.");
  return;
 }

 fetch("/api/order",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({
   name:name,
   phone:phone,
   address:address,
   payment:document.getElementById("payment").value,
   items:cart,
   total:cart.reduce((sum,x)=>sum+(x.price*x.qty),0)
  })
 })
 .then(r=>r.json())
 .then(data=>{
  hideNovaLoader();
  if(data.success){
   showNovaSuccess(data.order.id);
   setTimeout(()=>{ window.location.href="/track?order="+data.order.id; },1800);
   cart=[];
   save();
   closeCheckout();
   closeCart();
  }
 });
}

updateCount();
showProducts();
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(PAGE, products=PRODUCTS)

@app.route("/api/status")
def status():
    return jsonify({"success":True,"message":"NOVALEX Python Backend Connected 🚀"})

@app.route("/api/profile", methods=["POST"])
def save_profile():
    data=request.get_json() or {}
    name=data.get("name","").strip()
    phone=data.get("phone","").strip()
    address=data.get("address","").strip()

    if not name or not phone:
        return jsonify({"success":False,"message":"Name and phone are required."}),400

    con=db()

    existing=con.execute(
        "SELECT id FROM customers WHERE phone=?",
        (phone,)
    ).fetchone()

    if existing:
        con.execute(
            "UPDATE customers SET name=?, address=? WHERE phone=?",
            (name,address,phone)
        )
    else:
        con.execute(
            "INSERT INTO customers(name,phone,address) VALUES(?,?,?)",
            (name,phone,address)
        )

    con.commit()
    con.close()

    return jsonify({"success":True,"message":"Profile saved successfully!"})


@app.route("/api/profile")
def get_profile():
    phone=request.args.get("phone","").strip()

    if not phone:
        return jsonify({"success":False,"message":"Phone required."}),400

    con=db()
    row=con.execute(
        "SELECT id,name,phone,address FROM customers WHERE phone=?",
        (phone,)
    ).fetchone()
    con.close()

    if not row:
        return jsonify({"success":False,"message":"Profile not found."}),404

    return jsonify({"success":True,"profile":dict(row)})


@app.route("/api/wishlist", methods=["POST"])
def add_wishlist():
    data=request.get_json() or {}
    phone=data.get("phone","").strip()
    product_id=int(data.get("product_id",0))

    if not phone or not product_id:
        return jsonify({"success":False,"message":"Phone and product required."}),400

    con=db()
    exists=con.execute(
        "SELECT id FROM wishlist WHERE phone=? AND product_id=?",
        (phone,product_id)
    ).fetchone()

    if exists:
        con.close()
        return jsonify({"success":True,"message":"Already in wishlist."})

    con.execute(
        "INSERT INTO wishlist(phone,product_id) VALUES(?,?)",
        (phone,product_id)
    )
    con.commit()
    con.close()

    return jsonify({"success":True,"message":"Added to wishlist!"})


@app.route("/api/wishlist", methods=["GET"])
def get_wishlist():
    phone=request.args.get("phone","").strip()

    con=db()
    rows=con.execute("""
        SELECT p.*
        FROM wishlist w
        JOIN products p ON p.id=w.product_id
        WHERE w.phone=?
        ORDER BY w.id DESC
    """,(phone,)).fetchall()
    con.close()

    return jsonify({"success":True,"products":[dict(r) for r in rows]})


@app.route("/api/wishlist/<int:product_id>", methods=["DELETE"])
def delete_wishlist(product_id):
    phone=request.args.get("phone","").strip()

    con=db()
    con.execute(
        "DELETE FROM wishlist WHERE phone=? AND product_id=?",
        (phone,product_id)
    )
    con.commit()
    con.close()

    return jsonify({"success":True,"message":"Removed from wishlist."})


@app.route("/api/order",methods=["POST"])
def create_order():
    data=request.get_json() or {}

    con=db()
    cur=con.execute("""
        INSERT INTO orders(name,phone,address,payment,items,total)
        VALUES(?,?,?,?,?,?)
    """,(
        data.get("name",""),
        data.get("phone",""),
        data.get("address",""),
        data.get("payment","COD"),
        str(data.get("items",[])),
        int(data.get("total",0))
    ))
    con.commit()

    order_id=cur.lastrowid
    con.close()

    return jsonify({
        "success":True,
        "order":{
            "id":order_id,
            **data
        }
    })


@app.route("/api/product",methods=["POST"])
def add_product():
    data=request.get_json() or {}

    name=data.get("name","New Product").strip()
    price=int(data.get("price",0))
    category=data.get("category","T-Shirts")

    if not name or price <= 0:
        return jsonify({
            "success":False,
            "message":"Enter valid product name and price."
        })

    image="/static/images/tshirt.jpg"
    icon="👕"

    if category=="Hoodies":
        image="/static/images/hoodie.jpg"
        icon="🧥"
    elif category=="Caps":
        image="/static/images/cap.jpg"
        icon="🧢"

    con=db()
    cur=con.execute("""
        INSERT INTO products(name,price,category,image,icon)
        VALUES(?,?,?,?,?)
    """,(name,price,category,image,icon))
    con.commit()
    product_id=cur.lastrowid
    con.close()

    PRODUCTS.clear()
    PRODUCTS.extend(load_products())

    return jsonify({
        "success":True,
        "message":"Product added successfully!",
        "product_id":product_id
    })

@app.route("/api/product/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    con = db()

    row = con.execute(
        "SELECT id FROM products WHERE id=?",
        (product_id,)
    ).fetchone()

    if not row:
        con.close()
        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404

    con.execute(
        "DELETE FROM products WHERE id=?",
        (product_id,)
    )
    con.commit()
    con.close()

    PRODUCTS.clear()
    PRODUCTS.extend(load_products())

    return jsonify({
        "success": True,
        "message": "Product deleted successfully!"
    })

@app.route("/api/admin-products")
def admin_products():
    con = db()
    rows = con.execute(
        "SELECT * FROM products ORDER BY id"
    ).fetchall()
    con.close()

    return jsonify({
        "success": True,
        "products": [dict(row) for row in rows]
    })

@app.route("/api/product/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    price = int(data.get("price", 0))
    category = data.get("category", "T-Shirts")

    if not name or price <= 0:
        return jsonify({
            "success": False,
            "message": "Enter valid product name and price."
        }), 400

    image = "/static/images/tshirt.jpg"
    icon = "👕"

    if category == "Hoodies":
        image = "/static/images/hoodie.jpg"
        icon = "🧥"
    elif category == "Caps":
        image = "/static/images/cap.jpg"
        icon = "🧢"

    con = db()

    row = con.execute(
        "SELECT id FROM products WHERE id=?",
        (product_id,)
    ).fetchone()

    if not row:
        con.close()
        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404

    con.execute("""
        UPDATE products
        SET name=?, price=?, category=?, image=?, icon=?
        WHERE id=?
    """, (name, price, category, image, icon, product_id))

    con.commit()
    con.close()

    PRODUCTS.clear()
    PRODUCTS.extend(load_products())

    return jsonify({
        "success": True,
        "message": "Product updated successfully!"
    })

@app.route("/api/order/<int:order_id>")
def track_order(order_id):
    con = db()

    row = con.execute(
        "SELECT id,name,total,status FROM orders WHERE id=?",
        (order_id,)
    ).fetchone()

    con.close()

    if not row:
        return jsonify({
            "success": False,
            "message": "Order not found."
        }), 404

    return jsonify({
        "success": True,
        "order": dict(row)
    })


@app.route("/api/my-orders")
def my_orders():
    phone = request.args.get("phone", "").strip()

    if not phone:
        return jsonify({
            "success": False,
            "message": "Phone number required."
        }), 400

    con = db()
    rows = con.execute(
        "SELECT id,name,total,status FROM orders WHERE phone=? ORDER BY id DESC",
        (phone,)
    ).fetchall()
    con.close()

    return jsonify({
        "success": True,
        "orders": [dict(row) for row in rows]
    })


@app.route("/api/orders")
def get_orders():
    con = db()
    rows = con.execute(
        "SELECT * FROM orders ORDER BY id DESC"
    ).fetchall()
    con.close()

    return jsonify({
        "success": True,
        "orders": [dict(row) for row in rows]
    })

@app.route("/api/order/<int:order_id>", methods=["DELETE"])
def delete_order(order_id):
    con = db()

    cur = con.execute(
        "DELETE FROM orders WHERE id=?",
        (order_id,)
    )

    con.commit()
    con.close()

    if cur.rowcount == 0:
        return jsonify({
            "success": False,
            "message": "Order not found."
        }), 404

    return jsonify({
        "success": True,
        "message": "Order deleted successfully!"
    })


@app.route("/api/order/<int:order_id>/cancel", methods=["PUT"])
def cancel_order(order_id):
    con = db()

    row = con.execute(
        "SELECT status FROM orders WHERE id=?",
        (order_id,)
    ).fetchone()

    if not row:
        con.close()
        return jsonify({
            "success": False,
            "message": "Order not found."
        }), 404

    if row["status"] != "Pending":
        con.close()
        return jsonify({
            "success": False,
            "message": "Only Pending orders can be cancelled."
        }), 400

    con.execute(
        "UPDATE orders SET status=? WHERE id=?",
        ("Cancelled", order_id)
    )
    con.commit()
    con.close()

    return jsonify({
        "success": True,
        "message": "Order cancelled successfully!"
    })


@app.route("/api/order/<int:order_id>/status", methods=["PUT"])
def update_order_status(order_id):
    data = request.get_json() or {}
    status = data.get("status", "Pending")

    allowed = ["Pending", "Confirmed", "Shipped", "Delivered"]

    if status not in allowed:
        return jsonify({
            "success": False,
            "message": "Invalid order status."
        }), 400

    con = db()
    cur = con.execute(
        "UPDATE orders SET status=? WHERE id=?",
        (status, order_id)
    )
    con.commit()
    con.close()

    if cur.rowcount == 0:
        return jsonify({
            "success": False,
            "message": "Order not found."
        }), 404

    return jsonify({
        "success": True,
        "message": "Order status updated!"
    })

@app.route("/my-orders")
def my_orders_page():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NOVALEX My Orders</title>
<style>
body{
    margin:0;
    font-family:Arial,sans-serif;
    background:#111;
    color:white;
    padding:25px;
}
.box{
    max-width:500px;
    margin:40px auto;
    background:#222;
    padding:25px;
    border-radius:18px;
}
input,button{
    width:100%;
    box-sizing:border-box;
    padding:14px;
    margin-top:10px;
    border-radius:10px;
    border:0;
}
button{
    font-weight:bold;
    cursor:pointer;
}
.order{
    background:#111;
    padding:15px;
    margin-top:12px;
    border-radius:12px;
}
</style>
</head>
<body>

<div class="box">
<h1>📦 NOVALEX</h1>
<h2>My Orders</h2>

<input id="phone" type="tel" placeholder="Enter your phone number">

<button onclick="loadOrders()">VIEW MY ORDERS</button>

<div id="result"></div>
</div>

<script>
function cancelOrder(id){
    if(!confirm("Are you sure you want to cancel this order?")){
        return;
    }

    fetch("/api/order/"+id+"/cancel",{
        method:"PUT"
    })
    .then(r=>r.json())
    .then(data=>{
        alert(data.message);
        if(data.success){
            loadOrders();
        }
    })
    .catch(()=>{
        alert("Unable to cancel order.");
    });
}

function loadOrders(){
    let phone=document.getElementById("phone").value.trim();
phone=phone.replace(/[\\s-]/g,"");
if(phone.startsWith("+91")){
    phone=phone.substring(3);
}
if(phone.startsWith("91") && phone.length===12){
    phone=phone.substring(2);
}
if(phone.length===10){
    phone="0"+phone;
}
    const result=document.getElementById("result");

    if(!phone){
        result.innerHTML="<p>Please enter your phone number.</p>";
        return;
    }

    result.innerHTML="<p>Loading...</p>";

    fetch("/api/my-orders?phone="+encodeURIComponent(phone))
    .then(r=>r.json())
    .then(data=>{
        if(!data.success){
            result.innerHTML="<p>"+data.message+"</p>";
            return;
        }

        if(data.orders.length===0){
            result.innerHTML="<p>No orders found.</p>";
            return;
        }

        result.innerHTML=data.orders.map(o=>`
            <div class="order">
                <h3>Order #${o.id}</h3>
                <p>Total: ₹${o.total}</p>
                <p>Status: <b>${o.status}</b></p>
                <button onclick="location.href='/track?order=${o.id}'">
                    📦 Track Order
                </button>

                ${o.status==="Pending" ? `
                <button onclick="cancelOrder(${o.id})" style="background:#d33;color:white">
                    ❌ Cancel Order
                </button>
                ` : ""}
            </div>
        `).join("");
    })
    .catch(()=>{
        result.innerHTML="<p>Unable to load orders.</p>";
    });
}
</script>

</body>
</html>
""")





@app.route("/profile")
def profile_page():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NOVALEX Profile</title>
<style>
body{
    margin:0;
    font-family:Arial,sans-serif;
    background:#111;
    color:white;
    padding:20px;
}
.box{
    max-width:500px;
    margin:40px auto;
    background:#222;
    padding:25px;
    border-radius:20px;
}
input,button{
    width:100%;
    box-sizing:border-box;
    padding:14px;
    margin-top:12px;
    border-radius:10px;
    border:0;
}
button{
    background:white;
    color:#111;
    font-weight:bold;
    cursor:pointer;
}
</style>
</head>
<body>

<div class="box">
<h1>👤 NOVALEX PROFILE</h1>

<input id="name" placeholder="Your Name">
<input id="phone" placeholder="Mobile Number">
<input id="address" placeholder="Delivery Address">

<button onclick="saveProfile()">SAVE PROFILE</button>

<p id="msg"></p>
</div>

<script>
function saveProfile(){
    const name=document.getElementById("name").value.trim();
    const phone=document.getElementById("phone").value.trim();
    const address=document.getElementById("address").value.trim();

    if(!name || !phone){
        alert("Name and phone are required.");
        return;
    }

    localStorage.setItem("novaPhone",phone);
    localStorage.setItem("novaName",name);

    fetch("/api/profile",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            name:name,
            phone:phone,
            address:address
        })
    })
    .then(r=>r.json())
    .then(data=>{
        document.getElementById("msg").innerText=data.message;
    });
}

const savedPhone=localStorage.getItem("novaPhone");
const savedName=localStorage.getItem("novaName");

if(savedPhone) document.getElementById("phone").value=savedPhone;
if(savedName) document.getElementById("name").value=savedName;
</script>

</body>
</html>
""")

@app.route("/wishlist")
def wishlist_page():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NOVALEX Wishlist</title>
<style>
body{
    margin:0;
    font-family:Arial,sans-serif;
    background:#111;
    color:white;
    padding:20px;
}
.box{
    max-width:700px;
    margin:auto;
}
h1{text-align:center}
input,button{
    width:100%;
    box-sizing:border-box;
    padding:13px;
    margin-top:10px;
    border-radius:10px;
    border:0;
}
button{
    font-weight:bold;
    cursor:pointer;
}
.item{
    display:flex;
    gap:15px;
    align-items:center;
    background:#222;
    padding:12px;
    margin-top:12px;
    border-radius:14px;
}
.item img{
    width:75px;
    height:75px;
    object-fit:cover;
    border-radius:10px;
}
.remove{
    width:auto;
    background:#c62828;
    color:white;
    padding:8px 12px;
}
</style>
</head>
<body>
<div class="box">
<h1>❤️ NOVALEX WISHLIST</h1>

<input id="phone" placeholder="Enter mobile number">
<button onclick="loadWishlist()">VIEW WISHLIST</button>

<div id="list"></div>
</div>

<script>
function loadWishlist(){
    let phone=document.getElementById("phone").value.trim();

    if(!phone){
        alert("Enter mobile number.");
        return;
    }

    localStorage.setItem("novaPhone",phone);

    fetch("/api/wishlist?phone="+encodeURIComponent(phone))
    .then(r=>r.json())
    .then(data=>{
        const list=document.getElementById("list");

        if(!data.products.length){
            list.innerHTML="<p style='text-align:center;margin-top:30px'>❤️ Your wishlist is empty.</p>";
            return;
        }

        list.innerHTML=data.products.map(p=>`
            <div class="item">
                <img src="${p.image}" onerror="this.style.display='none'">
                <div style="flex:1">
                    <b>${p.name}</b>
                    <div style="margin-top:6px">₹${p.price}</div>
                    <button class="remove" onclick="removeWishlist(${p.id})">REMOVE</button>
                </div>
            </div>
        `).join("");
    });
}

function removeWishlist(id){
    const phone=document.getElementById("phone").value.trim();

    fetch("/api/wishlist/"+id+"?phone="+encodeURIComponent(phone),{
        method:"DELETE"
    })
    .then(r=>r.json())
    .then(()=>{
        loadWishlist();
    });
}

const saved=localStorage.getItem("novaPhone");
if(saved){
    document.getElementById("phone").value=saved;
    loadWishlist();
}
</script>
</body>
</html>
""")

@app.route("/track")
def track_page():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NOVALEX Order Tracking</title>
<style>
body{
    margin:0;
    font-family:Arial,sans-serif;
    background:#111;
    color:white;
    padding:25px;
}
.box{
    max-width:500px;
    margin:40px auto;
    background:#222;
    padding:25px;
    border-radius:18px;
}
input,button{
    width:100%;
    box-sizing:border-box;
    padding:14px;
    margin-top:10px;
    border-radius:10px;
    border:0;
}
button{
    font-weight:bold;
    cursor:pointer;
}
#result{
    margin-top:20px;
}
.status{
    font-size:22px;
    font-weight:bold;
    margin-top:10px;
}
</style>
</head>
<body>

<div class="box">
<h1>📦 NOVALEX</h1>
<h2>Track Your Order</h2>

<input id="orderId" type="number" placeholder="Enter Order ID">

<button onclick="trackOrder()">TRACK ORDER</button>

<div id="result"></div>
</div>

<script>
function trackOrder(){
    const id = document.getElementById("orderId").value.trim();
    const result = document.getElementById("result");

    if(!id){
        result.innerHTML = "<p>Please enter your Order ID.</p>";
        return;
    }

    result.innerHTML = "<p>⏳ Loading order...</p>";

    fetch("/api/order/" + id)
    .then(function(response){
        return response.json();
    })
    .then(function(data){
        if(!data.success){
            result.innerHTML = "<p>❌ " + (data.message || "Order not found.") + "</p>";
            return;
        }

        const order = data.order;

        let message = "Order status updated.";
        if(order.status === "Pending"){
            message = "⏳ Your order is waiting for confirmation.";
        }else if(order.status === "Confirmed"){
            message = "✅ Your order has been confirmed.";
        }else if(order.status === "Shipped"){
            message = "🚚 Your order is on the way.";
        }else if(order.status === "Delivered"){
            message = "🎉 Your order has been delivered.";
        }else if(order.status === "Cancelled"){
            message = "❌ This order has been cancelled.";
        }

        result.innerHTML =
            "<div style='background:#111;padding:15px;border-radius:12px'>" +
            "<h3>Order #" + order.id + "</h3>" +
            "<p>Customer: " + order.name + "</p>" +
            "<p>Total: ₹" + order.total + "</p>" +
            "<div class='status'>Status: " + order.status + "</div>" +
            "<div style='margin-top:12px;padding:12px;background:#222;border-radius:10px'>" +
            message +
            "</div>" +
            "</div>";
    })
    .catch(function(){
        result.innerHTML = "<p>❌ Unable to track order.</p>";
    });
}

document.addEventListener("DOMContentLoaded", function(){
    const urlOrderId = new URLSearchParams(window.location.search).get("order");

    if(urlOrderId){
        document.getElementById("orderId").value = urlOrderId;
        setTimeout(function(){
            trackOrder();
        }, 300);
    }
});
</script>

</body>
</html>
""")

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return render_template_string("""
        <html><body style="font-family:Arial;background:#111;color:white;padding:30px">
        <h1>NOVALEX ADMIN LOGIN</h1>
        <form method="post" action="/admin/login">
        <input name="password" type="password" placeholder="Admin Password" style="padding:14px">
        <button style="padding:14px">LOGIN</button>
        </form>
        </body></html>
        """)

    return render_template_string("""
    <html>
    <head><meta name="viewport" content="width=device-width,initial-scale=1"></head>
    <body style="font-family:Arial;background:#111;color:white;padding:25px">
    <style>
.adminWrap{
    max-width:1100px;
    margin:auto;
}
.adminTitle{
    font-size:32px;
    font-weight:800;
    margin-bottom:5px;
}
.adminSub{
    color:#aaa;
    margin-bottom:20px;
}
.statsGrid{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:15px;
    margin:20px 0;
}
.statCard{
    background:linear-gradient(145deg,#252525,#171717);
    border:1px solid #333;
    padding:20px;
    border-radius:18px;
    box-shadow:0 8px 25px rgba(0,0,0,.25);
}
.statIcon{
    font-size:30px;
    margin-bottom:8px;
}
.statLabel{
    color:#aaa;
    font-size:14px;
}
.statValue{
    font-size:28px;
    font-weight:800;
    margin-top:5px;
}
@media(max-width:600px){
    body{padding:15px!important}
    .statsGrid{grid-template-columns:1fr}
    .adminTitle{font-size:26px}
}
</style>

<div class="adminWrap">
<div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
<div class="adminTitle">NOVALEX ADMIN</div>
<a href="/admin/logout" style="background:#ff3b30;color:white;padding:10px 16px;border-radius:12px;text-decoration:none;font-weight:bold">🚪 Logout</a>
</div>
<div class="adminSub">Store management dashboard</div>

<div class="statsGrid">
    <div class="statCard">
        <div class="statIcon">📦</div>
        <div class="statLabel">TOTAL PRODUCTS</div>
        <div class="statValue" id="statProducts">0</div>
    </div>

    <div class="statCard">
        <div class="statIcon">🛒</div>
        <div class="statLabel">TOTAL ORDERS</div>
        <div class="statValue" id="statOrders">0</div>
    </div>

    <div class="statCard">
        <div class="statIcon">💰</div>
        <div class="statLabel">TOTAL SALES</div>
        <div class="statValue" id="statSales">₹0</div>
    </div>
</div>

    <div style="background:#222;padding:20px;border-radius:15px;margin:15px 0">
    <h2>📦 Products Management</h2>

    <input id="pname" placeholder="Product Name"
    style="width:100%;padding:12px;margin:5px 0;box-sizing:border-box">

    <input id="pprice" type="number" placeholder="Price"
    style="width:100%;padding:12px;margin:5px 0;box-sizing:border-box">

    <select id="pcat"
    style="width:100%;padding:12px;margin:5px 0;box-sizing:border-box">
    <option>T-Shirts</option>
    <option>Hoodies</option>
    <option>Caps</option>
    </select>

    <button onclick="addProduct()"
    style="width:100%;padding:13px;margin-top:8px;border:0;border-radius:10px;font-weight:bold">
    ADD PRODUCT
    </button>

    <p id="productMsg"></p>

    <h3>Current Products</h3>
    <div id="productList">Loading products...</div>
    </div>

    <script>
    function loadAdminProducts(){
        fetch("/api/admin-products")
        .then(r=>r.json())
        .then(data=>{
            const box=document.getElementById("productList");

            if(!data.products.length){
                box.innerHTML="<p>No products found.</p>";
                return;
            }

            box.innerHTML=data.products.map(p=>`
                <div style="border-top:1px solid #444;padding:12px 0">
                    <b>${p.name}</b><br>
                    ₹${p.price} • ${p.category}
                    <br>
                    <button onclick="editProduct(${p.id},${JSON.stringify(p.name)},${p.price},${JSON.stringify(p.category)})"
                    style="margin-top:8px;padding:8px 12px;border:0;border-radius:8px">
                    ✏️ EDIT
                    </button>

                    <button onclick="deleteProduct(${p.id})"
                    style="margin-top:8px;padding:8px 12px;border:0;border-radius:8px">
                    🗑️ DELETE
                    </button>
                </div>
            `).join("");
        });
    }

    function deleteProduct(id){
        if(!confirm("Delete this product?")) return;

        fetch("/api/product/"+id,{
            method:"DELETE"
        })
        .then(r=>r.json())
        .then(data=>{
            alert(data.message);
            loadAdminProducts();
        });
    }

    function editProduct(id,name,price,category){
        const newName=prompt("Product Name:",name);
        if(newName===null) return;

        const newPrice=prompt("Price:",price);
        if(newPrice===null) return;

        const newCategory=prompt(
            "Category: T-Shirts / Hoodies / Caps",
            category
        );
        if(newCategory===null) return;

        fetch("/api/product/"+id,{
            method:"PUT",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                name:newName.trim(),
                price:Number(newPrice),
                category:newCategory.trim()
            })
        })
        .then(r=>r.json())
        .then(data=>{
            alert(data.message);
            loadAdminProducts();
        });
    }

    loadAdminProducts();

    fetch("/api/admin-products")
    .then(r=>r.json())
    .then(d=>{
        document.getElementById("statProducts").innerText=d.products.length;
    });

    fetch("/api/orders")
    .then(r=>r.json())
    .then(d=>{
        document.getElementById("statOrders").innerText=d.orders.length;
        const sales=d.orders
    .filter(o=>o.status==="Delivered")
    .reduce((sum,o)=>sum+Number(o.total||0),0);
        document.getElementById("statSales").innerText="₹"+sales;
    });
    </script>
    <script>
    function addProduct(){
        const name=document.getElementById("pname").value.trim();
        const price=Number(document.getElementById("pprice").value);
        const category=document.getElementById("pcat").value;

        if(!name || !price){
            alert("Enter product name and price.");
            return;
        }

        fetch("/api/product",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                name:name,
                price:price,
                category:category
            })
        })
        .then(r=>r.json())
        .then(data=>{
            document.getElementById("productMsg").innerText=data.message;
            document.getElementById("pname").value="";
            document.getElementById("pprice").value="";
        });
    }
    </script>
    <div style="background:#222;padding:20px;border-radius:15px;margin:15px 0">
    🛒 Orders Management
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin:15px 0">
<button onclick="filterOrders('All')" style="padding:10px 15px;border:0;border-radius:10px">All</button>
<button onclick="filterOrders('Pending')" style="padding:10px 15px;border:0;border-radius:10px">Pending</button>
<button onclick="filterOrders('Confirmed')" style="padding:10px 15px;border:0;border-radius:10px">Confirmed</button>
<button onclick="filterOrders('Shipped')" style="padding:10px 15px;border:0;border-radius:10px">Shipped</button>
<button onclick="filterOrders('Delivered')" style="padding:10px 15px;border:0;border-radius:10px">Delivered</button>
<button onclick="filterOrders('Cancelled')" style="padding:10px 15px;border:0;border-radius:10px">Cancelled</button>
</div>

<input id="orderSearch" oninput="searchOrders()" placeholder="🔎 Search Order ID, customer or phone"
style="width:100%;box-sizing:border-box;padding:13px;margin:10px 0 15px;border-radius:12px;border:1px solid #444;background:#111;color:white">

<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:15px 0">
<div style="background:#222;padding:12px;border-radius:12px;text-align:center">
<div style="font-size:12px;color:#aaa">PENDING</div>
<b id="countPending">0</b>
</div>
<div style="background:#222;padding:12px;border-radius:12px;text-align:center">
<div style="font-size:12px;color:#aaa">CONFIRMED</div>
<b id="countConfirmed">0</b>
</div>
<div style="background:#222;padding:12px;border-radius:12px;text-align:center">
<div style="font-size:12px;color:#aaa">SHIPPED</div>
<b id="countShipped">0</b>
</div>
<div style="background:#222;padding:12px;border-radius:12px;text-align:center">
<div style="font-size:12px;color:#aaa">DELIVERED</div>
<b id="countDelivered">0</b>
</div>
<div style="background:#222;padding:12px;border-radius:12px;text-align:center">
<div style="font-size:12px;color:#aaa">CANCELLED</div>
<b id="countCancelled">0</b>
</div>
</div>

<style>
.orderCard{
    background:linear-gradient(145deg,#242424,#151515);
    border:1px solid #333;
    padding:18px;
    margin:12px 0;
    border-radius:16px;
    box-shadow:0 6px 20px rgba(0,0,0,.2);
}
.orderTop{
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:10px;
    flex-wrap:wrap;
}
.orderId{
    font-size:18px;
    font-weight:800;
}
.orderStatus{
    padding:6px 10px;
    border-radius:20px;
    background:#333;
    font-size:12px;
    font-weight:bold;
}
.orderInfo{
    color:#bbb;
    line-height:1.7;
    margin-top:10px;
}
</style>

<div id="orders">Loading...</div>
    </div>
    <script>
    let allAdminOrders=[];

let currentOrderFilter="All";

function searchOrders(){
    const q=document.getElementById("orderSearch").value.trim().toLowerCase();

    let filtered=allAdminOrders;

    if(currentOrderFilter!=="All"){
        filtered=filtered.filter(o=>o.status===currentOrderFilter);
    }

    filtered=filtered.filter(o =>
        String(o.id).includes(q) ||
        String(o.name || "").toLowerCase().includes(q) ||
        String(o.phone || "").includes(q)
    );

    document.getElementById("orders").innerHTML=filtered.length
        ? filtered.map(o=>`
            <div style="padding:10px 0;border-bottom:1px solid #444">
                <b>Order #${o.id}</b><br>
                Customer: ${o.name}<br>
                Phone: ${o.phone}<br>
                Total: ₹${o.total}<br>
                Status: <b>${o.status}</b>
            </div>
        `).join("")
        : "<p>No matching orders found.</p>";
}

function filterOrders(status){
    currentOrderFilter=status;

    const q=document.getElementById("orderSearch").value.trim().toLowerCase();

    let orders=status==="All"
        ? allAdminOrders
        : allAdminOrders.filter(o=>o.status===status);

    if(q){
        orders=orders.filter(o =>
            String(o.id).includes(q) ||
            String(o.name || "").toLowerCase().includes(q) ||
            String(o.phone || "").includes(q)
        );
    }

    document.getElementById("orders").innerHTML=orders.length
        ? orders.map(o=>`
            <div style="padding:10px 0;border-bottom:1px solid #444">
                <b>Order #${o.id}</b><br>
                Customer: ${o.name}<br>
                Total: ₹${o.total}<br>
                Status: <b>${o.status}</b>
            </div>
        `).join("")
        : "<p>No "+status+" orders found.</p>";
}

fetch("/api/orders").then(r=>r.json()).then(d=>{
     allAdminOrders=d.orders;

     ["Pending","Confirmed","Shipped","Delivered","Cancelled"].forEach(st=>{
        const el=document.getElementById("count"+st);
        if(el) el.innerText=allAdminOrders.filter(o=>o.status===st).length;
     });

     filterOrders("All"); document.getElementById("orders").innerHTML=d.orders.length?
     d.orders.map(o=>`
<hr>
<div style="padding:10px 0">
<b>Order #${o.id}</b><br>
Customer: ${o.name}<br>
Phone: ${o.phone}<br>
Address: ${o.address}<br>
Payment: ${o.payment}<br>
Total: ₹${o.total}<br>

<details style="margin-top:10px">
<summary style="cursor:pointer;font-weight:bold">📋 VIEW ORDER ITEMS</summary>
<div style="margin-top:8px;background:#111;padding:10px;border-radius:8px">
${(() => {
    try {
        const items = JSON.parse(o.items || "[]");
        return items.length
            ? items.map(i => `<div style="padding:5px 0;border-bottom:1px solid #333">${i.name} × ${i.qty} — ₹${Number(i.price) * Number(i.qty)}</div>`).join("")
            : "No items found.";
    } catch(e) {
        return "Order items unavailable.";
    }
})()}
</div>
</details>
Status:
<select onchange="changeOrderStatus(${o.id},this.value)"
style="padding:7px;margin-top:6px;border-radius:7px">
<option ${o.status==="Pending"?"selected":""}>Pending</option>
<option ${o.status==="Confirmed"?"selected":""}>Confirmed</option>
<option ${o.status==="Shipped"?"selected":""}>Shipped</option>
<option ${o.status==="Delivered"?"selected":""}>Delivered</option>
</select>

<button onclick="deleteOrder(${o.id})"
style="display:block;margin-top:10px;padding:8px 12px;border:0;border-radius:8px;background:#c62828;color:white;font-weight:bold">
🗑️ DELETE ORDER
</button>
</div>
`).join("")
     :"No orders yet.";
    });
    function deleteOrder(id){
        if(!confirm("Delete this order?")) return;

        fetch("/api/order/"+id,{
            method:"DELETE"
        })
        .then(r=>r.json())
        .then(data=>{
            alert(data.message);
            location.reload();
        });
    }

    function changeOrderStatus(id,status){
        fetch("/api/order/"+id+"/status",{
            method:"PUT",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({status:status})
        })
        .then(r=>r.json())
        .then(data=>{
            alert(data.message);
        });
    }
    </script>
    </body></html>
    """)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return "Logged out successfully. <a href='/admin'>Login Again</a>"

@app.route("/admin/login",methods=["POST"])
def admin_login():
    if request.form.get("password")==os.environ.get("NOVALEX_ADMIN_PASSWORD",""):
        session["admin"]=True
        return "Login successful. <a href='/admin'>Open Admin Panel</a>"
    return "Wrong password. <a href='/admin'>Try again</a>"

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000,debug=False)
