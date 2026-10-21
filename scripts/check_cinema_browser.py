"""Two isolated browsers: actual CC0 video, authority checks, comments and mobile UI.

Run against a local production build or the existing deployment. No credentials or
room tokens are logged. Requires Selenium and the user's existing Edge driver.
"""
import argparse
import json
import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait


# Only search/detail responses are deterministic fixtures. Authentication, room
# creation, role enforcement, comments and the actual CC0 video use the real app.
SEARCH_FIXTURE = r"""
(() => {
  const realFetch = window.fetch.bind(window);
  const movie = 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4';
  const sources = ['bad','good'].map(key => ({key:'fixture_'+key,name:'测试'+key,url:'https://example.com/'+key}));
  window.fetch = async (input, init) => {
    const u = new URL(typeof input === 'string' ? input : input.url, location.origin);
    if (u.origin !== location.origin) return realFetch(input, init);
    if (u.pathname === '/api/status') {
      const r=await realFetch(input,init), data=await r.json();
      return Response.json({...data,defaultSources:sources,defaultSubscriptions:[],defaultRecommendSource:'douban'});
    }
    if (u.pathname === '/api/douban') return Response.json({items:[]});
    if (u.pathname === '/api/search') {
      const change = JSON.parse(init.body).wd.includes('换片');
      const list = (change ? [sources[1]] : sources).map((s,i)=>({sourceKey:s.key,sourceName:s.name,
        sourceUrl:s.url,vodId:change?'3':String(i+1),name:change?'CC0 Flower 第二场':'CC0 Flower',remarks:'CC0 测试样本'}));
      const data={list,failures:[]};
      return u.searchParams.has('stream') ? new Response(JSON.stringify({type:'done',...data})+'\n',
        {headers:{'Content-Type':'application/x-ndjson'}}) : Response.json(data);
    }
    if (u.pathname === '/api/detail') {
      if(u.searchParams.get('id')==='1') return Response.json({error:'测试源不可用'},{status:404});
      return Response.json({episodes:[movie,movie+'?episode=2'],videoInfo:{title:'CC0 Flower',sourceKey:'fixture_good',sourceName:'测试good'}});
    }
    return realFetch(input,init);
  };
})();
"""


def button(driver, text):
    return driver.find_element('xpath', f'//button[contains(., "{text}")]')


def api(driver, body):
    return driver.execute_async_script("""
        const body = arguments[0], done = arguments[1];
        fetch('/api/cinema', {method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify(body)}).then(async r => done({status:r.status,data:await r.json()}))
          .catch(() => done({status:0}));
    """, body)


def member(driver):
    return driver.execute_script("return JSON.parse(sessionStorage.getItem('space-cinema-session-v1'))")


def media_state(driver):
    return driver.execute_script("""const v=document.querySelector('video');
      return v ? {time:v.currentTime,paused:v.paused,ready:v.readyState,controls:v.controls,
        rate:v.playbackRate,error:v.error?.code||null} : {};""")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tv', default='http://127.0.0.1:8091')
    parser.add_argument('--driver', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--credentials-file')
    args = parser.parse_args()
    password = os.environ.get('CINEMA_TEST_PASSWORD', 'cinema-local-test-only')
    if args.credentials_file:
        values = dict(line.split('=', 1) for line in Path(args.credentials_file).read_text(encoding='utf-8-sig').splitlines() if '=' in line and not line.startswith('#'))
        password = values['PASSWORD'].strip().strip('"').strip("'")
    elif not args.tv.startswith('http://127.0.0.1:'):
        raise RuntimeError('Use a private credentials file for production; never place passwords in arguments')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    drivers = []
    room_host = None
    results = {}
    try:
        for _ in range(2):
            options = Options()
            for flag in ['--headless=new', '--window-size=1440,1050', '--no-first-run', '--autoplay-policy=no-user-gesture-required']:
                options.add_argument(flag)
            driver = webdriver.Edge(service=Service(args.driver, service_args=['--disable-build-check']), options=options)
            drivers.append(driver)
            driver.set_page_load_timeout(90)
            driver.set_script_timeout(30)
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source':SEARCH_FIXTURE})
            driver.get(args.tv + '/cinema')
            authenticated = driver.execute_async_script("""const done=arguments[1];
              fetch('/api/auth',{method:'POST',headers:{'Content-Type':'application/json'},
              body:JSON.stringify({password:arguments[0]})}).then(r=>done(r.status)).catch(()=>done(0));""", password)
            assert authenticated == 200, 'Access verification failed'
            driver.refresh()
            WebDriverWait(driver, 30).until(lambda d: '选一部影片' in d.find_element('tag name', 'body').text)
            WebDriverWait(driver, 30).until(lambda d: '请先验证访问密码' not in d.find_element('tag name', 'body').text)
        host, guest = drivers
        host.get(args.tv)
        search = WebDriverWait(host, 20).until(lambda d: d.find_element('css selector', 'input[aria-label="搜索影片"]'))
        search.send_keys('同步测试', Keys.ENTER)
        launch = WebDriverWait(host, 20).until(lambda d: d.find_element('css selector','button[aria-label="用CC0 Flower启动放映厅"]'))
        host.save_screenshot(str(output / 'search-cinema-button.png'))
        launch.click()
        WebDriverWait(host, 20).until(lambda d: d.find_elements('css selector', '.cinema-room-heading'))
        room_host = member(host)
        assert '第1集' in host.find_element('css selector', '.cinema-room-heading').text
        assert not host.find_element('css selector', 'input[placeholder="MP4 / M3U8 直链"]').is_displayed()
        results['search_button_auto_creates_media_room_with_source_fallback'] = True
        guest.find_element('css selector', 'input[placeholder="你的昵称"]').send_keys('测试观众')
        guest.find_element('css selector', 'input[placeholder="16 位房间码"]').send_keys(room_host['roomId'])
        button(guest, '加入放映厅').click()
        WebDriverWait(guest, 20).until(lambda d: '你是观众' in d.find_element('tag name', 'body').text)
        room_guest = member(guest)
        assert media_state(host)['controls'] and not media_state(guest)['controls']
        results['create_join_and_host_only_controls'] = True

        for driver in drivers:
            WebDriverWait(driver, 45).until(lambda d: media_state(d).get('ready', 0) >= 2)
        Select(host.find_element('css selector','select[aria-label="切换集数"]')).select_by_value('1')
        WebDriverWait(guest, 15).until(lambda d: '第2集' in d.find_element('css selector','.cinema-room-heading').text)
        for driver in drivers:
            WebDriverWait(driver, 30).until(lambda d: media_state(d).get('ready', 0) >= 2)
        assert not guest.find_elements('css selector','select[aria-label="切换集数"]')
        results['host_episode_selection_syncs_to_guests'] = True
        host.execute_script("document.querySelector('video').muted=true; document.querySelector('video').play()")
        WebDriverWait(guest, 15).until(lambda d: not media_state(d)['paused'] and media_state(d)['time'] > .15)
        results['actual_playback'] = True
        host.execute_script("document.querySelector('video').pause()")
        WebDriverWait(guest, 10).until(lambda d: media_state(d)['paused'])
        time.sleep(.8)
        host.execute_script("document.querySelector('video').currentTime=2")
        WebDriverWait(guest, 10).until(lambda d: abs(media_state(d)['time'] - 2) < .4)
        results['host_pause_and_seek'] = True
        host.execute_script("document.querySelector('video').playbackRate=1.5")
        WebDriverWait(guest, 10).until(lambda d: abs(media_state(d)['rate'] - 1.5) < .04)
        results['rate_sync'] = True
        refused = api(guest, {'action':'control', **room_guest, 'role':'host', 'op':'seek', 'position':4, 'sequence':int(time.time()*1000000)})
        assert refused['status'] == 403
        guest.execute_script("document.querySelector('video').currentTime=4")
        WebDriverWait(guest, 10).until(lambda d: abs(media_state(d)['time'] - 2) < .4)
        results['guest_api_denied_and_local_seek_corrected'] = True

        guest.find_element('id', 'cinema-comment').send_keys('一起看测试：<img src=x onerror=alert(1)>')
        button(guest, '发送评论').click()
        WebDriverWait(host, 10).until(lambda d: '<img src=x onerror=alert(1)>' in d.find_element('css selector', '.cinema-message-list').text)
        assert not host.find_elements('css selector', '.cinema-message-list img')
        host.find_element('id', 'cinema-comment').send_keys('房主收到，继续观看')
        button(host, '发送评论').click()
        WebDriverWait(guest, 10).until(lambda d: '房主收到' in d.find_element('css selector', '.cinema-message-list').text)
        results['bidirectional_comments_as_plaintext'] = True
        host.save_screenshot(str(output / 'cinema-host-desktop.png'))
        guest.save_screenshot(str(output / 'cinema-guest-desktop.png'))
        guest.refresh()
        WebDriverWait(guest, 20).until(lambda d: '你是观众' in d.find_element('tag name', 'body').text)
        assert member(guest)['memberToken'] == room_guest['memberToken']
        results['refresh_retains_role'] = True
        host.get(args.tv + '/?s=换片')
        replacement = WebDriverWait(host, 20).until(lambda d: d.find_element('css selector','button[aria-label="用CC0 Flower 第二场启动放映厅"]'))
        replacement.click()
        WebDriverWait(host, 20).until(lambda d: d.find_elements('css selector','.cinema-room-heading'))
        assert member(host)['roomId'] == room_host['roomId']
        WebDriverWait(guest, 15).until(lambda d: '第二场' in d.find_element('css selector','.cinema-room-heading').text)
        assert member(guest)['memberToken'] == room_guest['memberToken']
        results['search_reuses_host_room_without_disconnect'] = True
        for driver in drivers:
            driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width':390,'height':900,'deviceScaleFactor':1,'mobile':True})
            assert driver.execute_script('return document.documentElement.scrollWidth<=innerWidth+1'), 'Mobile overflow'
        guest.save_screenshot(str(output / 'cinema-guest-mobile.png'))
        host.save_screenshot(str(output / 'cinema-host-mobile.png'))
        results['mobile_390px'] = True
        closed = api(host, {'action':'leave', **room_host})
        assert closed['status'] == 200
        room_host = None
        assert api(guest, {'action':'sync', **room_guest})['status'] == 410
        results['host_ends_room'] = True
        guest.get(args.tv)
        WebDriverWait(guest, 20).until(lambda d: '左右视频站' in d.title)
        assert guest.execute_script('return document.documentElement.scrollWidth<=innerWidth+1')
        assert not guest.find_elements('css selector', 'a[href="/ai-drama"]')
        removed = guest.execute_async_script("fetch('/ai-drama').then(r=>arguments[0](r.status))")
        assert removed == 404
        guest.save_screenshot(str(output / 'video-station-mobile.png'))
        results['new_brand_and_ai_page_removed'] = True
        print(json.dumps(results, ensure_ascii=False))
    except Exception:
        for index, driver in enumerate(drivers):
            try:
                driver.save_screenshot(str(output / f'failure-{index}.png'))
                print(json.dumps({'browser':index,'media':media_state(driver)}, ensure_ascii=False))
            except Exception:
                pass
        raise
    finally:
        if room_host and drivers:
            try:
                api(drivers[0], {'action':'leave', **room_host})
            except Exception:
                pass
        for driver in drivers:
            driver.quit()


if __name__ == '__main__':
    main()
