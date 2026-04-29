from playwright.sync_api import Page
from config import LOGIN_URL, TIMEOUTS


def login(page: Page, email: str, password: str) -> None:
    page.goto(LOGIN_URL)
    page.wait_for_selector('[name="email"], [type="email"]', timeout=10_000)

    page.locator('[name="email"], [type="email"]').first.fill(email)
    page.locator('[name="password"], [type="password"]').first.fill(password)
    page.locator('[type="submit"], button:has-text("Entrar"), button:has-text("Login")').first.click()

    page.wait_for_function(
        "() => !window.location.pathname.includes('/login')",
        timeout=TIMEOUTS["login"],
    )
