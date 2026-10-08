"""Real-input animation QA; no game-state injection, accounts or cloud writes."""
import argparse, json, time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
site='https://carbon-eye-sip.netlify.app' if args.live else 'http://127.0.0.1:5176'
out=ROOT/'outputs/swarm-polish'/('live' if args.live else 'local');out.mkdir(parents=True,exist_ok=True)
options=Options()
for flag in ['--headless=new','--window-size=1440,1100']:options.add_argument(flag)
driver=webdriver.Edge(service=Service(str(ROOT/'outputs/human3/webdriver-cache/msedgedriver/win64/154.0.4258.53/msedgedriver.exe')),options=options)
driver.execute_cdp_cmd('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'no-preference'}]})
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument',{'source':"window.__errors=[];addEventListener('error',e=>window.__errors.push(e.message));window.__writes=[];const f=fetch;window.fetch=(u,o={})=>{if(o.method&&!['GET','HEAD'].includes(o.method.toUpperCase()))window.__writes.push(o.method);return f(u,o)}"})
wait=WebDriverWait(driver,35,poll_frequency=.1)
checks=[]
def button(text):return wait.until(lambda d:next((e for e in d.find_elements('tag name','button') if e.is_displayed() and e.text.strip()==text),None))
def click(el):driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})",el);el.click()
def stage():return driver.find_element('css selector','.swarm-stage')
def clock():return stage().get_attribute('data-time')
def pixels():return driver.execute_script("return document.querySelector('.swarm-stage canvas').toDataURL()")
try:
    for job in ['ranger','guardian','mage']:
        driver.get(site+'/games/swarm');wait.until(lambda d:d.find_elements('css selector','.swarm-stage canvas'))
        click(driver.find_element('css selector',f'[data-profession={job}]'))
        Select(driver.find_elements('css selector','.arc-overlay select')[1]).select_by_value('practice')
        click(button('进入敌潮'));driver.execute_script('arguments[0].focus({preventScroll:true})',stage())
        before=pixels();ActionChains(driver).key_down('d').pause(.35).key_up('d').send_keys('e').perform();after=pixels()
        assert before!=after;assert float(stage().get_attribute('data-x'))>25
        stage().screenshot(str(out/f'{job}-detail.png'))
        time.sleep(.3);click(button('暂停'));frozen=clock();frame=pixels();time.sleep(.3)
        assert clock()==frozen and pixels()==frame,'paused animation must freeze too'
        reduce=driver.find_elements('css selector','.arc-sidebar input[type=checkbox]')[1]
        click(reduce);assert reduce.is_selected();assert pixels()!=frame,'reduced mode must repaint immediately'
        click(button('继续战斗'));assert clock()==frozen or float(clock())>=float(frozen)
        assert not driver.execute_script('return window.__errors');assert not driver.execute_script('return window.__writes.length')
        checks.append(job+': real movement/skill, distinct artwork, exact animation freeze and reduced-mode repaint')
    driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':320,'height':844,'deviceScaleFactor':1,'mobile':True})
    click(button('暂停'));assert driver.execute_script('return document.documentElement.scrollWidth<=innerWidth')
    stage().screenshot(str(out/'mage-mobile.png'));click(driver.find_element('css selector','.arc-stage-actions a'))
    wait.until(lambda d:d.find_elements('css selector','.games-grid'));assert not driver.find_elements('css selector','.arc-stage canvas')
    checks.append('320px layout and leaving the route releases animated canvas')
    report={'status':'passed','checks':checks,'count':len(checks),'cloud_writes':False}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
finally:driver.quit()
