#!/usr/bin/env python
"""
Sitemap Generator for VoltaireAI

One-time site map generation tool using Playwright.
Scans all interactive elements on a target page and outputs
the sitemap as JSON. Optionally uploads to the backend API.

Usage:
    python sitemap_generator.py --url https://example.com --output sitemap.json
    python sitemap_generator.py --url https://example.com --api-url http://localhost:8001 --name my_site

Requires: playwright (pip install playwright && playwright install chromium)
"""

import argparse
import json
import logging
import os
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_css_selector(element):
    """Generate a CSS selector for an element using Playwright's locator."""
    tag = element.get("tag", "").lower() if isinstance(element, dict) else ""
    if not tag:
        return "unknown"

    # Try to build a reasonable selector
    parts = []
    elem_id = element.get("id", "") if isinstance(element, dict) else ""
    if elem_id:
        return f"#{elem_id}"

    classes = element.get("classes", []) if isinstance(element, dict) else []
    if classes:
        return f"{tag}.{'.'.join(classes)}"

    return tag


def get_available_actions(tag_name, input_type, element_text):
    """Determine available actions for an element."""
    tag = tag_name.lower()
    actions = []

    if tag in ("button", "a", "option", "li", "td"):
        actions.append("click")
    elif tag == "input":
        if input_type in ("checkbox", "radio"):
            actions.append("toggle")
        elif input_type in ("submit", "button", "reset", "image"):
            actions.append("click")
        elif input_type in ("text", "password", "email", "number", "search", "tel", "url"):
            actions.append("fill")
        else:
            actions.append("fill")
    elif tag == "select":
        actions.append("select")
    elif tag == "textarea":
        actions.append("fill")

    # Any element with onclick or role=button can be clicked
    if not actions:
        actions.append("click")

    return actions


def scan_page(page):
    """
    Scan all interactive elements on the current page.

    Returns a list of element dicts compatible with the VoltaireAI API.
    """
    elements = page.evaluate(
        """
        () => {
            const results = [];
            const selectors = 'button, a, input, select, textarea, [role="button"], [role="link"], [tabindex], [onclick]';
            const seen = new Set();

            document.querySelectorAll(selectors).forEach((el, idx) => {
                if (idx >= 500) return;  // safety limit

                // Skip hidden elements
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) return;
                if (window.getComputedStyle(el).display === 'none') return;
                if (window.getComputedStyle(el).visibility === 'hidden') return;

                // Build CSS selector
                let selector = '';
                if (el.id) {
                    selector = '#' + CSS.escape(el.id);
                } else {
                    const classes = Array.from(el.classList).slice(0, 3).map(c => CSS.escape(c)).join('.');
                    selector = el.tagName.toLowerCase() + (classes ? '.' + classes : '');
                }

                // Deduplicate
                if (seen.has(selector)) return;
                seen.add(selector);

                const tag = el.tagName.toLowerCase();
                const type = el.getAttribute('type') || '';
                const text = (el.textContent || '').trim().substring(0, 150) || el.value || el.placeholder || '';
                const name = el.getAttribute('name') || '';
                const placeholder = el.getAttribute('placeholder') || '';
                const href = el.getAttribute('href') || '';
                const ariaLabel = el.getAttribute('aria-label') || '';
                const dataAttrs = {};
                for (const attr of el.attributes) {
                    if (attr.name.startsWith('data-')) {
                        dataAttrs[attr.name] = attr.value;
                    }
                }

                results.push({
                    id: 'elem_' + idx,
                    tag: tag,
                    type: type,
                    selector: selector,
                    text: text,
                    name: name,
                    placeholder: placeholder,
                    href: href,
                    aria_label: ariaLabel,
                    data_attrs: dataAttrs,
                    rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
                    actions: []  // filled by Python side
                });
            });
            return results;
        }
        """
    )

    # Fill in actions on Python side
    for elem in elements:
        elem["actions"] = get_available_actions(
            elem.get("tag", ""),
            elem.get("type", ""),
            elem.get("text", "")
        )

    return elements


def _get_llm():
    """Get LLM client from project if available, else None."""
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from llm.llm_client import get_llm_client
        client = get_llm_client()
        if client.is_available():
            return client
    except Exception:
        pass
    return None


def _llm_decide_explore(llm_client, elements, page_url, _progress, skip_indices=None):
    """
    Ask LLM to decide which elements should be clicked to discover more content.

    Args:
        llm_client: LLM client
        elements: List of element dicts
        page_url: Current page URL
        _progress: Progress callback
        skip_indices: Set of element indices to exclude (already clicked/expanded)

    Returns list of element indices to explore.
    """
    skip_indices = skip_indices or set()

    if not llm_client or len(elements) <= 1:
        # No LLM: explore all navigation-like elements (skip already clicked)
        nav_tags = {'a', 'button'}
        nav_texts = []
        for i, el in enumerate(elements):
            if i in skip_indices:
                continue
            tag = el.get('tag', '').lower()
            text = el.get('text', '')
            href = el.get('href', '')
            if tag in nav_tags and (text or href):
                nav_texts.append(i)
        return nav_texts[:30]

    # Build candidate list for LLM (limit to avoid token overflow)
    candidates = elements[:80]
    lines = []
    skip_info = []
    for i, el in enumerate(candidates):
        tag = el.get('tag', '')
        text = el.get('text', '')[:80]
        href = el.get('href', '')[:100]
        rect = el.get('rect', {})
        pos = f"({rect.get('x',0)},{rect.get('y',0)})" if rect else ""
        marker = " [已点击-勿选]" if i in skip_indices else ""
        lines.append(f"[{i}]{marker} tag={tag} text=\"{text}\" href=\"{href}\" pos={pos}")
        if i in skip_indices:
            skip_info.append(str(i))

    system = (
        "你是网页探索专家。分析当前页面上的可点击元素列表。"
        "识别哪些元素被点击后会导航到新页面、展开子菜单、切换标签页、"
        "或展示新的内容区域（这些都需要探索以发现更多页面元素）。"
        "排除：提交按钮、搜索按钮、删除按钮、关闭按钮、单纯的表单输入框、"
        "以及任何只会执行操作而不会展示新内容的元素。"
        "标记为[已点击-勿选]的元素是伸缩式菜单项，再次点击会收起已展开的内容，绝对不要选择。"
        "返回JSON: {\"explore_indices\": [0, 3, 5], \"reasoning\": \"简要说明\"}"
    )
    skip_hint = f"\n以下元素已点击过（伸缩菜单），再次点击会收起子菜单，请勿选择: [{', '.join(skip_info)}]" if skip_info else ""
    user = (
        f"当前页面: {page_url}\n"
        f"共 {len(candidates)} 个可交互元素，需要选出值得探索的：\n" +
        "\n".join(lines) + skip_hint
    )

    try:
        result = llm_client._call_llm(system, user)
        if result.startswith("LLM_ERROR:"):
            raise Exception(result)

        import re
        match = re.search(r"\{[\s\S]*\}", result)
        if match:
            data = json.loads(match.group())
            indices = data.get("explore_indices", [])
            indices = [i for i in indices if 0 <= i < len(candidates)]
            reasoning = data.get("reasoning", "")
            _progress("explore_llm", f"LLM选中 {len(indices)} 个导航元素: {reasoning[:100]}", {"count": len(indices)})
            return indices
    except Exception as e:
        logger.warning(f"LLM exploration decision failed: {e}")

    # Fallback: explore all links and buttons with text
    nav_texts = []
    for i, el in enumerate(elements[:80]):
        tag = el.get('tag', '').lower()
        text = el.get('text', '')
        if tag in ('a', 'button') and text:
            nav_texts.append(i)
    return nav_texts[:30]


def _click_element(page, element, _progress):
    """Try to click an element, return (success, opened_new_page, new_url)."""
    selector = element.get('selector', '')
    if not selector:
        return False, False, None

    old_url = page.url
    try:
        locator = page.locator(selector).first
        if not locator.is_visible(timeout=1000):
            # Try text-based matching
            text = element.get('text', '')[:50]
            if text:
                locator = page.get_by_text(text, exact=False).first
        locator.click(timeout=3000)
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception as e:
        logger.debug(f"Click failed for {selector}: {e}")
        return False, False, None

    time.sleep(0.5)
    new_url = page.url
    opened_new = (new_url != old_url)
    return True, opened_new, new_url


def _close_modal_or_popup(page):
    """Try to close any open modal/popup/dialog."""
    try:
        page.keyboard.press("Escape")
        time.sleep(0.3)
        page.wait_for_load_state("networkidle", timeout=3000)
        return True
    except Exception:
        return False


def _scan_page_elements(page):
    """
    Scan all visible interactive elements on the current page (JS evaluation).
    Returns list of element dicts with tag, type, selector, text, href, rect.
    Actions are filled in by caller.
    """
    elements = page.evaluate("""
        () => {
            const results = [];
            const selectors = 'button, a, input, select, textarea, [role="button"], [role="link"], [tabindex], [onclick]';
            const seen = new Set();
            let idx = 0;
            document.querySelectorAll(selectors).forEach((el) => {
                if (idx >= 500) return;
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) return;
                if (window.getComputedStyle(el).display === 'none') return;
                if (window.getComputedStyle(el).visibility === 'hidden') return;
                let selector = '';
                if (el.id) {
                    selector = '#' + CSS.escape(el.id);
                } else {
                    const classes = Array.from(el.classList).slice(0, 3).map(c => CSS.escape(c)).join('.');
                    selector = el.tagName.toLowerCase() + (classes ? '.' + classes : '');
                }
                if (seen.has(selector)) return;
                seen.add(selector);
                results.push({
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute('type') || '',
                    selector: selector,
                    text: (el.textContent || '').trim().substring(0, 150),
                    href: el.getAttribute('href') || '',
                    rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
                    actions: []
                });
                idx++;
            });
            return results;
        }
    """)
    for el in elements:
        el['actions'] = get_available_actions(el.get('tag', ''), el.get('type', ''), el.get('text', ''))
    return elements


def _register_elements(elements_list, source_url, all_elements, element_counter):
    """
    Register newly discovered elements into all_elements dict.
    Returns list of elements that are actually new (not already registered).
    """
    new_els = []
    for el in elements_list:
        sig = f"{el['tag']}|{el['selector']}|{el['text'][:60]}"
        if sig not in all_elements:
            el['id'] = f"elem_{element_counter[0]}"
            el['source_url'] = source_url
            all_elements[sig] = el
            element_counter[0] += 1
            new_els.append(el)
    return new_els


def _explore_level(page, url, depth, max_depth, llm_client, all_elements,
                   element_counter, visited_urls, total_clicks, max_total_clicks,
                   prog, clicked_sigs=None):
    """
    Recursively explore a page and its dynamically revealed content.

    After each click, re-scans the page for newly appeared elements (e.g.
    cascading menus that reveal sub-items). Continues recursively until
    max_depth is reached or max_total_clicks is exhausted.

    Tracks clicked element signatures to avoid re-clicking accordion menus
    that would collapse and hide sub-items.

    Args:
        page: Playwright page
        url: Current page URL
        depth: Current exploration depth (1-based)
        max_depth: Maximum depth
        llm_client: LLM client for exploration decisions
        all_elements: Dict of all discovered elements
        element_counter: Mutable counter [int] for element IDs
        visited_urls: Set of visited URLs
        total_clicks: Mutable counter [int] for click counting
        max_total_clicks: Max clicks limit
        prog: Progress callback function
        clicked_sigs: Set of element signatures already clicked (for accordion awareness)
    """
    if clicked_sigs is None:
        clicked_sigs = set()

    if depth > max_depth or total_clicks[0] >= max_total_clicks:
        return

    # Scan current page state
    page_elements = _scan_page_elements(page)
    new_els = _register_elements(page_elements, url, all_elements, element_counter)

    prog("explore_scan", f"深度{depth}: {len(new_els)} 个新元素, 总计 {len(all_elements)}",
         {"new": len(new_els), "total": len(all_elements), "depth": depth})

    if not page_elements or depth >= max_depth:
        return

    # Build skip_indices: elements whose sig is in clicked_sigs (accordion items)
    skip_indices = set()
    for i, el in enumerate(page_elements):
        sig = f"{el['tag']}|{el['selector']}|{el['text'][:60]}"
        if sig in clicked_sigs:
            skip_indices.add(i)
    if skip_indices:
        prog("explore_scan", f"跳过 {len(skip_indices)} 个已点击的伸缩菜单项 (避免再次点击收起)", {})

    # Ask LLM which elements to click (pass skip_indices so LLM avoids them)
    explore_indices = _llm_decide_explore(llm_client, page_elements, page.url, prog, skip_indices)
    if not explore_indices:
        return

    for idx in explore_indices:
        if total_clicks[0] >= max_total_clicks:
            return
        if idx >= len(page_elements):
            continue

        el = page_elements[idx]
        el_sig = f"{el['tag']}|{el['selector']}|{el['text'][:60]}"

        # Safety check: skip if already clicked (accordion toggle prevention)
        if el_sig in clicked_sigs:
            prog("explore_click", f"跳过已点击元素 (避免收起): {el.get('text','')[:60]}", {})
            continue

        total_clicks[0] += 1
        clicked_sigs.add(el_sig)  # Mark as clicked BEFORE the click

        prog("explore_click", f"[{total_clicks[0]}/{max_total_clicks}] 深度{depth} 点击: {el.get('text','')[:60]}",
             {"click": total_clicks[0], "text": el.get('text', '')[:60], "depth": depth})

        old_url = page.url
        success, opened_new, new_url = _click_element(page, el, prog)

        if not success:
            continue

        if opened_new and new_url:
            # --- URL navigation ---
            clean_new = new_url.split('#')[0]
            if clean_new not in visited_urls:
                visited_urls.add(clean_new)
                prog("explore_nav", f"发现新页面 (深度{depth+1}): {new_url[:100]}",
                     {"url": new_url, "depth": depth + 1})

                # Recursively explore the new page (fresh clicked_sigs for new URL)
                _explore_level(page, new_url, depth + 1, max_depth, llm_client,
                               all_elements, element_counter, visited_urls,
                               total_clicks, max_total_clicks, prog)

                # Navigate back to parent page
                try:
                    page.go_back(timeout=10000)
                    page.wait_for_load_state("networkidle", timeout=5000)
                    time.sleep(0.5)
                except Exception:
                    page.goto(url, timeout=10000, wait_until="networkidle")
                    time.sleep(0.5)

                # Re-scan after returning (page state may have changed)
                returned_els = _scan_page_elements(page)
                _register_elements(returned_els, url, all_elements, element_counter)
        else:
            # --- Same URL: SPA interaction (menu expand, tab switch, modal, etc.) ---
            time.sleep(0.5)

            # Re-scan for dynamically revealed elements
            after_click_els = _scan_page_elements(page)
            newly_appeared = _register_elements(after_click_els, url, all_elements, element_counter)

            if newly_appeared:
                prog("explore_new", f"点击 '{el.get('text','')[:40]}' 后出现 {len(newly_appeared)} 个新元素",
                     {"new_count": len(newly_appeared), "depth": depth})

                # Log first few new elements for debugging
                for ne in newly_appeared[:5]:
                    logger.info(f"  [NEW] {ne.get('tag','')} - {ne.get('text','')[:80]}")

                # Recursively explore the newly revealed content at depth+1
                # Pass clicked_sigs to avoid re-clicking accordion parents
                _explore_level(page, url, depth + 1, max_depth, llm_client,
                               all_elements, element_counter, visited_urls,
                               total_clicks, max_total_clicks, prog, clicked_sigs)

                # After exploring sub-branch, try to close nested menus/modals
                # Press Escape multiple times to unwind cascading menus
                for _ in range(min(depth + 1, 5)):
                    page.keyboard.press("Escape")
                    time.sleep(0.15)
                time.sleep(0.3)

                # Re-scan after unwinding to capture the parent-level state
                after_close_els = _scan_page_elements(page)
                _register_elements(after_close_els, url, all_elements, element_counter)

        time.sleep(0.3)


def explore_site(page, start_url, max_depth=3, max_total_clicks=80, _progress=None):
    """
    LLM-driven recursive site exploration.

    Discovers all interactive elements by recursively clicking through
    navigation, cascading menus, tabs, and modals. Re-scans the page
    after every click to capture dynamically revealed elements.

    Depth applies to both URL navigation AND SPA click chains.

    Args:
        page: Playwright page object
        start_url: Starting URL
        max_depth: Max exploration depth (URL nav + SPA click chains)
        max_total_clicks: Max total clicks across all pages
        _progress: Progress callback(step, message, data)

    Returns:
        List of all discovered elements with source_url metadata
    """
    def prog(step, msg, data=None):
        logger.info(f"[{step}] {msg}")
        if _progress:
            _progress(step, msg, data)

    llm_client = _get_llm()
    all_elements = {}
    visited_urls = set([start_url.split('#')[0]])
    total_clicks = [0]   # mutable list for pass-by-reference
    element_counter = [0]

    prog("explore_start", f"LLM智能递归探索 (max_depth={max_depth}, max_clicks={max_total_clicks}): {start_url}")

    _explore_level(page, start_url, 1, max_depth, llm_client, all_elements,
                   element_counter, visited_urls, total_clicks, max_total_clicks,
                   prog, clicked_sigs=set())

    prog("explore_done",
         f"探索完成: {len(all_elements)} 个元素, {len(visited_urls)} 个页面, {total_clicks[0]} 次点击",
         {"total_elements": len(all_elements), "pages": len(visited_urls), "clicks": total_clicks[0]})

    return list(all_elements.values())


def convert_to_api_format(elements, name="default"):
    """Convert scanned elements to VoltaireAI API format."""
    api_elements = []
    for elem in elements:
        api_elements.append({
            "id": elem.get("id", ""),
            "type": elem.get("tag", "element"),
            "selector": elem.get("selector", ""),
            "text": elem.get("text", ""),
            "position": {
                "x": elem.get("rect", {}).get("x", 0),
                "y": elem.get("rect", {}).get("y", 0),
            },
            "actions": elem.get("actions", []),
        })
    return {
        "category": "sitemap",
        "name": name,
        "elements": api_elements,
    }


def perform_login(page, login_url, target_url, username, password, login_submit_selector, manual_login, cookies_file, _progress):
    """
    Handle website login. Supports three modes:
    1. Cookies file: load cookies from file (fastest, no re-login needed)
    2. Credential login: auto-fill and submit
    3. Manual login: open visible browser, user logs in manually

    Returns True if login/cookies succeeded.
    """
    # Mode 1: Try loading cookies first
    if cookies_file and os.path.exists(cookies_file):
        _progress("login", f"从 {cookies_file} 加载已保存的登录凭证...")
        try:
            with open(cookies_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            page.context.add_cookies(cookies)
            _progress("login_done", "已从文件加载登录Cookie")
            return True
        except Exception as e:
            _progress("login", f"Cookie加载失败: {e}, 将尝试重新登录")

    # Manual login: navigate to login_url if provided, otherwise go to target_url
    if manual_login:
        nav_url = login_url or target_url
        if nav_url:
            _progress("login", f"正在导航到: {nav_url}...")
            page.goto(nav_url, timeout=30000, wait_until="networkidle")
            time.sleep(1)
        _progress("login", "请在浏览器窗口中手动完成登录操作...")
        logger.info("=" * 50)
        logger.info("MANUAL LOGIN: 请在浏览器窗口中完成登录操作")
        logger.info("等待登录完成（最多 180 秒）...")
        logger.info("=" * 50)

        # Wait for login by polling
        start_time = time.time()
        login_done = False
        last_url = page.url
        while time.time() - start_time < 180:
            try:
                current_url = page.url
                # Detection 1: URL changed (away from login/target page)
                if current_url != last_url:
                    _progress("login_done", "检测到页面跳转，登录可能成功")
                    login_done = True
                    time.sleep(1)  # Let page settle
                    break
                # Detection 2: User info elements appeared
                try:
                    if page.locator('.user-info, .avatar, .user-menu, .navbar-user, [data-user], .header-user, .user-name, .logged-in').first.is_visible(timeout=500):
                        _progress("login_done", "检测到用户信息元素，登录成功！")
                        login_done = True
                        break
                except Exception:
                    pass
            except Exception:
                pass
            time.sleep(1)

        if not login_done:
            _progress("login_done", "等待超时，将以当前状态继续扫描...")

        _progress("login_done", "继续扫描...")
        # Save cookies for future use
        if cookies_file:
            _save_cookies(page.context, cookies_file, _progress)
        return True

    # Mode 3: Auto credential login
    if username and password and login_submit_selector:
        _progress("login", "正在填写登录凭据...")

        # Try to find username field
        username_selectors = [
            'input[name="username"]', 'input[name="user"]', 'input[name="login"]',
            'input[name="account"]', 'input[name="phone"]', 'input[name="mobile"]',
            'input[type="text"]', 'input[placeholder*="账号"]', 'input[placeholder*="用户名"]',
            'input[placeholder*="手机"]', 'input[placeholder*="邮箱"]', 'input[placeholder*="email"]',
            '#username', '#user', '#login', '#account',
        ]
        username_el = None
        for sel in username_selectors:
            try:
                username_el = page.locator(sel).first
                if username_el.is_visible():
                    break
                username_el = None
            except Exception:
                continue

        if username_el:
            username_el.fill(username)
            _progress("login", "已填写用户名")
        else:
            _progress("login", "未找到用户名输入框，尝试按tab键选择第一个输入框")

        time.sleep(0.5)

        # Try to find password field
        password_selectors = [
            'input[name="password"]', 'input[name="pwd"]', 'input[name="pass"]',
            'input[type="password"]', 'input[placeholder*="密码"]',
            '#password', '#pwd', '#pass',
        ]
        password_el = None
        for sel in password_selectors:
            try:
                password_el = page.locator(sel).first
                if password_el.is_visible():
                    break
                password_el = None
            except Exception:
                continue

        if password_el:
            password_el.fill(password)
            _progress("login", "已填写密码")
        else:
            _progress("login", "未找到密码输入框")

        time.sleep(0.5)

        # Click submit
        _progress("login", "正在提交登录...")
        submit_clicked = False
        try:
            page.locator(login_submit_selector).first.click()
            submit_clicked = True
        except Exception:
            pass

        if not submit_clicked:
            # Try common submit selectors
            submit_selectors = [
                'button[type="submit"]', 'input[type="submit"]',
                'button:has-text("登录")', 'button:has-text("登錄")',
                'button:has-text("Login")', 'button:has-text("Sign in")',
                'a:has-text("登录")', '[role="button"]:has-text("登录")',
            ]
            for sel in submit_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible():
                        el.click()
                        submit_clicked = True
                        break
                except Exception:
                    continue

        if not submit_clicked:
            # Last resort: press Enter
            page.keyboard.press("Enter")

        # Wait for login to complete
        time.sleep(3)
        page.wait_for_load_state("networkidle")

        _progress("login_done", "登录完成")

        # Save cookies for future use
        if cookies_file:
            _save_cookies(page.context, cookies_file, _progress)

        return True

    return False


def _save_cookies(context, cookies_file, _progress):
    """Save browser cookies to file for future reuse."""
    try:
        cookies = context.cookies()
        os.makedirs(os.path.dirname(cookies_file) or ".", exist_ok=True)
        with open(cookies_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        _progress("login", f"登录凭证已保存到 {cookies_file}")
    except Exception as e:
        logger.warning(f"Failed to save cookies: {e}")


def generate_sitemap(
    url: str,
    name: str = "default",
    timeout: int = 30,
    wait: int = 2,
    headless: bool = True,
    upload_to_api: str = None,
    output_file: str = None,
    progress_callback=None,
    login_url: str = None,
    username: str = None,
    password: str = None,
    login_submit_selector: str = None,
    manual_login: bool = False,
    cookies_file: str = None,
    explore: bool = True,
    max_depth: int = 5,
    max_total_clicks: int = 80,
):
    """
    Generate sitemap by scanning the target URL with Playwright.

    Args:
        url: Target website URL
        name: Collection name in knowledge base
        timeout: Page load timeout in seconds
        wait: Extra wait time after page load
        headless: Run browser in headless mode
        upload_to_api: Optional API base URL for auto-upload
        output_file: Optional file path to save JSON output
        progress_callback: Optional callable(step, message, data) for progress updates
        login_url: URL of the login page (if authentication required)
        username: Login username
        password: Login password
        login_submit_selector: CSS selector for the login submit button
        manual_login: If True, opens visible browser and waits for user to log in manually
        cookies_file: Path to save/load cookies for future logins
        explore: If True, use LLM-driven recursive exploration; False = single-page scan
        max_depth: Max exploration depth (URL nav + SPA click chains, default 5)
        max_total_clicks: Max total clicks during exploration (default 80)

    Returns:
        Dict with status, element_count, elements, tag_counts
    """
    def _progress(step, message, data=None):
        logger.info(f"[{step}] {message}")
        if progress_callback:
            progress_callback(step, message, data)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        msg = "Playwright not installed. Run: pip install playwright && playwright install chromium"
        _progress("error", msg)
        return {"status": "error", "message": msg}

    _progress("init", f"正在启动浏览器...", {"url": url, "name": name})

    # Manual login requires visible browser
    if manual_login:
        headless = False

    with sync_playwright() as p:
        _progress("launch", "正在启动 Chromium 浏览器...")
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            # Handle login if needed
            need_login = login_url or manual_login or (username and password)
            if need_login:
                logged_in = perform_login(
                    page, login_url, url, username, password,
                    login_submit_selector, manual_login, cookies_file, _progress
                )
                if not logged_in and not cookies_file:
                    _progress("login", "登录未成功，将以未登录状态继续扫描")

            _progress("navigate", f"正在加载页面: {url}...")
            page.goto(url, timeout=timeout * 1000, wait_until="networkidle")

            # Extra wait for dynamic content
            if wait > 0:
                _progress("wait", f"等待动态内容加载 ({wait}秒)...")
                time.sleep(wait)

            _progress("scan", "正在扫描页面可交互元素...")
            if explore:
                elements = explore_site(
                    page, url, max_depth=max_depth,
                    max_total_clicks=max_total_clicks, _progress=_progress
                )
            else:
                elements = scan_page(page)
                _progress("scan_done", f"扫描完成，发现 {len(elements)} 个可交互元素", {"count": len(elements)})

            # Build output
            output_data = {
                "url": url,
                "name": name,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "element_count": len(elements),
                "elements": elements,
            }

            # Save to file if requested
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                _progress("saved", f"已保存到文件: {output_file}")

            # Upload to API if requested
            if upload_to_api:
                _progress("upload", "正在上传到知识库...")
                api_url = upload_to_api.rstrip("/") + "/VoltaireAI/upload-dom"
                api_data = convert_to_api_format(elements, name)

                import urllib.request
                import urllib.error

                req = urllib.request.Request(
                    api_url,
                    data=json.dumps(api_data).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        result = json.loads(resp.read().decode("utf-8"))
                        _progress("upload_done", f"已上传到知识库: {result.get('message', 'success')}", result)
                except urllib.error.URLError as e:
                    _progress("error", f"上传失败: {e}")

            # Compute tag summary
            tag_counts = {}
            for elem in elements:
                tag = elem.get("tag", "unknown")
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            _progress("done", f"站点地图生成完成: {len(elements)} 个元素", {
                "element_count": len(elements),
                "tag_counts": tag_counts,
                "name": name,
            })

            return {
                "status": "success",
                "element_count": len(elements),
                "elements": elements,
                "tag_counts": tag_counts,
                "output": output_file or "none",
            }

        except Exception as e:
            _progress("error", f"生成失败: {str(e)}")
            return {"status": "error", "message": str(e)}
        finally:
            browser.close()
            _progress("close", "浏览器已关闭")


def main():
    parser = argparse.ArgumentParser(description="VoltaireAI Sitemap Generator")
    parser.add_argument("--url", required=True, help="Target website URL to scan")
    parser.add_argument("--output", default=None, help="Output JSON file path")
    parser.add_argument("--api-url", default=None, help="Backend API base URL for auto-upload")
    parser.add_argument("--name", default="default", help="Collection name in knowledge base")
    parser.add_argument("--timeout", type=int, default=30, help="Page load timeout in seconds")
    parser.add_argument("--wait", type=int, default=2, help="Extra wait time after page load (seconds)")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode")
    parser.add_argument("--no-headless", action="store_true", help="Run with visible browser window")
    args = parser.parse_args()

    headless = not args.no_headless

    def cli_progress(step, message, data=None):
        pass  # Logger already handles it

    result = generate_sitemap(
        url=args.url,
        name=args.name,
        timeout=args.timeout,
        wait=args.wait,
        headless=headless,
        upload_to_api=args.api_url,
        output_file=args.output,
        progress_callback=cli_progress,
    )

    print(json.dumps({"status": result.get("status"), "element_count": result.get("element_count", 0), "output": args.output or "none"}))


if __name__ == "__main__":
    main()
