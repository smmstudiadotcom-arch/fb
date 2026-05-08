"""
Facebook Reels бот (curl_cffi с TLS impersonation Chrome 120)
"""
import random
import time
import os
import re
import requests
from datetime import datetime
from curl_cffi import requests as curl_requests

# ══════════════════════════════════════
#  JAP
# ══════════════════════════════════════
JAP_API_KEY = "ec2fb6c8f5a4ea7ba6cf532e87a09895"
JAP_API_URL = "https://justanotherpanel.com/api/v2"

# ══════════════════════════════════════
#  FACEBOOK REELS
# ══════════════════════════════════════
FB_PAGE_ID     = "100081997113052"
FB_SERVICE     = 9604
FB_QTY_MIN     = 500
FB_QTY_MAX     = 1000
CHECK_INTERVAL = 3600  # каждый час

# Cookies
C_USER = os.environ.get("FB_C_USER", "61553351803414")
XS     = os.environ.get("FB_XS",     "23%3AUcW9QDH7Lw4OMA%3A2%3A1777366320%3A-1%3A-1%3A%3AAcxV4doD641eN1HEAQNfnkX0cE357pxRh9ixF-wCuA")
DATR   = os.environ.get("FB_DATR",   "gvGqaR00HB8BBQCtWvA_ZrBw")
FR     = os.environ.get("FB_FR",     "1BiHkrekV5y5wC9M4.AWcjA0M_D1BFpG4ArVdD9DEHJz1hf_Cp4e633bJFekyBL_WG64E.Bp8HUz..AAA.0.0.Bp8HUz.AWd2xaqh1GaCzn5odyasmAo3ovQ")
SB     = os.environ.get("FB_SB",     "hfGqaZIWmBX2PQV9iqh9Tr1V")

COOKIES_STR = f"c_user={C_USER}; xs={XS}; datr={DATR}; fr={FR}; sb={SB}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cookie": COOKIES_STR,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Upgrade-Insecure-Requests": "1",
}

STATE_FILE = "processed_reels.txt"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [FB-Reels] {msg}", flush=True)

def load_processed():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed(data):
    with open(STATE_FILE, "w") as f:
        for item in data:
            f.write(f"{item}\n")

def check_balance():
    try:
        resp = requests.post(JAP_API_URL, data={"key": JAP_API_KEY, "action": "balance"}, timeout=10)
        if resp.text.strip():
            data = resp.json()
            if "balance" in data:
                log(f"💰 Баланс: ${data['balance']} {data.get('currency', '')}")
    except Exception as e:
        log(f"❌ Ошибка баланса: {e}")

def create_jap_order(link):
    quantity = random.randint(FB_QTY_MIN, FB_QTY_MAX)
    payload = {"key": JAP_API_KEY, "action": "add", "service": FB_SERVICE, "link": link, "quantity": quantity}
    try:
        log(f"📤 Заказ: service={FB_SERVICE}, qty={quantity}")
        resp = requests.post(JAP_API_URL, data=payload, timeout=15)
        log(f"📥 JAP: {resp.status_code} | {repr(resp.text[:150])}")
        if not resp.text.strip():
            log("❌ Пустой ответ JAP")
            return
        data = resp.json()
        if "order" in data:
            log(f"✅ Заказ! ID: {data['order']} | Кол-во: {quantity}")
        elif "error" in data:
            log(f"❌ JAP ошибка: {data['error']}")
    except Exception as e:
        log(f"❌ Ошибка заказа: {e}")

def fetch_reels():
    """Парсим страницу Reels через curl_cffi с TLS impersonation"""
    try:
        url = f"https://www.facebook.com/profile.php?id={FB_PAGE_ID}&sk=reels_tab"
        log(f"🔄 GET {url}")
        
        resp = curl_requests.get(
            url,
            headers=HEADERS,
            impersonate="chrome120",
            timeout=30,
            allow_redirects=True
        )
        log(f"📥 Status: {resp.status_code} | HTML: {len(resp.text)} символов")
        
        if resp.status_code != 200:
            log(f"⚠️  Ответ: {resp.text[:200]}")
            return []
        
        html = resp.text
        # Убираем экранирование слешей в JSON
        html_clean = html.replace("\\\\/", "/").replace("\\/", "/")
        
        urls = set()
        
        # Паттерны для поиска Reels
        patterns = [
            r'/reel/(\d{10,})',
            r'"video_id":"(\d{10,})"',
            r'/videos/(\d{10,})',
            r'watch/\?v=(\d{10,})',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, html_clean):
                urls.add(f"https://www.facebook.com/reel/{match.group(1)}")
        
        log(f"🎬 Найдено Reels: {len(urls)}")
        if urls:
            for u in list(urls)[:5]:
                log(f"   → {u}")
        
        return list(urls)
    
    except Exception as e:
        log(f"❌ Ошибка: {e}")
        return []

def main():
    log("🚀 Facebook Reels бот запущен (curl_cffi)!")
    log(f"📘 Страница: {FB_PAGE_ID} | Услуга: {FB_SERVICE} | {FB_QTY_MIN}-{FB_QTY_MAX}")
    check_balance()
    
    processed = load_processed()
    
    # Первый запуск — запоминаем существующие Reels
    if not processed:
        log("📌 Первый запуск — запоминаю существующие Reels...")
        reels = fetch_reels()
        if reels:
            processed.update(reels)
            save_processed(processed)
            log(f"📌 Запомнено {len(reels)} Reels. Жду новые...")
        else:
            log("⚠️  Reels не найдены при первом запуске")
    
    while True:
        time.sleep(CHECK_INTERVAL)
        try:
            reels = fetch_reels()
            new_reels = [url for url in reels if url not in processed]
            
            if new_reels:
                log(f"🆕 Новых Reels: {len(new_reels)}")
                for reel_url in new_reels:
                    log(f"🆕 {reel_url}")
                    create_jap_order(reel_url)
                    processed.add(reel_url)
                    time.sleep(2)
                save_processed(processed)
            else:
                log("🔍 Нет новых Reels")
        except Exception as e:
            log(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
