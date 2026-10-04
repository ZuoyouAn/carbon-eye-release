"""Read-only cloud regression; records live only in a disposable browser profile."""
import argparse
import json
from pathlib import Path
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true')
args = parser.parse_args()
site = 'https://carbon-eye-sip.netlify.app' if args.live else 'http://127.0.0.1:5176'
output = ROOT / 'outputs/exploration-reader' / ('live' if args.live else 'local')
output.mkdir(parents=True, exist_ok=True)
options = Options()
for option in ['--headless=new', '--window-size=1440,1100', '--enable-unsafe-swiftshader']:
    options.add_argument(option)
driver = webdriver.Edge(service=Service(str(ROOT / 'outputs/human3/webdriver-cache/msedgedriver/win64/154.0.4258.53/msedgedriver.exe')), options=options)
checks = []

def wait(predicate, timeout=35):
    return WebDriverWait(driver, timeout, poll_frequency=.1, ignored_exceptions=(StaleElementReferenceException,)).until(predicate)

def element(selector):
    return wait(lambda d: next((item for item in d.find_elements('css selector', selector) if item.is_displayed()), None))

def click(item):
    driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", item)
    wait(lambda d: not d.find_elements('css selector', '.page-fade-enter-active, .page-fade-leave-active'))
    item.click()

def button(text):
    return wait(lambda d: next((item for item in d.find_elements('tag name', 'button') if item.is_displayed() and item.text.strip() == text), None))

def visit(path, selector):
    driver.get(site + path)
    element(selector)
    wait(lambda d: not d.find_elements('css selector', '.page-fade-enter-active, .page-fade-leave-active'))

def ready():
    element('.guide-meta[data-index-ready="true"]')
    wait(lambda d: not d.find_elements('css selector', '.page-fade-enter-active, .page-fade-leave-active'))

def overflow():
    assert driver.execute_script('return document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'

def more_link(path):
    summary = driver.find_element('css selector', '.nav-more summary')
    click(summary)
    click(element(f'.nav-more a[href="{path}"]'))

probe = """
window.__bookWrites = []; window.__posted = []; window.__copied = '';
const originalSet = Storage.prototype.setItem;
Storage.prototype.setItem = function(key, value) { if (key === 'space-life-guide-reader-v1') window.__bookWrites.push(value); return originalSet.call(this, key, value); };
Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async text => { window.__copied = text; } } });
const originalFetch = window.fetch.bind(window);
window.fetch = (url, options = {}) => { if ((options.method || 'GET').toUpperCase() !== 'GET') window.__posted.push(String(url)); return originalFetch(url, options); };
"""
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': probe})
try:
    visit('/solar-system?planet=neptune&mission=voyager-2', '.mission-detail[data-mission="voyager-2"]')
    assert len(driver.find_elements('css selector', '.mission-card')) == 10
    assert len(driver.find_elements('css selector', '.solar-planet-list button[data-mission-target="true"]')) == 4
    assert '1977-08-20' in element('.mission-detail').text
    assert element('.mission-detail a').get_attribute('href').startswith('https://science.nasa.gov/')
    click(button('靠近天王星 ↗'))
    wait(lambda d: 'planet=uranus' in d.current_url)
    assert element('.solar-stage').get_attribute('data-playing') == 'false'
    checks.append('mission deep link highlights four targets; focus preserves mission and pauses animation')
    Select(driver.find_elements('css selector', '.mission-filters select')[0]).select_by_value('mars')
    Select(driver.find_elements('css selector', '.mission-filters select')[1]).select_by_value('modern')
    wait(lambda d: len(d.find_elements('css selector', '.mission-card')) == 2)
    assert '好奇号' in element('.mission-timeline').text and '毅力号' in element('.mission-timeline').text
    checks.append('chronological mission filters compose while selected archive stays open')
    click(button('关闭任务标记'))
    wait(lambda d: not d.find_elements('css selector', '.solar-planet-list button[data-mission-target="true"]'))
    visit('/solar-system?planet=wrong&mission=wrong', '.mission-placeholder')
    assert '地球' in element('.solar-information').text
    checks.append('invalid mission and planet degrade safely; closing removes target markers')
    driver.execute_script("arguments[0].scrollIntoView({block:'start',behavior:'instant'})", element('.mission-archive'))
    driver.save_screenshot(str(output / 'missions-desktop.png'))

    visit('/life-guide', '.guide-card'); ready()
    assert '657 / 657' in element('.guide-meta').text
    assert not driver.find_elements('css selector', '.guide-original'), 'closed cards eagerly render markdown'
    assert driver.execute_script("return localStorage.getItem('space-life-guide-reader-v1')") is None
    click(element('#entry-1-1 .guide-card-actions button'))
    click(element('#entry-1-1 summary'))
    element('#entry-1-1 .guide-original')
    assert not driver.execute_script('return window.__bookWrites') and not driver.execute_script('return window.__posted')
    checks.append('full original catalog, lazy safe markdown, session bookmarks and reading do not write or post')
    click(element('#entry-1-1 .guide-card-actions button:nth-child(2)'))
    wait(lambda d: d.execute_script('return window.__copied').endswith('/life-guide?entry=1-1'))
    link = driver.execute_script('return window.__copied')
    driver.get(link); element('#entry-1-1 .guide-original'); ready()
    checks.append('single-entry share link opens exact original independently of local favorites')

    visit('/life-guide?chapter=1&page=2', '#entry-1-13'); ready()
    click(element('#entry-1-13 .guide-card-actions button'))
    click(element('#entry-1-13 summary')); element('#entry-1-13 .guide-original')
    click(driver.find_elements('css selector', '.guide-reader-actions input')[0])
    stored = json.loads(driver.execute_script("return localStorage.getItem('space-life-guide-reader-v1')"))
    assert stored == {'version': 1, 'enabled': True, 'saved': ['1-13'], 'resume': '1-13'}
    driver.refresh(); element('#entry-1-13'); ready()
    assert element('#entry-1-13 .guide-card-actions button').get_attribute('aria-pressed') == 'true'
    click(button('继续读第 1 节第 13 条 ↗')); element('#entry-1-13 .guide-original')
    checks.append('explicit opt-in persists only IDs; reload and resume restore correct chapter, page and entry')
    driver.execute_script("localStorage.setItem('other-game-save','keep')")
    click(button('清除收藏与阅读记录'))
    assert driver.execute_script("return localStorage.getItem('space-life-guide-reader-v1')") is None
    assert driver.execute_script("return localStorage.getItem('other-game-save')") == 'keep'
    checks.append('clear records removes only reader data and preserves other game storage')

    visit('/life-guide?chapter=8&evidence=A&money=0&benefit=自由&value=高&page=1', '.guide-meta'); ready()
    selects = driver.find_elements('css selector', '.guide-filters select')
    assert [Select(item).first_selected_option.get_attribute('value') for item in selects] == ['8', 'A', '自由', '0', '高']
    click(button('复制筛选链接 ↗'))
    assert 'evidence=A' in driver.execute_script('return window.__copied')
    assert 'saved' not in driver.execute_script('return window.__copied')
    # Use real browser history to check a same-route query transition.
    driver.execute_script("history.pushState({},'', '/life-guide?chapter=1&page=2'); dispatchEvent(new PopStateEvent('popstate'))")
    element('#entry-1-13')
    driver.back(); wait(lambda d: Select(d.find_elements('css selector', '.guide-filters select')[0]).first_selected_option.get_attribute('value') == '8')
    checks.append('all public filter parameters round-trip; back navigation restores controls')
    click(button('清空筛选')); element('#entry-1-1')
    count = driver.execute_script("return performance.getEntriesByType('resource').filter(r => r.name.includes('/life-guide/chapter-')).length")
    more_link('/solar-system'); element('.mission-archive')
    more_link('/life-guide'); ready()
    assert driver.execute_script("return performance.getEntriesByType('resource').filter(r => r.name.includes('/life-guide/chapter-')).length") == count
    checks.append('SPA route return reuses chapter cache without downloading book again')
    driver.save_screenshot(str(output / 'reader-desktop.png'))

    for path, selector in [('/solar-system?mission=voyager-2', '.mission-detail[data-mission="voyager-2"]'), ('/life-guide?entry=1-13', '#entry-1-13 .guide-original')]:
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
        visit(path, selector); overflow()
        driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", element(selector))
        driver.save_screenshot(str(output / ('missions-mobile.png' if 'solar' in path else 'reader-mobile.png')))
    checks.append('mobile 390px mission archive and expanded source reader have no horizontal overflow')

    if not args.live:
        injection = """
        const networkFetch = window.fetch; let failed = false;
        window.fetch = async (url, opts) => {
          if (String(url).includes('/life-guide/chapter-') && !String(url).includes('chapter-01')) {
            await new Promise((resolve, reject) => { const timer = setTimeout(resolve, 700); opts?.signal?.addEventListener('abort', () => { clearTimeout(timer); reject(new DOMException('aborted', 'AbortError')); }, { once: true }); });
            if (String(url).includes('chapter-02') && !failed) { failed = true; return new Response('error', { status: 503 }); }
          }
          return networkFetch(url, opts);
        };
        """
        token = driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': injection})['identifier']
        visit('/life-guide', '.guide-card')
        assert element('.guide-meta').get_attribute('data-index-ready') == 'false'
        assert '当前结果尚不完整' in element('.guide-meta').text
        element('[role="alert"]')
        assert driver.find_elements('css selector', '.guide-card'), 'partial failure erased available content'
        click(button('重试未加载的章节')); ready()
        assert '657 / 657' in element('.guide-meta').text
        driver.execute_cdp_cmd('Page.removeScriptToEvaluateOnNewDocument', {'identifier': token})
        checks.append('slow chapters display early with honest partial counts; failure retains content and retry restores full catalog')

    assert not driver.execute_script('return window.__posted')
    result = {'status': 'passed', 'checks': checks, 'count': len(checks), 'production_writes': False}
    (output / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
except Exception:
    driver.save_screenshot(str(output / 'failure.png'))
    raise
finally:
    driver.quit()
