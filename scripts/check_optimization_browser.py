"""Fresh-profile responsive checks; optional AI UI is mocked on localhost only."""
import argparse
import json
from pathlib import Path
import secrets
import uuid

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', default='http://127.0.0.1:5176')
    parser.add_argument('--api', default='http://127.0.0.1:8013')
    args = parser.parse_args()
    local = args.site == 'http://127.0.0.1:5176' and args.api == 'http://127.0.0.1:8013'
    output = ROOT / 'outputs/optimization' / ('local' if local else 'live')
    output.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1440,1100')
    options.add_argument('--disable-gpu')
    driver = webdriver.Edge(service=Service(str(ROOT / 'outputs/human3/webdriver-cache/msedgedriver/win64/154.0.4258.53/msedgedriver.exe')), options=options)
    wait = WebDriverWait(driver, 65)
    checks = []

    def shown(selector):
        return wait.until(lambda d: next((e for e in d.find_elements(By.CSS_SELECTOR, selector) if e.is_displayed()), None))

    def click(selector):
        wait.until(lambda d: not d.find_elements(By.CSS_SELECTOR, '.page-fade-enter-active, .page-fade-leave-active'))
        element = shown(selector)
        driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", element)
        element.click()

    def visit(path):
        driver.get(args.site + path)
        shown('main')
        wait.until(lambda d: not d.find_elements(By.CSS_SELECTOR, '.page-fade-enter-active, .page-fade-leave-active'))

    def width():
        assert driver.execute_script('return document.documentElement.scrollWidth <= window.innerWidth')

    try:
        summary = requests.get(args.api + '/api/site-summary', timeout=65).json()
        visit('/')
        wait.until(lambda d: [e.text for e in d.find_elements(By.CSS_SELECTOR, '.stat-grid strong')] == [str(summary[k]) for k in ['novels', 'posts', 'articles']])
        resources = driver.execute_script('return performance.getEntriesByType("resource").map(x=>x.name)')
        assert not any('CarbonEyeView-' in name or 'AdminView-' in name for name in resources)
        assert not any(name.endswith('/api/novels') or name.endswith('/api/articles') or name.endswith('/api/posts') for name in resources)
        width()
        driver.save_screenshot(str(output / 'home-desktop.png'))
        checks.extend(['home uses summary not full lists', 'charts and admin not loaded on home'])
        visit('/store')
        assert len(driver.find_elements(By.CSS_SELECTOR, '.store-card')) == 3
        assert '暂不交易' in shown('.store-notice').text
        shown('.store-filters button:nth-child(2)').click()
        assert len(driver.find_elements(By.CSS_SELECTOR, '.store-card')) == 1
        click('.store-card-bottom button')
        assert '授权范围' in shown('.store-detail').text
        assert not driver.find_elements(By.CSS_SELECTOR, 'input, form')
        driver.save_screenshot(str(output / 'store-desktop.png'))
        checks.extend(['store filter and details', 'store has no purchasing or redemption'])
        visit('/missing-page-test')
        assert '这里还没有内容' in shown('main').text
        assert '页面不存在' in driver.title
        checks.append('404 recovery')
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
        for path in ['/', '/store', '/human3', '/projects', '/login', '/missing-page-test', '/carbon-eye']:
            visit(path)
            width()
        visit('/store')
        assert not driver.find_element(By.CSS_SELECTOR, '#main-navigation').is_displayed()
        click('.menu-toggle')
        assert shown('.menu-toggle').get_attribute('aria-expanded') == 'true'
        click('#main-navigation a[href="/human3"]')
        shown('.human-welcome')
        assert not driver.find_element(By.CSS_SELECTOR, '#main-navigation').is_displayed()
        width()
        driver.save_screenshot(str(output / 'human3-mobile.png'))
        visit('/store')
        driver.save_screenshot(str(output / 'store-mobile.png'))
        checks.extend(['390px layouts on 7 pages', 'mobile menu expands and closes after navigation'])
        driver.execute_cdp_cmd('Emulation.clearDeviceMetricsOverride', {})
        visit('/human3')
        for _ in range(24):
            if driver.find_elements(By.CSS_SELECTOR, '.human-welcome'):
                click('.human-primary')
            click('.human-option:last-of-type')
            click('.human-question-footer .human-primary')
        shown('.human-report')
        assert len(driver.find_elements(By.CSS_SELECTOR, '.human-reflection ol li')) == 4
        assert '信息不足' in shown('.human-reflection').text
        wait.until(lambda d: '当前为免费的本地规则版' in d.find_element(By.CSS_SELECTOR, '.human-report').text)
        resources = driver.execute_script('return performance.getEntriesByType("resource").map(x=>x.name)')
        assert not any('/api/human3/reflect' in name for name in resources)
        driver.save_screenshot(str(output / 'report-desktop.png'))
        checks.extend(['adaptive follow-ups for unknown answers', 'no answer upload in rules mode'])
        if local:
            # Disposable user only, never executed against cloud accounts/databases.
            credentials = {'username': 'ai-ui-' + uuid.uuid4().hex[:10], 'password': secrets.token_urlsafe(24)}
            assert requests.post(args.api + '/api/auth/register', json=credentials, timeout=20).status_code == 200
            auth = requests.post(args.api + '/api/auth/login', json=credentials, timeout=20).json()
            driver.execute_script("localStorage.setItem('token', arguments[0]);localStorage.setItem('currentUser', JSON.stringify(arguments[1]));", auth['token'], auth['user'])
            visit('/human3')
            wait.until(lambda d: credentials['username'] in d.find_element(By.CSS_SELECTOR, '.status-strip').text)
            driver.execute_script("""
                const original = window.fetch;
                window.fetch = (url, options) => {
                  if (String(url).endsWith('/api/human3/ai-status')) return Promise.resolve(new Response(JSON.stringify({enabled:true,provider:'doubao'}), {headers:{'Content-Type':'application/json'}}));
                  if (String(url).endsWith('/api/human3/reflect')) {
                    window.testReflectionPayload = JSON.parse(options.body);
                    return Promise.resolve(new Response(JSON.stringify({content:'<script>bad()</script>模拟反思',disclaimer:'仅测试，不是实际模型输出'}), {headers:{'Content-Type':'application/json'}}));
                  }
                  return original(url, options);
                };
            """)
            click('.human-primary')
            for _ in range(24):
                click('.human-option:last-of-type')
                click('.human-question-footer .human-primary')
            textarea = shown('#human-reflection')
            panel = textarea.find_element(By.XPATH, '..')
            button = panel.find_element(By.CSS_SELECTOR, 'button')
            assert not button.is_enabled()
            textarea.send_keys('测试一个真实行动。')
            click('#human-reflection + .human-check input')
            assert button.is_enabled()
            click('.human-report-panel:has(#human-reflection) .human-primary')
            assert '<script>bad()</script>' in shown('.human-ai-result').text
            assert not driver.find_elements(By.CSS_SELECTOR, '.human-ai-result script')
            payload = driver.execute_script('return window.testReflectionPayload')
            assert payload['consent'] is True and len(payload['answers']) == 24
            click('.human-report-bottom button:nth-child(2)')
            assert not driver.find_elements(By.CSS_SELECTOR, '.human-ai-result')
            checks.extend(['mocked AI requires explicit consent', 'mocked model output rendered as text', 'changing answers clears AI result'])
        print(json.dumps({'status': 'passed', 'checks': checks, 'screenshots': str(output), 'actual_model_calls': 0, 'cloud_writes': False}, ensure_ascii=False))
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
