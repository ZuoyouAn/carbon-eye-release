"""Local/live single-player browser QA. No accounts, uploads, cloud writes, or game-state injection."""
import argparse,json,time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait,Select

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
site='https://carbon-eye-sip.netlify.app' if args.live else 'http://127.0.0.1:5176'
out=ROOT/'outputs/arcade'/('live' if args.live else 'local');out.mkdir(parents=True,exist_ok=True)
options=Options()
for flag in ['--headless=new','--window-size=1440,1100','--enable-unsafe-swiftshader']:options.add_argument(flag)
driver=webdriver.Edge(service=Service(str(ROOT/'outputs/human3/webdriver-cache/msedgedriver/win64/154.0.4258.53/msedgedriver.exe')),options=options)
driver.execute_cdp_cmd('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-reduced-motion','value':'reduce'}]})
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument',{'source':"window.__writes=[];const original=fetch;window.fetch=(u,o={})=>{if(o.method&&!['GET','HEAD'].includes(o.method.toUpperCase()))window.__writes.push(o.method);return original(u,o)};"})
checks=[]
def wait(fn,seconds=45):return WebDriverWait(driver,seconds,poll_frequency=.12).until(fn)
def visible(selector):return wait(lambda d:next((e for e in d.find_elements('css selector',selector) if e.is_displayed()),None))
def button(text):return wait(lambda d:next((e for e in d.find_elements('tag name','button') if e.is_displayed() and e.text.strip()==text),None))
def click(el):driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})",el);el.click()
def visit(path,selector):driver.get(site+path);visible(selector);wait(lambda d:not d.find_elements('css selector','.page-fade-enter-active'))
def overflow():assert driver.execute_script('return document.documentElement.scrollWidth<=innerWidth'),'mobile overflow'
def stage():return visible('.arc-stage')
def attr(name):return stage().get_attribute('data-'+name)
def resource(name):return int(visible(f'[data-winter-resource={name}]').text)
def focus():driver.execute_script('arguments[0].focus({preventScroll:true})',stage())
def build(kind):click(visible(f'[data-winter-building={kind}]'));click(button('确认建造'))
def snapshot(name):driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})",stage());driver.save_screenshot(str(out/name))
try:
    visit('/games','.games-grid');assert len(driver.find_elements('css selector','.game-cover'))==3
    for path in ['/games/swarm','/games/winter','/wasteland']:assert driver.find_elements('css selector',f'.games-grid a[href="{path}"]')
    driver.save_screenshot(str(out/'gallery-desktop.png'));checks.append('three independently discoverable original games; old camp link remains')
    visit('/games/swarm','.swarm-stage canvas');click(visible('[data-profession=guardian]'));Select(driver.find_elements('css selector','.arc-overlay select')[1]).select_by_value('practice')
    click(button('进入敌潮'));focus();before=float(attr('x'));ActionChains(driver).key_down('d').pause(.35).key_up('d').perform();assert float(attr('x'))>before+20
    click(button('放大战场'));visible('.arc-stage.is-expanded');ActionChains(driver).send_keys(Keys.ESCAPE).perform();assert attr('phase')=='paused';assert driver.execute_script('return document.body.style.overflow')!='hidden'
    frozen=attr('time');time.sleep(.3);assert attr('time')==frozen;click(button('继续战斗'));checks.append('actual keyboard movement, expansion/Escape and pause freeze without state injection')
    deadline=time.monotonic()+110
    while not attr('branch') and time.monotonic()<deadline:
        choices=driver.find_elements('css selector','.arc-choices button')
        if choices:
            assert all(c.find_element('css selector','em').text for c in choices), 'upgrade cards must preview real numerical effects'
            frozen=attr('time');time.sleep(.18);assert attr('time')==frozen
            preferred=next((c for c in choices if c.get_attribute('data-upgrade') in ['bastion','damage','vitality','haste']),choices[0]);click(preferred)
        elif attr('phase') in ['lost','won']:raise AssertionError('journey ended before branch')
        else:
            focus();ActionChains(driver).send_keys('e').perform()
            # Public direction aid also exposes coordinates; use real movement to collect, never teleport.
            el=stage();gx,gy=el.get_attribute('data-loot-x'),el.get_attribute('data-loot-y')
            if gx and gy:
                dx=float(gx)-float(attr('x'));dy=float(gy)-float(attr('y'));chain=ActionChains(driver);held=[]
                if abs(dx)>30:held.append('d' if dx>0 else 'a')
                if abs(dy)>30:held.append('s' if dy>0 else 'w')
                for key in held:chain.key_down(key)
                chain.pause(.22)
                for key in held:chain.key_up(key)
                chain.perform()
            else:time.sleep(.25)
    assert attr('branch')=='bastion';assert int(attr('level'))>=4;assert int(attr('kills'))>=8
    while driver.find_elements('css selector','.arc-choices button'):click(driver.find_elements('css selector','.arc-choices button')[0])
    snapshot('swarm-desktop.png');checks.append('real enemy kills, XP pickup, frozen upgrades and permanent level-four profession branch')
    click(button('暂停'));frozen=attr('time');click(button('结束本局并查看结果'));assert attr('phase')=='ended';assert attr('time')==frozen
    checks.append('ending a run produces bounded statistics rather than continuing hidden combat')
    visit('/games/winter','.winter-stage canvas');click(button('点亮火种'));build('sawmill');assert int(attr('buildings'))==1;build('coal');assert int(attr('buildings'))==2
    wait(lambda d:resource('wood')>=20);build('mine');click(driver.find_element('css selector','button[aria-label="减少采煤岗位"]'));click(driver.find_element('css selector','button[aria-label="增加采铁岗位"]'));assert visible('[data-job=iron]').text=='1'
    click(button('取消蓝图'));click(button('暂停'));frozen=attr('time');time.sleep(.25);assert attr('time')==frozen;click(button('继续聚落'));click(button('4×'))
    checks.append('actual winter construction, mine-gated worker reassignment, pause and accelerated simulation')
    sent=False;returned=False;deadline=time.monotonic()+130
    while attr('phase')=='playing' and time.monotonic()<deadline:
        choices=driver.find_elements('css selector','[data-winter-supply=fuel]')
        if choices:click(choices[0]);continue
        level=int(attr('furnace'))
        if level<3 and resource('wood')>=18+level*10 and resource('iron')>=4+level*4:
            click(visible('.arc-sidebar>.arc-card:first-child>button.arc-small'));continue
        if level>=3 and not sent and resource('wood')>=20 and resource('iron')>=6:
            build('outpost');click(button('取消蓝图'));click(button('燃料储备点 · 2 人 / 20s'));sent=True
        if sent and not driver.find_elements('css selector','.arc-progress'):returned=True
        time.sleep(.15)
    assert attr('phase')=='won',f'winter campaign failed: {attr("phase")}, day {attr("day")}'
    assert int(attr('day'))==6;assert int(attr('furnace'))>=3;assert sent and returned;assert float(attr('health'))>50
    snapshot('winter-desktop.png');checks.append('complete real five-day campaign with furnace upgrades, dawn supplies and returning expedition')
    for width in [390,320]:
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':width,'height':844,'deviceScaleFactor':1,'mobile':True})
        for path,selector in [('/games','.games-grid'),('/games/swarm','.swarm-stage canvas'),('/games/winter','.winter-stage canvas')]:visit(path,selector);overflow()
        click(button('点亮火种'));build('hut');assert int(attr('buildings'))==1;overflow();snapshot(f'winter-mobile-{width}.png')
        assert driver.execute_script('const hud=document.querySelector(".arc-hud").getBoundingClientRect(),actions=document.querySelector(".arc-stage-actions").getBoundingClientRect();return hud.bottom<=actions.top'), 'winter HUD overlaps controls'
        visit('/games/swarm','.swarm-stage canvas');click(button('进入敌潮'));snapshot(f'swarm-mobile-{width}.png');overflow()
        stick=visible('.arc-stick');r=driver.execute_script('return arguments[0].getBoundingClientRect().toJSON()',stick);cx=int(r['x']+r['width']/2);cy=int(r['y']+r['height']/2);before=float(attr('x'))
        touch=ActionBuilder(driver,mouse=PointerInput('touch','arcade-touch'));touch.pointer_action.move_to_location(cx,cy);touch.pointer_action.pointer_down();touch.pointer_action.move_to_location(cx+26,cy);touch.pointer_action.pause(.3);touch.pointer_action.pointer_up();touch.perform()
        assert float(attr('x'))>before+15;click(button('暂停'));frozen=attr('x');time.sleep(.2);assert attr('x')==frozen
    checks.append('gallery and both games fit 390/320px; actual mobile building controls work')
    click(button('放大战场'));visible('.arc-stage.is-expanded');click(visible('.arc-stage-actions a'));visible('.games-grid');assert not driver.find_elements('css selector','.arc-stage canvas');assert driver.execute_script('return document.body.style.overflow')!='hidden'
    assert not driver.execute_script('return window.__writes.length');checks.append('route unmount releases canvas, input handlers and expansion scroll lock; no cloud writes')
    report={'status':'passed','count':len(checks),'checks':checks,'cloud_writes':False,'actual_model_calls':0};(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
except Exception:
    driver.save_screenshot(str(out/'failure.png'));raise
finally:driver.quit()
