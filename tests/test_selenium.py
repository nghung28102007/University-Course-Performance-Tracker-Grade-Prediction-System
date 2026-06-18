"""
SP7: Selenium automated testing for login form data entry.
Run: pytest tests/test_selenium.py -v
Requires: pip install selenium; Chrome/Chromium installed.
"""
import os
import sys
import time
import threading
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

import config
from app import app as flask_app


def _run_server():
    flask_app.run(host=config.HOST, port=config.PORT + 1, debug=False, use_reloader=False)


@pytest.fixture(scope="module")
def live_server():
    if not HAS_SELENIUM:
        pytest.skip("selenium not installed")
    thread = threading.Thread(target=_run_server, daemon=True)
    thread.start()
    time.sleep(2)
    yield f"http://{config.HOST}:{config.PORT + 1}"
    # daemon thread stops with process


@pytest.fixture
def browser(live_server):
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(5)
    yield driver
    driver.quit()


@pytest.mark.skipif(not HAS_SELENIUM, reason="selenium not installed")
def test_login_form_submission(browser, live_server):
    """Selenium: fill login form and verify redirect to dashboard."""
    browser.get(f"{live_server}/login")
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, "login-form")))

    browser.find_element(By.ID, "login-name").clear()
    browser.find_element(By.ID, "login-name").send_keys("Test User")
    Select(browser.find_element(By.ID, "login-role")).select_by_value("admin")
    browser.find_element(By.ID, "login-submit").click()

    WebDriverWait(browser, 10).until(EC.url_contains("/"))
    assert "Performance Dashboard" in browser.page_source or "Dashboard" in browser.page_source


@pytest.mark.skipif(not HAS_SELENIUM, reason="selenium not installed")
def test_dashboard_navigation(browser, live_server):
    """Selenium: navigate to Students page after login."""
    browser.get(f"{live_server}/login")
    browser.find_element(By.ID, "login-name").send_keys("Admin")
    Select(browser.find_element(By.ID, "login-role")).select_by_value("admin")
    browser.find_element(By.ID, "login-submit").click()
    time.sleep(1)

    browser.get(f"{live_server}/students")
    assert "Students" in browser.page_source or "student" in browser.page_source.lower()
