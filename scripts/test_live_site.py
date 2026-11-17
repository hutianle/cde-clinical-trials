from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in [1280, 1440]:
        page = browser.new_page(viewport={'width': width, 'height': 800})
        page.goto('https://hutianle.github.io/cde-clinical-trials/', wait_until='networkidle')
        # Click on Database Explorer tab
        page.locator('#tab-database-btn').click()
        page.wait_for_selector('#database-table-body tr')
        
        # Check trial count and table horizontal scrollbar on wrapper
        metrics = page.evaluate('''() => {
            const wrapper = document.querySelector('#tab-database .overflow-x-auto');
            const actionHeader = document.querySelector('th:last-child');
            const actionBtn = document.querySelector('#database-table-body tr:first-child td:last-child button');
            const rect = actionBtn ? actionBtn.getBoundingClientRect() : null;
            const thRect = actionHeader ? actionHeader.getBoundingClientRect() : null;
            const totalCountText = document.querySelector('#stat-total-trials') ? document.querySelector('#stat-total-trials').textContent : '';
            return {
                totalCount: totalCountText,
                wrapperClientWidth: wrapper ? wrapper.clientWidth : 0,
                wrapperScrollWidth: wrapper ? wrapper.scrollWidth : 0,
                hasHorizontalScrollbar: wrapper ? wrapper.scrollWidth > wrapper.clientWidth : false,
                actionHeaderRight: thRect ? thRect.right : 0,
                actionBtnRight: rect ? rect.right : 0,
                windowInnerWidth: window.innerWidth
            };
        }''')
        print(f"=== Viewport {width}px ===")
        print(f"Total trials displayed: {metrics['totalCount']}")
        print(f"Wrapper ClientWidth: {metrics['wrapperClientWidth']}px, ScrollWidth: {metrics['wrapperScrollWidth']}px")
        print(f"Horizontal scrollbar present: {metrics['hasHorizontalScrollbar']}")
        print(f"Action Header right edge: {metrics['actionHeaderRight']}px <= {width}px: {metrics['actionHeaderRight'] <= width}")
        print(f"Action Button right edge: {metrics['actionBtnRight']}px <= {width}px: {metrics['actionBtnRight'] <= width}")
        assert not metrics['hasHorizontalScrollbar'], f"Horizontal scrollbar detected at {width}px!"
        assert metrics['actionBtnRight'] <= width, f"Action button overflows viewport at {width}px!"
    browser.close()
print("\nLIVE SITE VERIFICATION PASSED COMPLETELY!")
