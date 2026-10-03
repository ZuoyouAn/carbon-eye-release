"""Optional browser smoke check. Requires selenium and an installed Edge driver.

Run while Vite is listening on port 5175. Only uses a fresh headless profile.
"""
from pathlib import Path
import argparse
import json
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--driver", help="Optional path; otherwise Selenium Manager resolves a matching driver.")
    parser.add_argument("--url", default="http://127.0.0.1:5175/human3")
    args = parser.parse_args()
    output = Path(__file__).resolve().parent.parent / "outputs" / "human3"
    output.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1100")
    options.add_argument("--disable-gpu")
    options.add_experimental_option("prefs", {"download.default_directory": str(output), "download.prompt_for_download": False})
    os.environ["SE_CACHE_PATH"] = str(output / "webdriver-cache")
    driver = webdriver.Edge(service=Service(args.driver) if args.driver else Service(), options=options)
    wait = WebDriverWait(driver, 20)

    def shown(selector):
        return wait.until(lambda d: d.find_element(By.CSS_SELECTOR, selector))

    def click(selector):
        wait.until(lambda d: not d.find_elements(By.CSS_SELECTOR, '.page-fade-enter-active, .page-fade-leave-active'))
        element = shown(selector)
        driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", element)
        element.click()

    def check_width():
        assert driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth"), "Horizontal overflow"

    def capture(name):
        wait.until(lambda d: not d.find_elements(By.CSS_SELECTOR, '.page-fade-enter-active, .page-fade-leave-active'))
        driver.execute_script("window.scrollTo({top:0,behavior:'instant'})")
        driver.save_screenshot(str(output / name))

    def complete():
        for _ in range(24):
            if driver.find_elements(By.CSS_SELECTOR, ".human-report"):
                break
            if not driver.find_elements(By.CSS_SELECTOR, ".human-option input:checked"):
                click(".human-option")
            click(".human-question-footer .human-primary")
        shown(".human-report")

    try:
        driver.get(args.url)
        shown(".human-welcome")
        assert not shown(".human-check input").is_selected()
        capture("welcome-desktop.png")
        check_width()
        click(".human-primary")
        assert not shown(".human-question-footer .human-primary").is_enabled()
        click(".human-option")
        click(".human-question-footer .human-primary")
        shown(".human-question-card legend")
        click(".human-question-footer .human-secondary")
        assert shown(".human-option input").is_selected()
        driver.refresh()
        shown(".human-welcome")
        assert not driver.execute_script("return localStorage.getItem('human3-questionnaire-progress')")

        click(".human-check input")
        click(".human-primary")
        click(".human-option")
        click(".human-question-footer .human-primary")
        driver.refresh()
        shown(".human-resume")
        click(".human-primary")
        wait.until(lambda d: '2 / 24' in d.find_element(By.CSS_SELECTOR, '.human-progress-heading').text)
        capture("question-desktop.png")
        complete()
        assert "寻找锚点型" in shown(".human-pattern").text
        assert len(driver.find_elements(By.CSS_SELECTOR, ".human-result-grid article")) == 4
        assert len(driver.find_elements(By.CSS_SELECTOR, ".human-plan > div")) == 4
        click(".human-result-grid details summary")
        assert "遇到与你观点冲突" in shown(".human-result-grid details[open]").text
        capture("report-desktop.png")
        check_width()
        click(".human-report-heading button")
        report_file = output / "四维成长评估报告.md"
        wait.until(lambda _: report_file.exists())
        assert "寻找锚点型" in report_file.read_text(encoding="utf-8")
        driver.refresh()
        shown(".human-resume")
        click(".human-primary")
        shown(".human-report")
        buttons = driver.find_elements(By.CSS_SELECTOR, ".human-report-bottom button")
        driver.execute_script("arguments[0].click()", buttons[1])
        click(".human-option:nth-of-type(2)")
        complete()
        assert "先独立寻找证据" in driver.find_element(By.CSS_SELECTOR, ".human-result-grid article").get_attribute("textContent")
        driver.set_window_size(390, 844)
        driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
        assert driver.execute_script("return window.innerWidth") == 390
        check_width()
        capture("report-mobile.png")
        buttons = driver.find_elements(By.CSS_SELECTOR, ".human-report-bottom button")
        driver.execute_script("arguments[0].click()", buttons[2])
        shown(".human-welcome")
        assert not driver.execute_script("return localStorage.getItem('human3-questionnaire-progress')")
        driver.refresh()
        shown(".human-welcome")
        assert not driver.find_elements(By.CSS_SELECTOR, ".human-resume")
        check_width()
        capture("welcome-mobile.png")
        click(".human-primary")
        check_width()
        capture("question-mobile.png")
        # Keyboard-only selection and navigation work with native radio buttons.
        radio = shown(".human-option input")
        driver.execute_script("arguments[0].focus()", radio)
        radio.send_keys(" ")
        assert shown(".human-question-footer .human-primary").is_enabled()
        # Invalid stored options are never trusted as assessment evidence.
        driver.execute_script("localStorage.setItem('human3-questionnaire-progress', JSON.stringify({version:'human3-questionnaire-v1',index:0,answers:{'mind-orientation':'forged'}}))")
        driver.refresh()
        shown(".human-notice")
        assert not driver.execute_script("return localStorage.getItem('human3-questionnaire-progress')")
        driver.get(args.url.replace("/human3", "/projects"))
        click(".project-detail-card a[href='/human3']")
        shown(".human-welcome")
        print(json.dumps({"status": "passed", "checks": ["no default retention", "required answer", "back navigation", "resume on reload", "24-question completion", "report evidence", "markdown download", "completed report recovery", "answer edits", "clear and reload", "mobile overflow", "keyboard selection", "tampered storage rejected", "project entry"], "screenshots": str(output)}, ensure_ascii=False))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
