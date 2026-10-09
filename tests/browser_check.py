from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://localhost:5173/traces")
    page.wait_for_load_state("networkidle")
    page.screenshot(path="artifacts/traces-desktop.png", full_page=True)
    assert page.get_by_text("执行记录").count() >= 1
    assert page.get_by_text("Knowledge QA").count() >= 1
    page.locator("tbody tr").nth(1).click()
    page.wait_for_selector("text=父子调用链")
    assert page.get_by_text("父子调用链").count() == 1
    page.screenshot(path="artifacts/detail-desktop.png", full_page=True)
    page.get_by_text("Call knowledge tool").first.click()
    assert page.get_by_text("knowledge tool timed out after 250ms").count() >= 1
    page.go_back()
    page.wait_for_load_state("networkidle")
    page.locator("nav button").nth(1).click()
    page.wait_for_load_state("networkidle")
    page.screenshot(path="artifacts/stats-desktop.png", full_page=True)
    assert page.get_by_text("运行统计").count() >= 1
    mobile = browser.new_page(viewport={"width": 390, "height": 844})
    mobile.goto("http://localhost:5173/traces")
    mobile.wait_for_load_state("networkidle")
    mobile.screenshot(path="artifacts/traces-mobile.png", full_page=True)
    assert mobile.locator("body").evaluate("el => el.scrollWidth <= el.clientWidth")
    browser.close()
