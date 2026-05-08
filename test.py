"""
Тестовый бот для Facebook Reels — проверяем 3 подхода:
1. curl_cffi (TLS fingerprint имитация)
2. cloudscraper (обход Cloudflare/anti-bot)
3. Page Plugin виджет (iframe от Facebook)
"""
import os
import re
import requests
from datetime import datetime

FB_PAGE_ID = "100081997113052"

# Cookies (последние)
C_USER = "61553351803414"
XS     = "23%3AUcW9QDH7Lw4OMA%3A2%3A1777366320%3A-1%3A-1%3A%3AAcxV4doD641eN1HEAQNfnkX0cE357pxRh9ixF-wCuA"
DATR   = "gvGqaR00HB8BBQCtWvA_ZrBw"
FR     = "1BiHkrekV5y5wC9M4.AWcjA0M_D1BFpG4ArVdD9DEHJz1hf_Cp4e633bJFekyBL_WG64E.Bp8HUz..AAA.0.0.Bp8HUz.AWd2xaqh1GaCzn5odyasmAo3ovQ"
SB     = "hfGqaZIWmBX2PQV9iqh9Tr1V"

COOKIES_STR = f"c_user={C_USER}; xs={XS}; datr={DATR}; fr={FR}; sb={SB}"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def find_reels(html):
    """Ищем Reels в HTML"""
    urls = set()
    
    # Убираем экранирование слешей
    html_clean = html.replace("\\\\/", "/").replace("\\/", "/")
    
    patterns = [
        r'/reel/(\d{10,})',
        r'"video_id":"(\d{10,})"',
        r'/videos/(\d{10,})',
        r'watch/\?v=(\d{10,})',
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, html_clean):
            urls.add(f"https://www.facebook.com/reel/{match.group(1)}")
    
    return list(urls)


# ═══════════════════════════════════════
# ПОДХОД 1: curl_cffi (TLS impersonation)
# ═══════════════════════════════════════
def test_curl_cffi():
    log("=" * 50)
    log("🧪 ТЕСТ 1: curl_cffi (TLS impersonation)")
    log("=" * 50)
    try:
        from curl_cffi import requests as curl_requests
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Cookie": COOKIES_STR,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        
        urls_to_try = [
            f"https://www.facebook.com/{FB_PAGE_ID}/reels",
            f"https://m.facebook.com/{FB_PAGE_ID}/reels",
            f"https://m.facebook.com/profile.php?id={FB_PAGE_ID}&sk=reels",
        ]
        
        for url in urls_to_try:
            log(f"📡 GET {url}")
            try:
                resp = curl_requests.get(url, headers=headers, impersonate="chrome120", timeout=20)
                log(f"   Status: {resp.status_code} | HTML: {len(resp.text)} символов")
                
                reels = find_reels(resp.text)
                log(f"   🎬 Найдено Reels: {len(reels)}")
                if reels:
                    for r in reels[:3]:
                        log(f"      → {r}")
                    return True
            except Exception as e:
                log(f"   ❌ {e}")
        
        return False
    except ImportError:
        log("❌ curl_cffi не установлен. pip install curl-cffi")
        return False
    except Exception as e:
        log(f"❌ Ошибка: {e}")
        return False


# ═══════════════════════════════════════
# ПОДХОД 2: cloudscraper
# ═══════════════════════════════════════
def test_cloudscraper():
    log("=" * 50)
    log("🧪 ТЕСТ 2: cloudscraper")
    log("=" * 50)
    try:
        import cloudscraper
        
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False}
        )
        
        headers = {"Cookie": COOKIES_STR}
        
        urls_to_try = [
            f"https://www.facebook.com/{FB_PAGE_ID}/reels",
            f"https://m.facebook.com/{FB_PAGE_ID}/reels",
        ]
        
        for url in urls_to_try:
            log(f"📡 GET {url}")
            try:
                resp = scraper.get(url, headers=headers, timeout=20)
                log(f"   Status: {resp.status_code} | HTML: {len(resp.text)} символов")
                
                reels = find_reels(resp.text)
                log(f"   🎬 Найдено Reels: {len(reels)}")
                if reels:
                    for r in reels[:3]:
                        log(f"      → {r}")
                    return True
            except Exception as e:
                log(f"   ❌ {e}")
        
        return False
    except ImportError:
        log("❌ cloudscraper не установлен. pip install cloudscraper")
        return False
    except Exception as e:
        log(f"❌ Ошибка: {e}")
        return False


# ═══════════════════════════════════════
# ПОДХОД 3: Page Plugin виджет
# ═══════════════════════════════════════
def test_page_plugin():
    log("=" * 50)
    log("🧪 ТЕСТ 3: Page Plugin виджет (iframe Facebook)")
    log("=" * 50)
    try:
        # Page Plugin URL — публичный виджет страницы
        href = f"https://www.facebook.com/{FB_PAGE_ID}"
        plugin_urls = [
            f"https://www.facebook.com/plugins/page.php?href={requests.utils.quote(href)}&tabs=timeline&width=500&height=700&hide_cover=false&show_facepile=true",
            f"https://www.facebook.com/plugins/page.php?href={requests.utils.quote(href)}&tabs=timeline",
            f"https://www.facebook.com/plugins/feed.php?href={requests.utils.quote(href)}",
        ]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        
        for url in plugin_urls:
            log(f"📡 GET {url[:80]}...")
            try:
                resp = requests.get(url, headers=headers, timeout=20)
                log(f"   Status: {resp.status_code} | HTML: {len(resp.text)} символов")
                
                reels = find_reels(resp.text)
                log(f"   🎬 Найдено Reels: {len(reels)}")
                if reels:
                    for r in reels[:3]:
                        log(f"      → {r}")
                    return True
                
                # Также ищем посты вообще
                story_ids = re.findall(r'/posts/(\d{10,})', resp.text)
                log(f"   📝 Найдено постов: {len(set(story_ids))}")
            except Exception as e:
                log(f"   ❌ {e}")
        
        return False
    except Exception as e:
        log(f"❌ Ошибка: {e}")
        return False


def main():
    log("🚀 Тестирую 3 подхода для Facebook Reels")
    log(f"📘 Страница: {FB_PAGE_ID}\n")
    
    results = {}
    results["curl_cffi"]    = test_curl_cffi()
    log("")
    results["cloudscraper"] = test_cloudscraper()
    log("")
    results["page_plugin"]  = test_page_plugin()
    
    log("\n" + "=" * 50)
    log("📊 РЕЗУЛЬТАТЫ:")
    log("=" * 50)
    for name, success in results.items():
        emoji = "✅" if success else "❌"
        log(f"{emoji} {name}: {'РАБОТАЕТ' if success else 'не работает'}")

if __name__ == "__main__":
    main()
