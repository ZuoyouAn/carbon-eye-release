"""Local or cloud read-only checks for readable text and original 3D controls."""
import argparse
import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true')
args = parser.parse_args()
site = 'https://carbon-eye-sip.netlify.app' if args.live else 'http://127.0.0.1:5176'
output = ROOT / 'outputs/readable-scenes' / ('live' if args.live else 'local')
output.mkdir(parents=True, exist_ok=True)
options = Options()
for flag in ['--headless=new', '--window-size=1440,1100', '--enable-unsafe-swiftshader']:
    options.add_argument(flag)
driver = webdriver.Edge(service=Service(str(ROOT / 'outputs/human3/webdriver-cache/msedgedriver/win64/154.0.4258.53/msedgedriver.exe')), options=options)
driver.execute_cdp_cmd('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
checks = []

def wait(predicate, timeout=35):
    return WebDriverWait(driver, timeout, poll_frequency=.1, ignored_exceptions=(StaleElementReferenceException,)).until(predicate)

def element(selector):
    return wait(lambda d: next((item for item in d.find_elements('css selector', selector) if item.is_displayed()), None))

def click(item):
    driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", item)
    item.click()

def button(text):
    return wait(lambda d: next((item for item in d.find_elements('tag name', 'button') if item.is_displayed() and item.text.strip() == text), None))

def visit(path, selector):
    driver.get(site + path); element(selector)

def overflow():
    assert driver.execute_script('return document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'

def font(selector, minimum):
    item = element(selector)
    assert driver.execute_script('return parseFloat(getComputedStyle(arguments[0]).fontSize)', item) >= minimum, selector

try:
    visit('/', '.hero-description'); font('.hero-description', 16); font('.status-strip', 14); font('.nav-links a', 14); overflow()
    checks.append('desktop body, navigation and status typography have readable minimum sizes')
    visit('/life-guide', '.guide-card'); element('.guide-meta[data-index-ready="true"]')
    font('.guide-card>p', 16); font('.guide-tags span', 14); font('.guide-search input', 16)
    checks.append('original book summaries, labels and search use enlarged text')

    visit('/wasteland', '.expedition-stage canvas'); font('.expedition-brief p', 14)
    Select(element('.expedition-difficulty select')).select_by_value('practice')
    click(button('开始探索')); wait(lambda d: element('.expedition-stage').get_attribute('data-difficulty') == 'practice')
    assert element('.expedition-hud strong').text.startswith('4:') or element('.expedition-hud strong').text == '5:00'
    assert len(driver.find_elements('css selector', '.expedition-map svg circle')) > 3
    font('.expedition-context', 14)
    click(button('放大场景')); element('.expedition-stage.is-expanded')
    assert driver.execute_script('return document.body.style.overflow') == 'hidden'
    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    wait(lambda d: element('.expedition-stage').get_attribute('data-status') == 'paused')
    assert not driver.find_elements('css selector', '.expedition-stage.is-expanded')
    assert driver.execute_script('return document.body.style.overflow') != 'hidden'
    checks.append('practice mode starts with extended timer; minimap and enlarged scene work; Escape pauses and restores scrolling')
    click(button('继续探索'))
    click(element('button[aria-label="向左旋转视角"]'))
    stage = element('.expedition-stage'); driver.execute_script('arguments[0].focus({preventScroll:true})', stage)
    ActionChains(driver).key_down('d').perform()
    try:
        wait(lambda d: float(element('.expedition-stage').get_attribute('data-x')) >= -10.4)
    finally:
        ActionChains(driver).key_up('d').perform()
    click(element('.expedition-context button'))
    wait(lambda d: '1 / 4' in element('.expedition-brief').text)
    assert '寻找下一个零件' in element('.expedition-context').text
    driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", element('.expedition-layout'))
    driver.save_screenshot(str(output / 'game-desktop.png'))
    checks.append('real movement exposes contextual pickup; inventory, target ring and minimap progress together')

    visit('/solar-system?planet=earth', '.solar-stage canvas')
    font('.solar-information p', 16); font('.solar-stage-note', 14)
    view = driver.find_elements('css selector', '.solar-toolbar select')[1]
    Select(view).select_by_value('top'); wait(lambda d: element('.solar-stage').get_attribute('data-view') == 'top')
    click(driver.find_elements('css selector', '.solar-toolbar input[type="checkbox"]')[1])
    wait(lambda d: element('.solar-stage').get_attribute('data-orbits') == 'false')
    slider = element('#solar-time')
    driver.execute_script("arguments[0].value='120';arguments[0].dispatchEvent(new Event('input',{bubbles:true}))", slider)
    wait(lambda d: float(element('.solar-stage').get_attribute('data-time')) == 120)
    assert element('.solar-stage').get_attribute('data-playing') == 'false'
    checks.append('top view, orbit visibility and bounded illustrative time scrubber respond without real-date claims')
    click(button('跟随这颗行星观察 ↗'))
    wait(lambda d: element('.solar-stage').get_attribute('data-follow') == 'earth')
    click(button('播放示意轨道'))
    wait(lambda d: float(element('.solar-stage').get_attribute('data-time')) > 120.2)
    click(button('暂停运行'))
    label = element('.solar-label')
    assert font('.solar-label', 14) is None
    click(element('.solar-planet-list button:nth-child(5)'))
    wait(lambda d: element('.solar-stage').get_attribute('data-follow') == 'jupiter')
    assert element('.solar-information h2').text == '木星'
    click(button('放大图谱')); element('.solar-stage.is-expanded')
    driver.save_screenshot(str(output / 'solar-expanded.png'))
    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    wait(lambda d: not d.find_elements('css selector', '.solar-stage.is-expanded'))
    assert driver.execute_script('return document.body.style.overflow') != 'hidden'
    click(button('回到全景'))
    assert element('.solar-stage').get_attribute('data-follow') == ''
    checks.append('camera follows selected planet during playback and selection changes; expansion cleans up and overview exits follow mode')
    click(driver.find_elements('css selector', '.solar-toolbar input[type="checkbox"]')[1])
    driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", element('.solar-layout'))
    driver.save_screenshot(str(output / 'solar-desktop.png'))

    for width in [390, 320]:
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
        for path, selector in [('/', '.hero-description'), ('/life-guide', '.guide-card'), ('/solar-system', '.solar-stage canvas'), ('/wasteland', '.expedition-stage canvas'), ('/human3', '.human-page'), ('/store', '.store-page'), ('/chat', '.auth-page')]:
            if path == '/chat':
                continue
            visit(path, selector); overflow()
        visit('/wasteland', '.expedition-stage canvas'); click(button('开始探索')); click(button('放大场景')); overflow()
        camera = element('.expedition-camera'); expand = element('.expedition-expand')
        assert driver.execute_script('const a=arguments[0].getBoundingClientRect(),b=arguments[1].getBoundingClientRect();return !(a.left<b.right && a.right>b.left && a.top<b.bottom && a.bottom>b.top)', camera, expand), 'game camera overlaps expand button'
        click(button('收起场景')); click(button('暂停'))
        if width == 390:
            driver.save_screenshot(str(output / 'game-mobile.png'))
        visit('/solar-system', '.solar-stage canvas'); click(button('放大图谱')); overflow()
        font('.solar-label', 14)
        click(button('收起图谱'))
        if width == 390:
            driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", element('.solar-layout'))
            driver.save_screenshot(str(output / 'solar-mobile.png'))
    checks.append('larger typography and scene controls fit 390px and 320px phones without overflow or button overlap')
    driver.execute_cdp_cmd('Emulation.clearDeviceMetricsOverride', {})
    visit('/solar-system', '.solar-stage canvas'); click(button('放大图谱'))
    driver.execute_script("history.pushState({},'', '/life-guide'); dispatchEvent(new PopStateEvent('popstate'))")
    element('.guide-card'); assert driver.execute_script('return document.body.style.overflow') != 'hidden'
    assert len(driver.find_elements('css selector', '.solar-stage canvas')) == 0
    checks.append('route unmount releases expansion scroll lock, canvas and scene controls')
    result = {'status': 'passed', 'count': len(checks), 'checks': checks, 'cloud_writes': False}
    (output / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
except Exception:
    driver.save_screenshot(str(output / 'failure.png'))
    raise
finally:
    driver.quit()
