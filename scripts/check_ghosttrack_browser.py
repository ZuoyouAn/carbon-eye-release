"""Check the installed GhostTrack page with the workstation's existing Edge driver."""
import argparse
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--site', default='http://127.0.0.1:5178')
args = parser.parse_args()
OUT = ROOT / 'outputs/ghosttrack'
OUT.mkdir(parents=True, exist_ok=True)
driver_path = ROOT / 'outputs/human3/webdriver-cache/msedgedriver/win64/154.0.4258.53/msedgedriver.exe'
options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=1440,1100')
driver = webdriver.Edge(service=Service(str(driver_path)), options=options)
wait = WebDriverWait(driver, 75)
checks = []

def click(selector):
    item = driver.find_element('css selector', selector)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'})", item)
    item.click()

def enter_frame():
    wait.until(lambda d: d.find_elements('css selector', 'iframe.ghosttrack-frame'))
    driver.switch_to.frame(driver.find_element('css selector', 'iframe.ghosttrack-frame'))
    wait.until(lambda d: d.find_element('id', 'health').text == '查询服务已连接')

try:
    driver.get(args.site + '/ghosttrack')
    enter_frame()
    assert driver.execute_script('return document.documentElement.scrollWidth <= innerWidth')
    assert driver.find_element('id', 'retry-health').is_displayed()
    driver.save_screenshot(str(OUT / 'desktop.png'))
    checks.append('route, iframe, health, retry button, desktop layout')
    click('[data-kind=phone]')
    driver.find_element('id', 'value').send_keys('+1 202 555 0123')
    click('#submit')
    wait.until(lambda d: d.find_element('id', 'export').is_displayed())
    assert '+12025550123' in driver.find_element('id', 'result').text
    assert '机主' in driver.find_element('id', 'result').text
    checks.append('real offline phone endpoint and privacy boundaries')
    click('[data-kind=ip]')
    driver.find_element('id', 'value').send_keys('127.0.0.1')
    click('#submit')
    wait.until(lambda d: d.find_element('id', 'error').is_displayed())
    assert '公网' in driver.find_element('id', 'error').text
    assert not driver.find_element('id', 'export').is_displayed()
    checks.append('private address rejected and stale result cleared')
    click('[data-kind=username]')
    driver.find_element('id', 'value').send_keys('../admin')
    click('#submit')
    wait.until(lambda d: d.find_element('id', 'error').is_displayed())
    assert '用户名' in driver.find_element('id', 'error').text
    click('#clear')
    assert driver.find_element('id', 'value').get_attribute('value') == ''
    checks.append('username injection rejected and clear works')
    driver.switch_to.default_content()
    driver.set_window_size(390, 844)
    driver.refresh()
    wait.until(lambda d: d.find_elements('css selector', 'iframe.ghosttrack-frame'))
    assert driver.execute_script('return document.documentElement.scrollWidth <= innerWidth')
    enter_frame()
    assert driver.execute_script('return document.documentElement.scrollWidth <= innerWidth')
    driver.save_screenshot(str(OUT / 'mobile.png'))
    checks.append('mobile parent and iframe without horizontal overflow')
    driver.switch_to.default_content()
    driver.get(args.site + '/')
    wait.until(lambda d: d.find_elements('css selector', 'a.feature-card[href="/ghosttrack"]'))
    driver.get(args.site + '/projects')
    wait.until(lambda d: d.find_elements('css selector', 'a.text-button[href="/ghosttrack"]'))
    assert driver.find_elements('css selector', '.nav-more a[href="/ghosttrack"]')
    checks.append('home, projects, more navigation')
    report = {'status': 'passed', 'site': args.site, 'checks': checks}
    filename = 'live-browser.json' if args.site.startswith('https://') else 'local-browser.json'
    (OUT / filename).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
finally:
    driver.quit()
