"""UI-only deterministic admin metrics fixture; creates no real analytics events."""
import argparse
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import Select, WebDriverWait

FIXTURE = r"""
(() => {
const user={id:999,username:'analytics-ui-test',role:'admin',is_muted:false,is_deleted:false};
localStorage.setItem('token','ui-fixture-only');localStorage.setItem('currentUser',JSON.stringify(user));
const realFetch=window.fetch.bind(window);window.__metricRequests=[];
window.fetch=async(input,init)=>{
 const url=new URL(typeof input==='string'?input:input.url,location.origin);
 if(url.pathname==='/api/auth/me')return Response.json({user});
 if(url.pathname==='/api/admin/dashboard')return Response.json({users:8,muted_users:0,articles:12,posts:3,post_comments:4,article_comments:6,messages:5});
 if(url.pathname==='/api/admin/analytics'){
  const days=Number(url.searchParams.get('days')||7),site=url.searchParams.get('site')||'all';window.__metricRequests.push({days,site});
  const series=Array.from({length:days},(_,i)=>({date:new Date(Date.UTC(2026,9,22-days+i)).toISOString().slice(0,10),pv:12+i*7,uv:6+i*3}));
  return Response.json({site,days,timezone:'Asia/Shanghai',started_at:'2026-10-21T22:00:00+08:00',retention_days:90,from:series[0].date,to:series.at(-1).date,
   today:{pv:54,uv:24},totals:{pv:231,uv:78},series,sites:[{site:'space',pv:180,uv:50},{site:'video',pv:51,uv:28}],
   top_pages:[{site:'video',path:'/cinema',pv:51,uv:28},{site:'space',path:'/projects',pv:120,uv:40},{site:'space',path:'/',pv:60,uv:23}]});
 }
 return realFetch(input,init);
};})();
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--website', default='http://127.0.0.1:5179')
    parser.add_argument('--driver', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.add_argument('--headless=new'); options.add_argument('--window-size=1440,1100')
    driver = webdriver.Edge(service=Service(args.driver, service_args=['--disable-build-check']), options=options)
    try:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source':FIXTURE})
        driver.get(args.website + '/admin')
        WebDriverWait(driver, 30).until(lambda d: d.find_elements('css selector','.traffic-cards strong'))
        WebDriverWait(driver, 15).until(lambda d: '54' in d.find_element('css selector','.traffic-cards').text)
        assert len(driver.find_elements('css selector','.traffic-bar-column')) == 7
        assert '放映厅' in driver.find_element('css selector','.traffic-pages').text
        driver.execute_script('window.scrollTo(0,0)'); driver.save_screenshot(str(output/'analytics-desktop.png'))
        filters = driver.find_elements('css selector','.traffic-filters select')
        Select(filters[0]).select_by_value('video')
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return window.__metricRequests.at(-1).site==='video'"))
        Select(filters[1]).select_by_value('30')
        WebDriverWait(driver, 10).until(lambda d: len(d.find_elements('css selector','.traffic-bar-column')) == 30)
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width':390,'height':900,'deviceScaleFactor':1,'mobile':True})
        assert driver.execute_script('return document.documentElement.scrollWidth<=innerWidth+1')
        driver.execute_script('document.documentElement.style.setProperty("scroll-behavior","auto","important"); document.querySelector(".traffic-panel").scrollIntoView({behavior:"instant",block:"start"})'); driver.save_screenshot(str(output/'analytics-mobile.png'))
        assert driver.execute_script('return !localStorage.getItem("space-analytics-browser-v1")')
        privacy = driver.find_element('css selector','.analytics-privacy summary')
        driver.execute_script('arguments[0].scrollIntoView({behavior:"instant",block:"center"})',privacy)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script('const r=arguments[0].getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight',privacy))
        privacy.click()
        driver.find_element('css selector','.analytics-privacy button').click()
        assert driver.execute_script('return localStorage.getItem("space-analytics-optout-v1")==="1"')
        print(json.dumps({'admin_chart':True,'site_filter':True,'range_filter':True,'mobile_390px':True,'no_test_tracking':True,'privacy_opt_out':True}))
    except Exception:
        driver.save_screenshot(str(output/'analytics-failure.png'))
        raise
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
