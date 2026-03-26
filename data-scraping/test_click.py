"""Test: Capture RSC response for a specific room to get full image data."""
import asyncio
import json
import re
import sys
from playwright.async_api import async_playwright

print = lambda *args, **kwargs: (sys.stdout.write(' '.join(str(a) for a in args) + kwargs.get('end', '\n')), sys.stdout.flush())

ACTION_GET_COLLEGES = "00c5c892dd885d8d752a185a2e0a2daf1816c31254"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        captured_rsc = []
        captured = {}

        async def on_response(response):
            action_id = response.request.headers.get("next-action", "")
            if action_id:
                try:
                    body = await response.text()
                    captured.setdefault(action_id, []).append(body)
                except:
                    pass
            # Capture RSC responses (room detail navigations)
            url = response.url
            if "_rsc=" in url or "room=" in url:
                try:
                    body = await response.text()
                    captured_rsc.append({"url": url, "body": body})
                except:
                    pass

        page.on("response", on_response)

        print("Log in...")
        await page.goto("https://roomviewer.hres.princeton.edu/")
        for _ in range(180):
            await asyncio.sleep(1)
            if ACTION_GET_COLLEGES in captured:
                break
        print("Logged in!\n")
        await asyncio.sleep(2)

        # Navigate directly to room 401 detail page
        print("Navigating to Little Hall Room 401...")
        captured_rsc.clear()
        url = "https://roomviewer.hres.princeton.edu/buildings?college=Upperclass&building=Little%20Hall&room=401"
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(3)

        print(f"\nCaptured {len(captured_rsc)} RSC responses")
        for rsc in captured_rsc:
            print(f"\n  URL: {rsc['url'][:120]}")
            body = rsc["body"]
            print(f"  Body length: {len(body)}")

            # Search for image URLs in the RSC response
            urls_found = re.findall(r'https://purv360s[^"\\]+', body)
            print(f"  Image URLs found: {len(urls_found)}")
            for u in urls_found:
                # Categorize
                if "Room_Plans" in u and "level_" not in u.split("/")[-1]:
                    cat = "ROOM_PLAN"
                elif "Room_Plans" in u:
                    cat = "FLOOR_PLAN"
                elif "images/" in u:
                    cat = "360"
                elif "Building_Photos" in u:
                    cat = "THUMBNAIL"
                else:
                    cat = "OTHER"
                print(f"    [{cat}] {u[:100]}")

            # Also look for room_plan references
            if "room_plan" in body:
                print("  Contains 'room_plan' reference!")
            if "floor_plan" in body:
                print("  Contains 'floor_plan' reference!")

        # Save full RSC bodies for analysis
        with open("/tmp/rsc_responses.json", "w") as f:
            json.dump(captured_rsc, f, indent=2)
        print(f"\nFull RSC data saved to /tmp/rsc_responses.json")

        await asyncio.sleep(5)
        await browser.close()

asyncio.run(main())
