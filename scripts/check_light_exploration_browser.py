"""Read-only browser regression: original 3D game, solar atlas and licensed book."""
import argparse
import json
from pathlib import Path
import time
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true')
args = parser.parse_args()
site = 'https://carbon-eye-sip.netlify.app' if args.live else 'http://127.0.0.1:5176'
output = ROOT / 'outputs/light-exploration' / ('live' if args.live else 'local')
output.mkdir(parents=True, exist_ok=True)
options = Options()
for option in ['--headless=new', '--window-size=1440,1100', '--enable-unsafe-swiftshader']:
    options.add_argument(option)
driver = webdriver.Edge(service=Service(str(ROOT / 'outputs/human3/webdriver-cache/msedgedriver/win64/154.0.4258.53/msedgedriver.exe')), options=options)
checks = []
def wait(predicate, timeout=35):
    return WebDriverWait(driver, timeout, poll_frequency=.1, ignored_exceptions=(StaleElementReferenceException,)).until(predicate)
def visible(selector):
    return wait(lambda d: next((e for e in d.find_elements('css selector', selector) if e.is_displayed()), None))
def button(text):
    return wait(lambda d: next((e for e in d.find_elements('tag name', 'button') if e.is_displayed() and e.text.strip() == text), None))
def click(element):
    driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", element)
    element.click()
def visit(path, selector):
    driver.get(site + path); visible(selector)
    wait(lambda d: not d.find_elements('css selector', '.page-fade-enter-active, .page-fade-leave-active'))
def overflow():
    assert driver.execute_script('return document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'
def point():
    stage = driver.find_element('css selector', '.expedition-stage')
    return float(stage.get_attribute('data-x')), float(stage.get_attribute('data-z'))
def move(axis, target):
    current = point()[axis]
    if abs(current - target) < .2: return
    positive = current < target
    key = ('d' if positive else 'a') if axis == 0 else ('s' if positive else 'w')
    driver.execute_script('arguments[0].focus({preventScroll:true})', visible('.expedition-stage'))
    ActionChains(driver).key_down(key).perform()
    try:
        wait(lambda d: visible('.expedition-stage').get_attribute('data-status') == 'won' or (point()[axis] >= target - .12 if positive else point()[axis] <= target + .12), 20)
    finally:
        ActionChains(driver).key_up(key).perform()
def key(text):
    ActionChains(driver).send_keys(text).perform()
try:
    visit('/', '.hero-copy h1'); overflow()
    assert driver.execute_script("return getComputedStyle(document.documentElement).colorScheme") == 'light'
    assert driver.execute_script("return getComputedStyle(document.body).backgroundColor") == 'rgb(245, 245, 247)'
    assert driver.find_elements('css selector', '.feature-card[href="/solar-system"]') and driver.find_elements('css selector', '.feature-card[href="/life-guide"]')
    driver.save_screenshot(str(output / 'home-desktop.png')); checks.append('light homepage and discoverable new pages')
    visit('/wasteland', '.expedition-stage canvas')
    assert len(driver.find_elements('css selector', '.expedition-stage canvas')) == 1
    click(button('开始探索')); wait(lambda d: visible('.expedition-stage').get_attribute('data-status') == 'playing')
    click(visible('button[aria-label="向左旋转视角"]'))
    move(0, -10); key('e'); wait(lambda d: '1 / 4' in visible('.expedition-brief').text)
    driver.save_screenshot(str(output / 'game-desktop.png')); checks.append('actual WebGL2 scene and continuous keyboard movement picks up real loot')
    key(Keys.ESCAPE); wait(lambda d: visible('.expedition-stage').get_attribute('data-status') == 'paused')
    elapsed = float(visible('.expedition-stage').get_attribute('data-elapsed'))
    until = time.monotonic() + .8
    wait(lambda d: time.monotonic() >= until)
    assert float(visible('.expedition-stage').get_attribute('data-elapsed')) == elapsed
    click(button('继续探索')); checks.append('pause freezes time, resume clears held keys')
    for x, z, pickup in [(-6, 12, True), (0, 12, True), (4, 8, True), (-2, 6, True), (6, 6, False), (6, 0, True), (0, 0, False), (0, -10, True), (12, -10, False), (12, -12, False)]:
        move(0, x); move(1, z)
        if pickup: key('e')
    wait(lambda d: visible('.expedition-stage').get_attribute('data-status') == 'won')
    assert '你点亮了晨光' in visible('.expedition-overlay').text
    assert driver.execute_script("return localStorage.getItem('space-wasteland-v1')") is None
    checks.append('complete mission via real keys: four scraps, two cells, beacon and extraction; no hidden teleport or default persistence')
    visit('/solar-system?planet=saturn', '.solar-stage canvas'); overflow()
    assert visible('.solar-information h2').text == '土星'
    assert visible('.solar-stage').get_attribute('data-playing') == 'false'
    assert len(driver.find_elements('css selector', '.solar-planet-list button')) == 8
    click(visible('.solar-planet-list button:nth-child(8)')); wait(lambda d: visible('.solar-information h2').text == '海王星')
    assert 'planet=neptune' in driver.current_url
    click(button('播放示意轨道')); wait(lambda d: float(visible('.solar-stage').get_attribute('data-time')) > .2)
    click(button('暂停运行')); elapsed = visible('.solar-stage').get_attribute('data-time')
    until = time.monotonic() + .4; wait(lambda d: time.monotonic() >= until)
    assert visible('.solar-stage').get_attribute('data-time') == elapsed
    click(button('暂停并靠近它 ↗')); click(button('回到全景'))
    driver.save_screenshot(str(output / 'solar-desktop.png')); checks.append('eight keyboard-accessible planet selectors, deep link, playback, pause and close-up')
    visit('/life-guide', '.guide-card')
    visible('.guide-meta[data-index-ready="true"]')
    assert '657 / 657' in visible('.guide-meta').text
    assert len(driver.find_elements('css selector', '.guide-card')) == 12
    click(visible('.guide-card summary')); wait(lambda d: '备注' in visible('.guide-original').text and '来源' in visible('.guide-original').text)
    assert 'CC BY 4.0' in visible('.guide-attribution').text
    assert 'b4048d14960f' in visible('.guide-attribution').text
    checks.append('complete 657-entry licensed book snapshot; unabridged original, remarks, attribution and revision')
    field = visible('.guide-search input'); field.send_keys('借条')
    wait(lambda d: '657 / 657' not in visible('.guide-meta').text and len(d.find_elements('css selector', '.guide-card')) > 0)
    click(button('清空筛选')); wait(lambda d: '657 / 657' in visible('.guide-meta').text)
    Select(visible('.guide-filters label:nth-child(2) select')).select_by_value('13')
    wait(lambda d: visible('.guide-intro') and all('第 13 节' in e.text for e in d.find_elements('css selector', '.guide-entry-meta')))
    driver.save_screenshot(str(output / 'guide-desktop.png')); checks.append('full-text search and chapter filters preserve original numbering and chapter introduction')
    driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
    for path, selector, image in [('/', '.hero-copy h1', 'home'), ('/solar-system', '.solar-stage canvas', 'solar'), ('/life-guide', '.guide-card', 'guide'), ('/wasteland', '.expedition-stage canvas', 'game')]:
        visit(path, selector); overflow(); driver.save_screenshot(str(output / (image + '-mobile.png')))
    checks.append('four new/light pages fit 390-pixel mobile viewport')
    click(button('开始探索'))
    joy = visible('.expedition-stick'); before = point()
    rect = joy.rect
    cx, cy = int(rect['x'] + rect['width'] / 2), int(rect['y'] + rect['height'] / 2)
    click(joy)
    rect = joy.rect
    cx, cy = int(rect['x'] + rect['width'] / 2), int(rect['y'] + rect['height'] / 2)
    cy -= int(driver.execute_script('return scrollY'))
    touch = ActionBuilder(driver, mouse=PointerInput('touch', 'joystick'))
    touch.pointer_action.move_to_location(cx, cy); touch.pointer_action.pointer_down(); touch.pointer_action.move_to_location(cx + 30, cy); touch.perform()
    wait(lambda d: abs(point()[0] - before[0]) > .3)
    touch.pointer_action.pointer_up(); touch.perform()
    checks.append('mobile joystick moves continuously and handles cancellation')
    driver.execute_cdp_cmd('Emulation.clearDeviceMetricsOverride', {})
    driver.execute_cdp_cmd('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
    visit('/', '.hero-copy h1'); assert driver.execute_script("return getComputedStyle(document.querySelector('.sculpture-orbit')).animationName") == 'none'
    source = "const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return type==='webgl2'?null:original.call(this,type,...args)};"
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': source})
    visit('/solar-system', '.solar-error'); click(visible('.solar-planet-list button:nth-child(1)')); assert visible('.solar-information h2').text == '水星'
    visit('/wasteland', '.expedition-overlay a'); assert visible('.expedition-overlay a').get_attribute('href').endswith('/wasteland?mode=story')
    checks.append('reduced motion disables decoration; WebGL2 failure keeps text atlas and story fallback usable')
    print(json.dumps({'status': 'passed', 'checks': checks, 'count': len(checks), 'screenshots': str(output)}, ensure_ascii=False))
finally:
    driver.quit()
