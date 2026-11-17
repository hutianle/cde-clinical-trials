import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for width in [1280, 1440]:
            context = await browser.new_context(viewport={"width": width, "height": 900})
            page = await context.new_page()
            await page.goto("http://localhost:8000/index.html", timeout=15000)
            await page.wait_for_timeout(1000)
            
            # Switch to Database & Explorer tab
            await page.click("#tab-database-btn")
            await page.wait_for_timeout(1000)
            
            metrics = await page.evaluate("""() => {
                const wrapper = document.querySelector('#tab-database .overflow-x-auto');
                const table = wrapper.querySelector('table');
                const actionTh = table.querySelector('thead tr th:last-child');
                const firstActionBtn = table.querySelector('tbody tr:first-child td:last-child button');
                
                const wrapperRect = wrapper.getBoundingClientRect();
                const actionThRect = actionTh ? actionTh.getBoundingClientRect() : null;
                const btnRect = firstActionBtn ? firstActionBtn.getBoundingClientRect() : null;
                
                return {
                    viewportWidth: window.innerWidth,
                    wrapperScrollWidth: wrapper.scrollWidth,
                    wrapperClientWidth: wrapper.clientWidth,
                    hasHorizontalScrollbar: wrapper.scrollWidth > wrapper.clientWidth,
                    tableScrollWidth: table.scrollWidth,
                    tableClientWidth: table.clientWidth,
                    actionThVisible: actionThRect ? (actionThRect.right <= window.innerWidth && actionThRect.left >= 0) : false,
                    btnVisible: btnRect ? (btnRect.right <= window.innerWidth && btnRect.left >= 0) : false,
                    actionThRect: actionThRect,
                    btnRect: btnRect,
                    wrapperRect: wrapperRect
                };
            }""")
            
            print(f"\n=== Viewport {width}px ===")
            print(f"Wrapper ClientWidth: {metrics['wrapperClientWidth']}px | ScrollWidth: {metrics['wrapperScrollWidth']}px")
            print(f"Has Horizontal Scrollbar: {metrics['hasHorizontalScrollbar']}")
            print(f"Action Column Header fully in viewport: {metrics['actionThVisible']} (right edge: {metrics['actionThRect']['right']}px <= {width}px)")
            print(f"Action Button fully in viewport: {metrics['btnVisible']} (right edge: {metrics['btnRect']['right']}px <= {width}px)")
            
            await page.screenshot(path=f"web/table_{width}px.png")
            await context.close()
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
