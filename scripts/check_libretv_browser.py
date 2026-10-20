"""Local/production smoke checks, using synthetic data and no private media sources."""
import argparse
import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--website', default='http://127.0.0.1:5179')
    parser.add_argument('--tv', default='http://127.0.0.1:8091')
    parser.add_argument('--driver', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--website-only', action='store_true')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1440,1050')
    options.add_argument('--no-first-run')
    # Only used with this machine's existing driver. No global browser changes.
    service = Service(args.driver, service_args=['--disable-build-check'])
    driver = webdriver.Edge(service=service, options=options)
    driver.set_page_load_timeout(90)
    try:
        driver.get(args.website.rstrip('/') + '/libretv')
        WebDriverWait(driver, 30).until(lambda d: '给自己一点' in d.find_element('tag name', 'body').text)
        assert 'LibreTV' in driver.title
        assert driver.find_element('css selector', '.cinema-primary').get_attribute('href').startswith('https://')
        driver.save_screenshot(str(output / 'website-desktop.png'))
        driver.set_window_size(390, 900)
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 900, 'deviceScaleFactor': 1, 'mobile': True})
        time.sleep(1)
        assert driver.execute_script('return document.documentElement.scrollWidth <= innerWidth + 1')
        driver.save_screenshot(str(output / 'website-mobile.png'))
        if args.website_only:
            print(json.dumps({'website_route': True, 'mobile_overflow': False}))
            return
        driver.set_window_size(1440, 1050)
        driver.execute_cdp_cmd('Emulation.clearDeviceMetricsOverride', {})
        driver.get(args.tv)
        WebDriverWait(driver, 45).until(lambda d: d.find_elements('css selector', 'a[href="https://carbon-eye-sip.netlify.app/libretv"]'))
        assert 'dark' not in driver.find_element('tag name', 'html').get_attribute('class').split()
        assert driver.find_elements('css selector', 'a[href="https://github.com/ZuoyouAn/carbon-eye-release/tree/main/apps/libretv"]')
        driver.save_screenshot(str(output / 'tv-desktop.png'))
        driver.set_window_size(390, 900)
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 900, 'deviceScaleFactor': 1, 'mobile': True})
        time.sleep(1)
        assert driver.execute_script('return document.documentElement.scrollWidth <= innerWidth + 1')
        driver.save_screenshot(str(output / 'tv-mobile.png'))
        result = {'website_route': True, 'source_link': True, 'light_theme': True, 'mobile_overflow': False}
        print(json.dumps(result))
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
