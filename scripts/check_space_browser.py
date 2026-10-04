"""Two independent browser profiles on disposable localhost; --live does not write cloud data."""
import argparse
import json
from pathlib import Path
import secrets
import uuid

from PIL import Image
import requests
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    site = 'https://carbon-eye-sip.netlify.app' if args.live else 'http://127.0.0.1:5176'
    api = 'https://personal-website-carbon-eye-api.onrender.com' if args.live else 'http://127.0.0.1:8013'
    output = ROOT / 'outputs/space' / ('live' if args.live else 'local') / uuid.uuid4().hex[:8]
    output.mkdir(parents=True, exist_ok=True)
    checks, drivers = [], []

    def browser():
        options = Options()
        for item in ['--headless=new', '--window-size=1440,1100', '--disable-gpu']:
            options.add_argument(item)
        driver = webdriver.Edge(service=Service(str(ROOT / 'outputs/human3/webdriver-cache/msedgedriver/win64/154.0.4258.53/msedgedriver.exe')), options=options)
        driver.execute_cdp_cmd('Browser.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': str(output)})
        drivers.append(driver)
        return driver

    def wait(driver, predicate):
        return WebDriverWait(driver, 65, ignored_exceptions=(StaleElementReferenceException,)).until(predicate)

    def shown(driver, selector):
        return wait(driver, lambda d: next((e for e in d.find_elements(By.CSS_SELECTOR, selector) if e.is_displayed()), None))

    def click(driver, element):
        wait(driver, lambda d: not d.find_elements(By.CSS_SELECTOR, '.page-fade-enter-active, .page-fade-leave-active'))
        driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", element)
        element.click()

    def button(driver, text, selector='button'):
        return wait(driver, lambda d: next((e for e in d.find_elements(By.CSS_SELECTOR, selector) if e.is_displayed() and e.text.strip() == text), None))

    def visit(driver, path):
        driver.get(site + path)
        shown(driver, 'main')
        wait(driver, lambda d: not d.find_elements(By.CSS_SELECTOR, '.page-fade-enter-active, .page-fade-leave-active'))

    def responsive(driver):
        assert driver.execute_script('return document.documentElement.scrollWidth <= window.innerWidth'), 'horizontal overflow'

    def sign_in(driver, name, credential):
        visit(driver, '/login')
        shown(driver, 'input[autocomplete=username]').send_keys(name)
        shown(driver, 'input[autocomplete=current-password]').send_keys(credential)
        click(driver, shown(driver, 'form button[type=submit]'))
        wait(driver, lambda d: '/login' not in d.current_url and name in shown(d, '.status-strip').text)

    def refresh_chat(driver):
        click(driver, button(driver, '刷新'))
        wait(driver, lambda d: not button(d, '刷新').get_attribute('disabled'))

    def select_room(driver, name):
        room = wait(driver, lambda d: next((e for e in d.find_elements(By.CSS_SELECTOR, '.room-button') if e.find_element(By.CSS_SELECTOR, 'strong').text == name), None))
        click(driver, room)

    def send_message(driver, text):
        wait(driver, lambda d: shown(d, '#chat-content').is_enabled())
        shown(driver, '#chat-content').send_keys(text)
        click(driver, button(driver, '发送消息'))
        wait(driver, lambda d: text in shown(d, '.chat-messages').text)

    def search(driver, name):
        field = shown(driver, '#chat-user-search'); field.clear(); field.send_keys(name)
        click(driver, button(driver, '查找'))
        wait(driver, lambda d: name in shown(d, '.chat-person').text)

    try:
        a = browser()
        for path in ['/', '/projects', '/roadmap', '/changelog', '/timeline']:
            visit(a, path)
            assert '个人网站' not in shown(a, 'body').text and '左右的Space' in a.title
            responsive(a)
        checks.append('Space branding on five public routes')
        visit(a, '/chat')
        wait(a, lambda d: '/login' in d.current_url)
        assert requests.get(api + '/api/chat/rooms', timeout=65).status_code == 401
        checks.append('guest chat redirects and API requires authentication')

        a.execute_cdp_cmd('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
        a.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': "const originalScroll=window.scrollTo;window.__scrollCalls=[];window.scrollTo=function(...args){window.__scrollCalls.push(args[0]);return originalScroll.apply(window,args)}"})
        visit(a, '/wasteland')
        assert shown(a, '.setup-form .game-primary').get_attribute('disabled')
        click(a, shown(a, '.talent-card:nth-child(3)')); click(a, shown(a, '.talent-card:nth-child(6)'))
        assert len(a.find_elements(By.CSS_SELECTOR, '.talent-card[aria-pressed=true]')) == 2
        click(a, shown(a, '.talent-card:nth-child(1)'))
        assert len(a.find_elements(By.CSS_SELECTOR, '.talent-card[aria-pressed=true]')) == 2
        assert all(e.get_attribute('disabled') for e in a.find_elements(By.CSS_SELECTOR, '.attribute-controls button:last-child'))
        a.save_screenshot(str(output / 'game-setup-desktop.png'))
        click(a, shown(a, '.setup-form .game-primary'))
        shown(a, '.game-status')
        assert a.execute_script("return window.__scrollCalls.some(call=>call?.behavior==='instant')")
        assert a.execute_script("return getComputedStyle(document.documentElement).scrollBehavior") == 'auto'
        checks.append('game scroll and page transitions respect reduced-motion preference')
        assert a.execute_script("return localStorage.getItem('space-wasteland-v1')") is None
        click(a, shown(a, '.event-choices button:not(:disabled)'))
        wait(a, lambda d: len(d.find_elements(By.CSS_SELECTOR, '.game-journal li')) == 1)
        click(a, shown(a, '.game-session input[type=checkbox]'))
        click(a, shown(a, '.event-choices button:not(:disabled)'))
        wait(a, lambda d: len(d.find_elements(By.CSS_SELECTOR, '.game-journal li')) == 2)
        title = shown(a, '.game-event h2').text
        a.refresh(); click(a, button(a, '继续本机存档 →'))
        assert shown(a, '.game-event h2').text == title
        assert len(a.find_elements(By.CSS_SELECTOR, '.game-journal li')) == 2
        assert shown(a, '.day-marker strong').text == '03'
        checks.extend(['talent and attribute gates', 'no default game persistence', 'opt-in save resumes exact day and event'])
        for count in range(2, 30):
            if not a.find_elements(By.CSS_SELECTOR, '.event-choices button'): break
            click(a, shown(a, '.event-choices button:not(:disabled)'))
            wait(a, lambda d: len(d.find_elements(By.CSS_SELECTOR, '.game-journal li')) == count + 1)
        assert 'ENDING /' in shown(a, '.game-event').text
        a.save_screenshot(str(output / 'game-ending-desktop.png'))
        click(a, button(a, '下载生存记录'))
        wait(a, lambda d: bool(list(output.glob('*.md'))))
        exported = next(output.glob('*.md')).read_text(encoding='utf-8')
        assert '生存记录' in exported and '原创虚构' in exported
        click(a, button(a, '清除存档')); a.switch_to.alert.accept()
        wait(a, lambda d: d.execute_script("return localStorage.getItem('space-wasteland-v1')") is None)
        checks.extend(['playable journey reaches ending', 'Markdown journal download', 'local save deletion'])
        a.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
        responsive(a); a.save_screenshot(str(output / 'game-ending-mobile.png'))
        visit(a, '/wasteland'); responsive(a)
        a.save_screenshot(str(output / 'game-setup-mobile.png'))
        checks.append('game setup and gameplay mobile layout')
        a.execute_script("localStorage.setItem('space-wasteland-v1', '{invalid')")
        a.refresh()
        assert '无法验证' in shown(a, '.game-notice').text
        click(a, button(a, '清除本机存档')); a.switch_to.alert.accept()
        wait(a, lambda d: d.execute_script("return localStorage.getItem('space-wasteland-v1')") is None)
        checks.append('corrupt game save can be cleared without starting a game')
        a.execute_cdp_cmd('Emulation.clearDeviceMetricsOverride', {})

        if not args.live:
            credential = secrets.token_urlsafe(24)
            names = ['sociala-' + uuid.uuid4().hex[:8], 'socialb-' + uuid.uuid4().hex[:8]]
            users = []
            for name in names:
                result = requests.post(api + '/api/auth/register', json={'username': name, 'password': credential}, timeout=20)
                assert result.status_code == 200
                users.append(result.json()['user'])
            local_admin_credential = '-'.join(['local', 'browser', 'test', 'only', 'password'])
            admin = requests.post(api + '/api/auth/login', json={'username': 'admin', 'password': local_admin_credential}, timeout=20)
            assert admin.status_code == 200
            admin_headers = {'Authorization': 'Bearer ' + admin.json()['token']}
            elevated = requests.put(api + f'/api/admin/users/{users[0]["id"]}/role', headers=admin_headers, json={'role': 'elevated', 'admin_password': local_admin_credential}, timeout=20)
            assert elevated.status_code == 200
            b = browser()
            sign_in(a, names[0], credential); sign_in(b, names[1], credential)
            visit(a, '/profile')
            avatar_file = output / 'test-avatar.png'
            Image.new('RGB', (300, 200), '#88cba7').save(avatar_file)
            a.find_element(By.CSS_SELECTOR, '.avatar-picker input[type=file]').send_keys(str(avatar_file))
            shown(a, '.avatar-preview')
            click(a, button(a, '保存头像'))
            wait(a, lambda d: '已保存' in shown(d, '.avatar-settings').text)
            a.refresh()
            wait(a, lambda d: d.execute_script('return [...document.querySelectorAll(".avatar-settings .user-avatar img")].some(i=>i.complete&&i.naturalWidth===128)'))
            assert requests.get(api + f'/api/users/{users[0]["id"]}/avatar', timeout=20).headers['content-type'] == 'image/webp'
            a.save_screenshot(str(output / 'profile-avatar-desktop.png'))
            checks.append('real file upload persists avatar across reload')

            visit(a, '/chat'); visit(b, '/chat')
            shown(a, '.chat-composer'); shown(b, '.chat-composer')
            text = '大厅验收-' + uuid.uuid4().hex[:6]
            send_message(a, text); refresh_chat(b)
            wait(b, lambda d: text in shown(d, '.chat-messages').text)
            checks.append('two independent accounts share persistent lobby')
            public_draft = '本次页面里暂存的未发送草稿'
            shown(a, '#chat-content').send_keys(public_draft)
            search(a, names[1]); click(a, button(a, '私聊', '.chat-person button'))
            wait(a, lambda d: shown(d, '.conversation-heading h2').text == names[1])
            assert not shown(a, '#chat-content').is_enabled()
            assert '等待对方接受' in shown(a, '.chat-composer').text
            checks.append('pending direct room disables composer with consent hint')
            select_room(a, 'Space公共大厅')
            wait(a, lambda d: shown(d, '#chat-content').get_attribute('value') == public_draft)
            select_room(a, names[1])
            wait(a, lambda d: not shown(d, '#chat-content').is_enabled())
            checks.append('room switching preserves unsent draft in memory only')
            refresh_chat(b); select_room(b, names[0])
            shown(b, '.chat-invitation')
            assert not b.find_elements(By.CSS_SELECTOR, '.chat-messages')
            click(b, button(b, '接受邀请')); shown(b, '.chat-composer')
            refresh_chat(a)
            private_text = '<img src=x onerror=alert(1)> 私聊只是文本'
            send_message(b, private_text); refresh_chat(a)
            wait(a, lambda d: private_text in shown(d, '.chat-messages').text)
            assert not a.find_elements(By.CSS_SELECTOR, '.chat-message p img')
            b.save_screenshot(str(output / 'private-chat-desktop.png'))
            click(b, shown(b, '.chat-retract')); b.switch_to.alert.accept()
            wait(b, lambda d: '消息已撤回' in shown(d, '.chat-messages').text)
            refresh_chat(a); wait(a, lambda d: '消息已撤回' in shown(d, '.chat-messages').text)
            checks.extend(['private invitation and recipient acceptance UI', 'private text does not render HTML', 'retraction propagates to other account'])
            group = '夜航小队'
            shown(a, '#chat-group-name').send_keys(group); click(a, button(a, '创建并进入'))
            wait(a, lambda d: shown(d, '.conversation-heading h2').text == group)
            search(a, names[1]); click(a, button(a, '邀请', '.chat-person button'))
            wait(a, lambda d: '邀请已发出' in shown(d, '.message').text)
            refresh_chat(b); select_room(b, group); click(b, button(b, '接受邀请'))
            shown(b, '.chat-composer')
            refresh_chat(a)
            group_text = '小群验收-' + uuid.uuid4().hex[:6]
            send_message(a, group_text); refresh_chat(b)
            wait(b, lambda d: group_text in shown(d, '.chat-messages').text)
            a.save_screenshot(str(output / 'group-chat-desktop.png'))
            checks.append('elevated group creation, invitation and shared group messages')
            for path in ['/profile', '/chat']:
                a.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
                visit(a, path); responsive(a)
                a.save_screenshot(str(output / (path.strip('/') + '-mobile.png')))
            checks.append('avatar profile and chat mobile layout')
        report = {'environment': 'live-read-only' if args.live else 'localhost-disposable', 'passed': len(checks), 'checks': checks, 'screenshots': str(output)}
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))
    finally:
        for driver in drivers: driver.quit()


if __name__ == '__main__':
    main()
