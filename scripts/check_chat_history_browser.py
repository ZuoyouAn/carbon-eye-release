"""Local-only history UI stress test. Mocked history; no production writes or model calls."""
import json
from pathlib import Path
import secrets
import time
import uuid
import requests
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
SITE = 'http://127.0.0.1:5176'
API = 'http://127.0.0.1:8013'


def main():
    credential = secrets.token_urlsafe(24)
    account = {'username': 'history-' + uuid.uuid4().hex[:8], 'password': credential}
    response = requests.post(API + '/api/auth/register', json=account, timeout=20)
    assert response.status_code == 200
    auth = requests.post(API + '/api/auth/login', json=account, timeout=20).json()
    output = ROOT / 'outputs/chat-polish' / uuid.uuid4().hex[:8]
    output.mkdir(parents=True, exist_ok=True)
    options = Options()
    for option in ['--headless=new', '--window-size=1440,1100', '--disable-gpu']:
        options.add_argument(option)
    driver = webdriver.Edge(service=Service(str(ROOT / 'outputs/human3/webdriver-cache/msedgedriver/win64/154.0.4258.53/msedgedriver.exe')), options=options)
    wait = WebDriverWait(driver, 30, ignored_exceptions=(StaleElementReferenceException,))
    checks = []
    sender = {'id': auth['user']['id'], 'username': auth['user']['username']}
    mock = """
      const originalFetch = window.fetch;
      window.__historyCount = 260; window.__historyCalls = 0; window.__retracted = 0;
      window.__hidden = false; window.__failHistory = false;
      Object.defineProperty(document, 'hidden', { configurable: true, get: () => window.__hidden });
      window.fetch = async (input, init) => {
        const url = new URL(typeof input === 'string' ? input : input.url, location.origin);
        if (url.origin === 'http://127.0.0.1:8013' && url.pathname === '/api/chat/rooms/public-lobby/messages' && (!init?.method || init.method === 'GET')) {
          window.__historyCalls++;
          if (window.__failHistory) throw new TypeError('simulated network failure');
          const before = Number(url.searchParams.get('before_id') || 0);
          const rows = Array.from({ length: window.__historyCount }, (_, i) => ({ id: i + 1, sender: SENDER, content: i + 1 === window.__retracted ? '' : 'history-row-' + (i + 1), is_deleted: i + 1 === window.__retracted, can_retract: false, created_at: new Date().toISOString() })).filter(row => !before || row.id < before);
          return new Response(JSON.stringify({ items: rows.slice(-50), has_more: rows.length > 50 }), { status: 200, headers: { 'Content-Type': 'application/json' } });
        }
        return originalFetch(input, init);
      };
    """.replace('SENDER', json.dumps(sender))
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': mock})

    def shown(selector):
        return wait.until(lambda d: next((e for e in d.find_elements(By.CSS_SELECTOR, selector) if e.is_displayed()), None))
    def click(element):
        wait.until(lambda d: not d.find_elements(By.CSS_SELECTOR, '.page-fade-enter-active, .page-fade-leave-active'))
        driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", element)
        element.click()
    def button(text):
        return wait.until(lambda d: next((e for e in d.find_elements(By.CSS_SELECTOR, 'button') if e.is_displayed() and e.text == text), None))
    def ids():
        return driver.execute_script('return [...document.querySelectorAll("[data-message-id]")].map(e=>Number(e.dataset.messageId))')
    def refresh():
        click(button('刷新'))
        wait.until(lambda d: not button('刷新').get_attribute('disabled'))

    try:
        driver.get(SITE + '/')
        shown('main')
        styles = driver.execute_script('return [...document.querySelectorAll("link[rel=stylesheet]")].map(e=>e.href)')
        assert len(styles) == 1 and not any('AdminView' in url or 'el-pagination' in url for url in styles)
        assert 'el-table__body-wrapper' not in requests.get(styles[0], timeout=20).text
        checks.append('home does not load admin table or pagination styles')
        driver.execute_script("localStorage.setItem('token',arguments[0]); localStorage.setItem('currentUser',JSON.stringify(arguments[1]))", auth['token'], auth['user'])
        driver.get(SITE + '/chat')
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '[data-message-id]')) == 50)
        wait.until(lambda d: not button('刷新').get_attribute('disabled'))
        driver.execute_script('document.querySelector(".chat-messages").scrollTop=0')
        initial = driver.execute_script('const p=document.querySelector(".chat-messages");const r=document.querySelector(arguments[0]);return r.getBoundingClientRect().top-p.getBoundingClientRect().top', '[data-message-id="211"]')
        click(button('查看更早消息'))
        wait.until(lambda d: len(ids()) == 100)
        after = driver.execute_script('const p=document.querySelector(".chat-messages");const r=document.querySelector(arguments[0]);return r.getBoundingClientRect().top-p.getBoundingClientRect().top', '[data-message-id="211"]')
        assert abs(initial - after) < 3
        checks.append('older history prepending preserves reading position')
        previous_ids = ids()
        previous_scroll = driver.execute_script('return document.querySelector(".chat-messages").scrollTop')
        driver.execute_script('window.__historyCount=264;window.__retracted=250')
        refresh()
        assert ids() == previous_ids
        assert abs(driver.execute_script('return document.querySelector(".chat-messages").scrollTop') - previous_scroll) < 3
        assert '有新消息' in shown('.chat-history-bar').text
        assert '消息已撤回' in shown('[data-message-id="250"]').text
        checks.extend(['poll preserves loaded history and scroll position', 'new messages have explicit return-to-latest hint', 'overlapping retraction updates during history reading'])
        for expected in [150, 200, 200, 200]:
            click(button('查看更早消息'))
            wait.until(lambda d: len(ids()) == expected and not shown('.chat-messages').get_attribute('aria-busy') == 'true')
        assert ids() == list(range(1, 201))
        checks.append('pagination remains usable beyond 200 messages with bounded rendering')
        driver.save_screenshot(str(output / 'history-desktop.png'))
        click(button('回到最新消息 ↓'))
        wait.until(lambda d: ids() == list(range(215, 265)))
        wait.until(lambda d: not d.find_elements(By.CSS_SELECTOR, '.chat-history-bar'))
        checks.append('return-to-latest clears history mode and reaches newest message')
        driver.execute_script("window.__hidden=true;document.dispatchEvent(new Event('visibilitychange'))")
        calls = driver.execute_script('return window.__historyCalls')
        time.sleep(13)
        assert driver.execute_script('return window.__historyCalls') == calls
        driver.execute_script("window.__hidden=false;document.dispatchEvent(new Event('visibilitychange'))")
        wait.until(lambda d: d.execute_script('return window.__historyCalls') > calls)
        checks.append('hidden page stops polling and visible page resumes')
        wait.until(lambda d: not button('刷新').get_attribute('disabled'))
        driver.execute_script('window.__failHistory=true')
        refresh()
        assert '降低频率' in shown('.chat-sync').text
        calls = driver.execute_script('return window.__historyCalls')
        time.sleep(13)
        assert driver.execute_script('return window.__historyCalls') == calls
        driver.execute_script('window.__failHistory=false')
        refresh()
        assert '降低频率' not in shown('.chat-sync').text
        checks.append('failed polling backs off and manual refresh recovers')
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
        assert driver.execute_script('return document.documentElement.scrollWidth <= window.innerWidth')
        driver.save_screenshot(str(output / 'history-mobile.png'))
        checks.append('history and new-message control fit mobile viewport')
        report = {'status': 'passed', 'checks': checks, 'cloud_writes': False, 'mocked_history': True, 'screenshots': str(output)}
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
