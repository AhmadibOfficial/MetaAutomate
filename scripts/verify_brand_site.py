#!/usr/bin/env python3
"""MetaAutomate global business experience: real Chromium desktop/mobile acceptance.

No cloud deployment, backend, tokens or API calls. Every request must target
the local static HTTP test server.
"""
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:18080"
ART = Path("artifacts")
ART.mkdir(exist_ok=True)


def assert_no_horizontal_overflow(page, name):
    dimensions = page.evaluate(
        "() => ({scroll:document.documentElement.scrollWidth, width:innerWidth})"
    )
    assert dimensions["scroll"] <= dimensions["width"]+1, (name, dimensions)


def inspect_asset(page):
    expect(page.locator(".brand img").first).to_be_visible()
    assert page.locator(".brand img").first.evaluate(
        "(img) => img.complete && img.naturalWidth > 0"
    ), "Official MetaAutomate mark unavailable"


def assert_text_contrast(page, selector, minimum=4.5):
    """Check solid backgrounds or both ends of a CSS gradient, not a WCAG audit."""
    ratios = page.locator(selector).first.evaluate("""el => {
      const style = getComputedStyle(el);
      const parse = value => {
        const match = value.match(/rgba?\\(([^)]+)\\)/);
        if (!match) return null;
        return match[1].split(',').slice(0, 3).map(v => Number.parseFloat(v));
      };
      const luminance = rgb => {
        const transformed = rgb.map(x => {
          const a = x / 255;
          return a <= 0.04045 ? a / 12.92 : ((a + 0.055) / 1.055) ** 2.4;
        });
        return transformed[0]*0.2126 + transformed[1]*0.7152 + transformed[2]*0.0722;
      };
      const foreground = parse(style.color);
      const gradientStops = [...style.backgroundImage.matchAll(/rgba?\\([^)]+\\)/g)]
        .map(m => parse(m[0])).filter(Boolean);
      const solid = parse(style.backgroundColor);
      const palette = gradientStops.length ? gradientStops : [solid];
      if (!foreground || palette.some(x => !x || x.length !== 3)) return [];
      const f = luminance(foreground);
      return palette.map(x => {
        const b = luminance(x);
        return (Math.max(f, b) + 0.05) / (Math.min(f, b) + 0.05);
      });
    }""")
    assert ratios and min(ratios) >= minimum, (selector, ratios, minimum)
    return min(ratios)


def main():
    bad_requests = []
    page_errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        desktop = browser.new_context(
            viewport={"width": 1440, "height": 940},
            device_scale_factor=1, reduced_motion="reduce",
            accept_downloads=True,
        )
        page = desktop.new_page()
        page.on("request", lambda request: (
            bad_requests.append(request.url)
            if not request.url.startswith(BASE) else None
        ))
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        # Home: flagship brand and intelligent-system interaction.
        response = page.goto(BASE+"/", wait_until="networkidle")
        assert response.status == 200
        expect(page).to_have_title("MetaAutomate — Smarter Systems for Business Challenges")
        expect(page.get_by_role("heading", level=1)).to_contain_text("Business challenges deserve")
        expect(page.locator("#solutions .clarity-card")).to_have_count(3)
        # Nine mapped capabilities are present, compact and link to real service disciplines.
        expect(page.locator(".capability-card")).to_have_count(9)
        expect(page.locator(".capability-card").first).to_contain_text("AI Agents & Orchestration")
        expect(page.locator(".capability-card").last).to_contain_text("Islamic Knowledge Systems")
        expect(page.locator(".capability-disclaimer")).to_contain_text("not nine live products")
        expect(page.locator(".clarity-audiences span")).to_have_count(4)
        expect(page.locator(".hero-availability")).to_contain_text("in development")
        expect(page.get_by_role("link", name="Explore solutions")).to_have_attribute("href", "#solutions")
        expect(page.get_by_role("link", name="Explore our planning approach")).to_have_attribute("href", "#workspace-demo")
        assert page.evaluate("""() => {
          const a = document.querySelector('#solutions').getBoundingClientRect().top + scrollY;
          const b = document.querySelector('#workspace-demo').getBoundingClientRect().top + scrollY;
          const c = document.querySelector('#services').getBoundingClientRect().top + scrollY;
          return a < b && b < c;
        }"""), "Example should appear before the services and industry catalogs"
        # High-risk CTA and label contrast measured from computed browser colors.
        assert_text_contrast(page, ".hero-home .action-primary")
        assert_text_contrast(page, ".site-navigation .nav-action")
        # Contrast for text on white solution cards.
        contrast = page.locator(".clarity-card .clarity-index").first.evaluate("""el => {
          const nums = getComputedStyle(el).color.match(/\\d+/g).slice(0,3).map(Number);
          const linear = nums.map(v => {
            const c = v/255;
            return c <= 0.04045 ? c/12.92 : ((c+0.055)/1.055)**2.4;
          });
          return 1.05/(0.05 + linear[0]*0.2126 + linear[1]*0.7152 + linear[2]*0.0722);
        }""")
        assert contrast >= 4.5, ("Solution labels should meet normal-text AA contrast", contrast)
        expect(page.locator("#workspace-demo")).to_be_visible()
        expect(page.locator(".workspace-board-status")).to_contain_text("PLANNING EXPERIENCE")
        expect(page.locator(".workspace-board-foot")).to_contain_text("Guided planning scenario")
        demo_buttons = page.locator("[data-workspace-step]")
        expect(demo_buttons).to_have_count(3)
        expect(demo_buttons.nth(0)).to_have_attribute("aria-pressed", "true")
        demo_buttons.nth(1).focus()
        demo_buttons.nth(1).press("Enter")
        expect(page.locator("#workspace-stage-title")).to_have_text("Identify what needs to happen first.")
        expect(demo_buttons.nth(1)).to_have_attribute("aria-pressed", "true")
        expect(demo_buttons.nth(0)).to_have_attribute("aria-pressed", "false")
        demo_buttons.nth(2).focus()
        demo_buttons.nth(2).press("Space")
        expect(page.locator("#workspace-stage-description")).to_contain_text("No supplier message")
        expect(page.locator("#workspace-demo")).to_contain_text("illustrative information")
        expect(page.locator(".capability-card")).to_have_count(9)
        expect(page.locator(".focus-sector-card")).to_have_count(7)
        for sector in ("Retail", "Wholesale", "Transportation", "Logistics",
                       "Tourism", "Education", "Healthcare"):
            expect(page.locator("#industries")).to_contain_text(sector)
        expect(page.locator("#industries .industry-scope")).to_contain_text("not deployed sector products")
        expect(page.locator(".proof-section")).to_have_count(0)
        expect(page.locator(".social-card")).to_have_count(2)
        expect(page.locator(".statement-section")).to_contain_text("Always HALAL")
        inspect_asset(page)
        tabs=page.get_by_role("tab")
        expect(tabs).to_have_count(7)
        expect(page.locator("#operation-counter")).to_have_text("01 / 07")
        expect(page.locator("#operation-title")).to_have_text("Start with the objective.")
        # Every new stage has its own description and is keyboard accessible.
        tabs.nth(0).press("ArrowRight")
        expect(page.locator("#tab-think")).to_be_focused()
        expect(page.locator("#operation-title")).to_have_text("Think before we build.")
        expect(page.locator("#operation-counter")).to_have_text("02 / 07")
        tabs.nth(2).click()
        expect(page.locator("#operation-title")).to_have_text("Engineer the right system.")
        tabs.nth(3).click()
        expect(page.locator("#operation-title")).to_have_text("Make the solution real.")
        expect(page.locator("#tab-create")).to_have_attribute("aria-selected", "true")
        tabs.nth(3).press("ArrowRight")
        expect(page.locator("#operation-title")).to_have_text("Make repeatable work simpler.")
        expect(page.locator("#tab-automate")).to_be_focused()
        expect(page.locator("#operation-description")).to_contain_text("human authorization")
        tabs.nth(4).press("ArrowRight")
        expect(page.locator("#operation-title")).to_have_text("Prove what the system does.")
        expect(page.locator("#tab-verify")).to_be_focused()
        tabs.nth(5).press("End")
        expect(page.locator("#tab-improve")).to_be_focused()
        expect(page.locator("#operation-counter")).to_have_text("07 / 07")
        tabs.nth(6).press("Home")
        expect(page.locator("#tab-understand")).to_be_focused()
        # Selected business example follows the active engineering stage;
        # changing scenarios never sends customer data or performs live actions.
        use_cases = page.locator(".use-case-option")
        expect(use_cases).to_have_count(3)
        expect(use_cases.nth(0)).to_have_attribute("aria-pressed", "true")
        expect(page.locator("#use-case-stage")).to_have_text("01 / UNDERSTAND")
        expect(page.locator("#use-case-detail-title")).to_have_text("Inventory & purchasing")
        tabs.nth(4).click()
        expect(page.locator("#use-case-stage")).to_have_text("05 / AUTOMATE")
        expect(page.locator("#use-case-stage-description")).to_contain_text("send nothing")
        use_cases.nth(1).click()
        expect(use_cases.nth(1)).to_have_attribute("aria-pressed", "true")
        expect(use_cases.nth(0)).to_have_attribute("aria-pressed", "false")
        expect(page.locator("#use-case-detail-title")).to_have_text("Content & client engagement")
        expect(page.locator("#use-case-stage-description")).to_contain_text("do not publish")
        tabs.nth(5).click()
        expect(page.locator("#use-case-stage-description")).to_contain_text("image rights")
        use_cases.nth(2).focus()
        use_cases.nth(2).press("Enter")
        expect(use_cases.nth(2)).to_have_attribute("aria-pressed", "true")
        expect(page.locator("#use-case-stage-description")).to_contain_text("permissions")
        assert_no_horizontal_overflow(page, "desktop home")
        page.goto(BASE+"/", wait_until="networkidle")
        # Official social presence: exact addresses, secure external-link behavior.
        expected_socials = {
            "YouTube": "https://youtube.com/@MetaAutomate",
            "LinkedIn": "https://www.linkedin.com/company/meta-automate",
            "Instagram": "https://instagram.com/meta_automate",
            "X / Twitter": "https://twitter.com/MetaAutomate",
            "Facebook": "https://facebook.com/MetaAutomate",
            "TikTok": "https://tiktok.com/@metaautomate",
            "WhatsApp Channel": "https://whatsapp.com/channel/0029VbDSQMdBqbr1vqRyYR2U",
            "Telegram": "https://t.me/Meta_Automate",
        }
        expect(page.locator(".social-card")).to_have_count(2)
        for label in ("YouTube", "LinkedIn"):
            card = page.get_by_role("link", name=f"Visit MetaAutomate on {label} — opens in a new tab")
            expect(card).to_have_attribute("href", expected_socials[label])
            expect(card).to_have_attribute("target", "_blank")
            expect(card).to_have_attribute("rel", "noopener noreferrer")
        assert sorted(page.locator(".footer-social-link").evaluate_all(
            "(links) => links.map(link => link.href)"
        )) == sorted(expected_socials.values())
        expect(page.locator(".footer-social-link")).to_have_count(8)
        for page_path in ("/services/", "/company/", "/engage/"):
            page.goto(BASE + page_path, wait_until="networkidle")
            footer_links=page.locator(".footer-social-link")
            expect(footer_links).to_have_count(8)
            assert sorted(footer_links.evaluate_all("(links)=>links.map(link=>link.href)")) == sorted(expected_socials.values())
            contact = page.locator(".footer-contact-email")
            expect(contact).to_have_count(1)
            expect(contact).to_contain_text("metaautomating@gmail.com")
            expect(contact).to_have_attribute(
                "href", "mailto:metaautomating@gmail.com?subject=MetaAutomate%20%7C%20Business%20inquiry"
            )

        page.goto(BASE + "/", wait_until="networkidle")
        page.screenshot(path=str(ART/"metaautomate-global-home-desktop.png"), full_page=True)

        # Service catalog is addressable and routes to a real on-device brief.
        services=page.goto(BASE+"/services/", wait_until="networkidle")
        assert services.status == 200
        expect(page.locator(".discipline")).to_have_count(6)
        expect(page.locator("#software")).to_contain_text("Software &")
        inspect_asset(page)
        assert_no_horizontal_overflow(page, "desktop services")
        page.screenshot(path=str(ART/"metaautomate-global-services-desktop.png"), full_page=True)
        page.locator("#software .discipline-action").click()
        assert "/engage/" in page.url
        expect(page.locator("#brief-service")).to_have_value("Software & Digital Products")

        # Brand values and roadmap are presented without claiming shipped features.
        page.goto(BASE+"/company/", wait_until="networkidle")
        expect(page.locator(".roadmap-entry").nth(2)).to_contain_text("WORKFLOW DESIGN")
        expect(page.locator(".roadmap-entry").nth(2)).to_contain_text("VALIDATION")
        expect(page.locator(".roadmap-entry").nth(2)).to_contain_text("Customer activation follows independent security and operational review")
        expect(page.locator(".roadmap-note")).to_contain_text("Our roadmap describes active engineering")
        expect(page.locator(".roadmap-note")).to_contain_text("Customer access, provider integrations")
        expect(page.locator(".purpose-panel")).to_have_count(2)
        expect(page.locator(".value-principles article")).to_have_count(5)
        expect(page.locator(".principle-halal")).to_contain_text("Always HALAL")
        expect(page.locator(".brand-meaning div")).to_have_count(5)
        expect(page.locator(".roadmap-entry")).to_have_count(4)
        expect(page.locator(".roadmap-entry").first).to_contain_text("ENGINEERING FOUNDATION IN PROGRESS")
        expect(page.locator(".roadmap-horizon")).to_contain_text("A Better World.")
        expect(page.locator(".roadmap-horizon")).to_contain_text("OUR LONG-TERM AMBITION")
        assert_no_horizontal_overflow(page, "desktop company")
        page.screenshot(path=str(ART/"metaautomate-global-company-desktop.png"), full_page=True)

        # Blue Start a Project experience replaces the removed structured form.
        page.goto(BASE+"/engage/",wait_until="networkidle")
        expect(page.get_by_role("heading",level=1)).to_have_text(
            "What would you like to build today?")
        assert page.locator("#brief-form").count()==0
        expect(page.locator("#project-chat-input")).to_be_visible()
        toggle=page.locator("#workspace-sidebar-toggle")
        expect(toggle).to_have_attribute("aria-expanded","true")
        toggle.click()
        expect(page.locator("#project-workspace-side")).to_be_hidden()
        toggle.click()
        expect(page.locator("#project-workspace-side")).to_be_visible()
        page.locator("#project-chat-suggestions [data-project-template=creative]").click()
        page.locator("#project-chat-send").click()
        expect(page.locator("#project-chat-progress")).to_contain_text("Step 2 of 5")
        expect(page.locator("#project-chat-email")).to_have_attribute(
            "href", "mailto:metaautomating@gmail.com?subject=MetaAutomate%20%7C%20Project%20inquiry")
        page.screenshot(path=str(ART/"metaautomate-global-project-chat-blue.png"),
                        full_page=True)
        assert_no_horizontal_overflow(page,"blue project chat")

        # Mobile: navigation and all four pages, 390px and narrower 360px.
        for width in (390, 360):
            mobile = browser.new_context(
                viewport={"width": width,"height": 844},
                device_scale_factor=1, is_mobile=True, has_touch=True,
                reduced_motion="reduce",
            )
            mpage=mobile.new_page()
            mpage.on("request", lambda request: (
                bad_requests.append(request.url)
                if not request.url.startswith(BASE) else None
            ))
            mpage.on("pageerror", lambda error: page_errors.append(str(error)))
            for path in ("/","/services/","/company/","/engage/"):
                mpage.goto(BASE+path,wait_until="networkidle")
                if path=="/engage/":
                    expect(mpage.locator("#workspace-sidebar-toggle")).to_be_visible()
                    expect(mpage.locator("#project-chat-input")).to_be_visible()
                    assert mpage.locator("#brief-form").count()==0
                    logo=mpage.locator(".project-chat-side-title img")
                    assert logo.evaluate(
                        "(img) => img.complete && img.naturalWidth > 0"
                    )
                    mpage.locator("#workspace-sidebar-toggle").click()
                    expect(mpage.locator("#project-workspace-side")).to_be_visible()
                    mpage.keyboard.press("Escape")
                    expect(mpage.locator("#project-workspace-side")).to_be_hidden()
                else:
                    inspect_asset(mpage)
                    expect(mpage.locator(".footer-contact-email")).to_have_count(1)
                    social_links = mpage.locator(".footer-social-link")
                    expect(social_links).to_have_count(8)
                    assert sorted(social_links.evaluate_all(
                        "(links) => links.map(link => link.href)"
                    )) == sorted(expected_socials.values())
                assert_no_horizontal_overflow(mpage, f"mobile {width} {path}")
                if path == "/":
                    expect(mpage.locator(".social-card")).to_have_count(2)
                    expect(mpage.locator(".clarity-card")).to_have_count(3)
                    expect(mpage.locator(".workspace-node")).to_have_count(4)
                    if width == 390:
                        page_height = mpage.evaluate("() => document.documentElement.scrollHeight")
                        assert page_height < 13200, ("Reduce mobile homepage scrolling", page_height)
                        print(f"MOBILE_HOME_HEIGHT_390={page_height}")
                    demo = mpage.locator("[data-workspace-step]")
                    demo.nth(1).click()
                    expect(mpage.locator("#workspace-stage-index")).to_have_text("STEP 02 / MAP")


            mpage.goto(BASE+"/",wait_until="networkidle")
            # Focus/skip-link affordance remains reachable on narrow screens.
            mpage.keyboard.press("Tab")
            expect(mpage.locator(".skip-link")).to_be_focused()
            mpage.keyboard.press("Enter")
            assert mpage.evaluate("location.hash") == "#main"
            menu=mpage.locator("#menu-button")
            expect(mpage.locator("#site-navigation")).to_be_hidden()
            menu.click()
            expect(menu).to_have_attribute("aria-expanded","true")
            expect(mpage.locator("#site-navigation")).to_be_visible()
            mpage.get_by_role("link", name="Services", exact=True).first.click()
            expect(mpage).to_have_url(BASE+"/services/")
            expect(menu).to_have_attribute("aria-expanded","false")
            expect(mpage.locator("#site-navigation")).to_be_hidden()
            mpage.goto(BASE+"/",wait_until="networkidle")
            if width==390:
                mpage.screenshot(path=str(ART/"metaautomate-global-home-mobile.png"),full_page=True)
            if width==360:
                mpage.screenshot(path=str(ART/"metaautomate-global-home-mobile-360.png"),full_page=True)
            mobile.close()

        # Portrait tablet visual and horizontal-overflow check.
        tablet = browser.new_context(
            viewport={"width": 768, "height": 1024},
            device_scale_factor=1, reduced_motion="reduce",
        )
        tpage = tablet.new_page()
        tpage.on("request", lambda request: (
            bad_requests.append(request.url)
            if not request.url.startswith(BASE) else None
        ))
        tpage.on("pageerror", lambda error: page_errors.append(str(error)))
        tpage.goto(BASE + "/", wait_until="networkidle")
        inspect_asset(tpage)
        assert_no_horizontal_overflow(tpage, "tablet 768 home")
        expect(tpage.locator("#workspace-demo")).to_be_visible()
        tpage.screenshot(
            path=str(ART/"metaautomate-global-home-tablet-768.png"), full_page=True,
        )
        tablet.close()

        assert not bad_requests, f"Unexpected third-party HTTP requests: {bad_requests}"
        assert not page_errors, f"Browser JavaScript errors: {page_errors}"
        browser.close()
    print("PASS: business value-led hero, early synthetic walkthrough, condensed mobile, tablet 768, mobile 390/360, blue project workspace, secure branding and no external requests")


if __name__=="__main__":
    main()
