"""
Facebook Reels бот (curl_cffi с TLS impersonation Chrome 120)
2 страницы, лимит 10 заказов в день на каждую
"""
import random
import time
import os
import re
import json
import requests
from datetime import datetime, date
from curl_cffi import requests as curl_requests

# ══════════════════════════════════════
#  JAP
# ══════════════════════════════════════
JAP_API_KEY = "ec2fb6c8f5a4ea7ba6cf532e87a09895"
JAP_API_URL = "https://justanotherpanel.com/api/v2"

# ══════════════════════════════════════
#  FACEBOOK PAGES
# ══════════════════════════════════════
FB_PAGES = [
    {
        "name":     "National-Centre-Russia",
        "page_id":  "100081997113052",
        "url":      "https://www.facebook.com/profile.php?id=100081997113052&sk=reels_tab",
        "service":  9604,
        "qty_min":  500,
        "qty_max":  1000,
        "all_posts": False,  # только Reels
    },
    {
        "name":     "kinshik",
        "page_id":  "kinshik",
        "url":      "https://www.facebook.com/kinshik",
        "service":  7654,
        "qty_min":  30,
        "qty_max":  55,
        "all_posts": True,  # парсить все типы постов
    },
]

CHECK_INTERVAL    = 3600  # каждый час
DAILY_LIMIT       = 10    # макс заказов в день на страницу

# ══════════════════════════════════════
#  COOKIES
# ══════════════════════════════════════
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

STATE_FILE       = "processed_reels.json"
DAILY_COUNT_FILE = "daily_count.json"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [FB-Reels] {msg}", flush=True)

# ══════════════════════════════════════
#  STATE: обработанные Reels
# ══════════════════════════════════════
def load_processed():
    """Возвращает {page_name: set(reel_urls)}"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
            return {k: set(v) for k, v in data.items()}
        except Exception:
            pass
    return {}

def save_processed(data):
    with open(STATE_FILE, "w") as f:
        json.dump({k: list(v) for k, v in data.items()}, f)

# ══════════════════════════════════════
#  STATE: дневной счётчик
# ══════════════════════════════════════
def load_daily_count():
    """Возвращает {page_name: {"date": "YYYY-MM-DD", "count": N}}"""
    if os.path.exists(DAILY_COUNT_FILE):
        try:
            with open(DAILY_COUNT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_daily_count(data):
    with open(DAILY_COUNT_FILE, "w") as f:
        json.dump(data, f)

def get_today_count(daily, page_name):
    """Сколько заказов на эту страницу сегодня"""
    today = date.today().isoformat()
    page_data = daily.get(page_name, {})
    if page_data.get("date") != today:
        return 0
    return page_data.get("count", 0)

def increment_daily_count(daily, page_name):
    today = date.today().isoformat()
    page_data = daily.get(page_name, {})
    if page_data.get("date") != today:
        daily[page_name] = {"date": today, "count": 1}
    else:
        daily[page_name]["count"] = page_data.get("count", 0) + 1
    save_daily_count(daily)

# ══════════════════════════════════════
#  JAP
# ══════════════════════════════════════
def check_balance():
    try:
        resp = requests.post(JAP_API_URL, data={"key": JAP_API_KEY, "action": "balance"}, timeout=10)
        if resp.text.strip():
            data = resp.json()
            if "balance" in data:
                log(f"💰 Баланс: ${data['balance']} {data.get('currency', '')}")
    except Exception as e:
        log(f"❌ Ошибка баланса: {e}")

def create_jap_order(link, service, qty_min, qty_max, page_name):
    quantity = random.randint(qty_min, qty_max)
    payload = {"key": JAP_API_KEY, "action": "add", "service": service, "link": link, "quantity": quantity}
    try:
        log(f"📤 [{page_name}] Заказ: service={service}, qty={quantity}")
        resp = requests.post(JAP_API_URL, data=payload, timeout=15)
        log(f"📥 JAP: {resp.status_code} | {repr(resp.text[:150])}")
        if not resp.text.strip():
            log("❌ Пустой ответ JAP")
            return False
        data = resp.json()
        if "order" in data:
            log(f"✅ [{page_name}] Заказ! ID: {data['order']} | Кол-во: {quantity}")
            return True
        elif "error" in data:
            log(f"❌ JAP ошибка: {data['error']}")
    except Exception as e:
        log(f"❌ Ошибка заказа: {e}")
    return False

# ══════════════════════════════════════
#  FACEBOOK SCRAPING
# ══════════════════════════════════════
def fetch_reels(page_url, page_name, all_posts=False):
    """Парсим страницу через curl_cffi
    all_posts=True — ищем все типы постов (с нескольких URL)
    all_posts=False — только Reels с одной страницы
    """
    try:
        urls = set()
        
        if all_posts:
            # Парсим несколько URL чтобы собрать все типы контента
            urls_to_fetch = [
                f"https://www.facebook.com/{page_name}",
                f"https://www.facebook.com/{page_name}/videos",
                f"https://www.facebook.com/{page_name}/reels",
                f"https://www.facebook.com/{page_name}/posts",
            ]
        else:
            urls_to_fetch = [page_url]
        
        for url in urls_to_fetch:
            log(f"🔄 [{page_name}] GET {url}")
            
            try:
                resp = curl_requests.get(
                    url,
                    headers=HEADERS,
                    impersonate="chrome120",
                    timeout=30,
                    allow_redirects=True
                )
                log(f"📥 [{page_name}] Status: {resp.status_code} | HTML: {len(resp.text)} символов")
                
                if resp.status_code != 200:
                    continue
                
                html = resp.text
                html_clean = html.replace("\\\\/", "/").replace("\\/", "/")
                
                if all_posts:
                    # Все типы постов
                    for match in re.finditer(r'/posts/(pfbid[A-Za-z0-9]{20,}|\d{10,})', html_clean):
                        post_id = match.group(1)
                        urls.add(f"https://www.facebook.com/{page_name}/posts/{post_id}")
                    
                    for match in re.finditer(r'/videos/(\d{10,})', html_clean):
                        video_id = match.group(1)
                        urls.add(f"https://www.facebook.com/{page_name}/videos/{video_id}")
                    
                    for match in re.finditer(r'/reel/(\d{10,})', html_clean):
                        urls.add(f"https://www.facebook.com/reel/{match.group(1)}")
                    
                    for match in re.finditer(r'story_fbid=(\d{10,})', html_clean):
                        urls.add(f"https://www.facebook.com/{page_name}/posts/{match.group(1)}")
                    
                    for match in re.finditer(r'/photo/\?fbid=(\d{10,})', html_clean):
                        urls.add(f"https://www.facebook.com/photo/?fbid={match.group(1)}")
                else:
                    # Только Reels
                    patterns = [
                        r'/reel/(\d{10,})',
                        r'"video_id":"(\d{10,})"',
                        r'/videos/(\d{10,})',
                        r'watch/\?v=(\d{10,})',
                    ]
                    for pattern in patterns:
                        for match in re.finditer(pattern, html_clean):
                            urls.add(f"https://www.facebook.com/reel/{match.group(1)}")
                
                time.sleep(2)  # пауза между запросами
            except Exception as e:
                log(f"⚠️  [{page_name}] {url}: {e}")
                continue
        
        if all_posts:
            log(f"📊 [{page_name}] Найдено постов всех типов: {len(urls)}")
        else:
            log(f"🎬 [{page_name}] Найдено Reels: {len(urls)}")
        
        return list(urls)
    
    except Exception as e:
        log(f"❌ [{page_name}] Ошибка: {e}")
        return []

# ══════════════════════════════════════
#  MAIN
# ══════════════════════════════════════
def process_page(page, processed, daily):
    """Обработать одну страницу"""
    name = page["name"]
    
    # Проверяем дневной лимит
    today_count = get_today_count(daily, name)
    if today_count >= DAILY_LIMIT:
        log(f"⏸  [{name}] Дневной лимит достигнут ({today_count}/{DAILY_LIMIT})")
        return
    
    reels = fetch_reels(page["url"], name, page.get("all_posts", False))
    if not reels:
        return
    
    page_processed = processed.get(name, set())
    
    # Первый запуск — запоминаем все
    if not page_processed:
        page_processed.update(reels)
        processed[name] = page_processed
        save_processed(processed)
        log(f"📌 [{name}] Запомнено {len(reels)} Reels. Жду новые...")
        return
    
    new_reels = [url for url in reels if url not in page_processed]
    
    if not new_reels:
        log(f"🔍 [{name}] Нет новых Reels")
        return
    
    log(f"🆕 [{name}] Новых Reels: {len(new_reels)}")
    
    for reel_url in new_reels:
        # Проверяем дневной лимит перед каждым заказом
        today_count = get_today_count(daily, name)
        if today_count >= DAILY_LIMIT:
            log(f"⏸  [{name}] Дневной лимит достигнут ({today_count}/{DAILY_LIMIT}) — оставшиеся Reels пропускаю до завтра")
            break
        
        log(f"🆕 [{name}] {reel_url} ({today_count + 1}/{DAILY_LIMIT})")
        success = create_jap_order(reel_url, page["service"], page["qty_min"], page["qty_max"], name)
        
        if success:
            page_processed.add(reel_url)
            increment_daily_count(daily, name)
            time.sleep(2)
    
    processed[name] = page_processed
    save_processed(processed)

def main():
    log("🚀 Facebook Reels бот запущен (curl_cffi)!")
    log(f"📘 Страниц: {len(FB_PAGES)} | Лимит: {DAILY_LIMIT} заказов/день на страницу")
    for p in FB_PAGES:
        log(f"   • {p['name']} | Услуга: {p['service']} | {p['qty_min']}-{p['qty_max']}")
    check_balance()
    
    processed = load_processed()
    daily     = load_daily_count()
    
    # Первый запуск — запоминаем существующие Reels на всех страницах
    for page in FB_PAGES:
        if page["name"] not in processed:
            log(f"📌 [{page['name']}] Первый запуск — запоминаю существующие Reels...")
            process_page(page, processed, daily)
            time.sleep(5)
    
    while True:
        time.sleep(CHECK_INTERVAL)
        try:
            for page in FB_PAGES:
                process_page(page, processed, daily)
                time.sleep(5)
        except Exception as e:
            log(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
