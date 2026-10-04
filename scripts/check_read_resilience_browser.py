"""Local-only deterministic slow/error read tests; no production or model writes."""
import json
from pathlib import Path
import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
SITE = 'http://127.0.0.1:5176'


def main():
    output = ROOT / 'outputs/read-resilience' / uuid.uuid4().hex[:8]
    output.mkdir(parents=True, exist_ok=True)
    options = Options()
    for arg in ['--headless=new', '--window-size=1440,1100', '--disable-gpu']:
        options.add_argument(arg)
    driver = webdriver.Edge(service=Service(str(ROOT / 'outputs/human3/webdriver-cache/msedgedriver/win64/154.0.4258.53/msedgedriver.exe')), options=options)
    wait = WebDriverWait(driver, 30)
    checks = []
    mock = r"""
      const original = window.fetch;
      window.__reads = []; window.__pending = []; window.__fails = {}; window.__aborts = 0; window.__slowHome = false;
      window.__release = () => { for (const done of window.__pending.splice(0)) done(); };
      window.fetch = (input, init = {}) => {
        const url = new URL(String(input), location.origin);
        if (url.origin !== 'http://127.0.0.1:8013' || (init.method && init.method !== 'GET')) return original(input, init);
        window.__reads.push({ path: url.pathname, q: url.searchParams.get('q'), headers: init.headers, compact: url.searchParams.get('include_content') });
        init.signal?.addEventListener('abort', () => window.__aborts++, {once:true});
        const json = (body, status = 200) => new Response(JSON.stringify(body), {status, headers:{'Content-Type':'application/json'}});
        const deferred = body => new Promise(resolve => window.__pending.push(() => resolve(json(body)))); // Deliberately ignore abort to test stale-response guards.
        if (window.__fails[url.pathname]) return Promise.resolve(new Response('simulated gateway error', {status:503}));
        const id = Number(url.pathname.split('/').at(-1));
        const item = n => ({id:n, title:'result-' + n, name:'novel-' + n, content:'body-' + n, summary:'summary', category:'Test', tags:[], created_at:'2026-10-05', author:'tester', like_count:0, favorite_count:0, comment_count:0, progress:0, font_size:18, theme:'dark', is_liked:false, is_favorited:false});
        if (url.pathname === '/api/site-summary') return window.__slowHome ? deferred({novels:2, posts:1, articles:1}) : Promise.resolve(json({novels:2, posts:1, articles:1}));
        if (url.pathname === '/api/yulu/random') return window.__slowHome ? deferred({id:1,content:'test quote'}) : Promise.resolve(json({id:1,content:'test quote'}));
        if (url.pathname === '/api/articles/categories') return Promise.resolve(json(['Test']));
        for (const kind of ['articles', 'posts', 'novels']) {
          if (url.pathname === '/api/' + kind) {
            const row = item(url.searchParams.get('q') === 'slow' ? 1 : 2);
            const data = kind === 'novels' ? [item(1), item(2)] : {items:[row], page:1, page_size:9, total:1, pages:1};
            return url.searchParams.get('q') === 'slow' ? deferred(data) : Promise.resolve(json(data));
          }
          if (url.pathname.startsWith('/api/' + kind + '/') && Number.isInteger(id)) {
            const body = kind === 'articles' ? {article:item(id),comments:[]} : kind === 'posts' ? {post:item(id),comments:[]} : {novel:item(id)};
            return id === 1 ? deferred(body) : Promise.resolve(json(body));
          }
        }
        return original(input, init);
      };
    """
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': mock})

    def shown(selector):
        return wait.until(lambda d: next((e for e in d.find_elements(By.CSS_SELECTOR, selector) if e.is_displayed()), None))
    def settled():
        wait.until(lambda d: not d.find_elements(By.CSS_SELECTOR, '.page-fade-enter-active, .page-fade-leave-active'))
    def navigate(path):
        driver.execute_script("document.querySelector('#app').__vue_app__.config.globalProperties.$router.push(arguments[0])", path)
        wait.until(lambda d: d.execute_script('return location.pathname') == path)
        settled()
    def search(text):
        field = shown('input[type=search]'); field.clear(); field.send_keys(text); field.send_keys(Keys.ENTER)
    def header():
        return shown('main h1').text

    try:
        driver.get(SITE + '/articles/1'); shown('main'); settled()
        wait.until(lambda d: d.execute_script('return window.__pending.length') == 1)
        assert driver.execute_script("return window.__reads.filter(r=>r.path==='/api/articles'||r.path==='/api/articles/categories').length") == 0
        assert not driver.find_elements(By.CSS_SELECTOR, '.card-grid, .toolbar')
        checks.append('direct article detail skips list and categories; loading stays in detail mode')
        navigate('/articles/2'); wait.until(lambda d: header() == 'result-2')
        driver.execute_script('window.__release()')
        wait.until(lambda d: d.execute_script('return window.__pending.length') == 0)
        assert header() == 'result-2'
        checks.append('out-of-order article detail cannot replace the current route')

        navigate('/articles'); shown('.content-card'); search('slow')
        wait.until(lambda d: d.execute_script('return window.__pending.length') == 1)
        search('fast'); wait.until(lambda d: shown('.card-heading-button').text == 'result-2')
        driver.execute_script('window.__release()'); assert shown('.card-heading-button').text == 'result-2'
        checks.append('Enter search works and slower previous search cannot overwrite the latest result')
        driver.execute_script("window.__fails['/api/articles']=true")
        search('fast'); assert '服务暂不可用' in shown('.request-error').text
        assert not driver.find_elements(By.CSS_SELECTOR, '.el-empty')
        driver.save_screenshot(str(output / 'error-desktop.png'))
        driver.execute_script("window.__fails['/api/articles']=false")
        shown('.request-error button').click(); shown('.content-card')
        wait.until(lambda d: not d.find_elements(By.CSS_SELECTOR, '.request-error'))
        checks.append('failed list is not confused with an empty list; retry recovers')

        navigate('/articles/404'); wait.until(lambda d: header() == 'result-404')
        driver.execute_script("window.__fails['/api/articles/405']=true")
        navigate('/articles/405'); shown('.request-error')
        assert not driver.find_elements(By.CSS_SELECTOR, '.markdown-body, .card-grid, .toolbar')
        checks.append('failed new detail does not show previous article or unrelated list')

        navigate('/posts/1'); wait.until(lambda d: d.execute_script('return window.__pending.length') == 1)
        assert driver.execute_script("return window.__reads.filter(r=>r.path==='/api/posts').length") == 0
        navigate('/posts/2'); wait.until(lambda d: header() == 'result-2')
        driver.execute_script('window.__release()'); assert header() == 'result-2'
        checks.append('direct post detail skips list; stale post cannot win')
        navigate('/posts'); shown('.content-card')
        driver.execute_script("window.__fails['/api/posts']=true")
        search('failed'); shown('.request-error'); assert not driver.find_elements(By.CSS_SELECTOR, '.el-empty')
        driver.execute_script("window.__fails['/api/posts']=false")
        shown('.request-error button').click(); shown('.content-card')
        checks.append('post read failure and manual recovery')

        navigate('/novels/1'); wait.until(lambda d: d.execute_script('return window.__pending.length') == 1)
        assert driver.execute_script("return window.__reads.filter(r=>r.path==='/api/novels').length") == 1
        assert driver.execute_script("return window.__reads.find(r=>r.path==='/api/novels').compact") == 'false'
        navigate('/novels/2'); wait.until(lambda d: header() == 'novel-2')
        driver.execute_script('window.__release()'); assert shown('.reader-box').text == 'body-2'
        checks.append('novel list loads once without bodies; direct detail loads in parallel and stays correct')
        driver.execute_script("window.__fails['/api/novels/3']=true")
        navigate('/novels/3'); shown('.request-error')
        assert not driver.find_elements(By.CSS_SELECTOR, '.reader-box')
        driver.execute_script("window.__fails['/api/novels/3']=false")
        shown('.request-error button').click(); wait.until(lambda d: shown('.reader-box').text == 'body-3')
        checks.append('novel detail failure hides old reader and supports retry')

        assert driver.execute_script("return window.__reads.every(r=>!Object.keys(r.headers).some(k=>k.toLowerCase()==='content-type'))")
        checks.append('public reads do not add non-simple JSON request headers')
        driver.execute_script('window.__slowHome=true; window.__aborts=0')
        navigate('/'); wait.until(lambda d: d.execute_script('return window.__pending.length') == 2)
        navigate('/projects'); wait.until(lambda d: d.execute_script('return window.__aborts') >= 2)
        driver.execute_script('window.__release()'); assert 'result-' not in header()
        checks.append('leaving home cancels quote and summary reads without stale UI effects')

        driver.set_window_size(390, 844)
        navigate('/articles/405'); shown('.request-error')
        assert driver.execute_script('return document.documentElement.scrollWidth <= innerWidth')
        driver.save_screenshot(str(output / 'error-mobile.png'))
        checks.append('mobile error and recovery controls fit 390px width')
        report = {'status':'passed', 'passed':len(checks), 'checks':checks, 'screenshots':str(output), 'cloud_writes':False, 'actual_model_calls':0}
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
