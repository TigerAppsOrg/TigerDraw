"""
Scrape room data from Princeton's Room Viewer (roomviewer.hres.princeton.edu).

Usage:
    pip install playwright && playwright install chromium
    python scrape_roomviewer.py

1. Opens browser — log in via CAS
2. Auto-navigates through every building AND every room detail page
3. Captures full image data (360, floor plan, room plan) from RSC responses
4. Outputs CSV + image JSON files
"""

import asyncio
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Install: pip install playwright && playwright install chromium")
    sys.exit(1)

# Force unbuffered output
_print = print
def print(*args, **kwargs):
    _print(*args, **kwargs)
    sys.stdout.flush()

ACTION_GET_COLLEGES = "00c5c892dd885d8d752a185a2e0a2daf1816c31254"
ACTION_GET_BUILDINGS = "403be69e449e7bd5c598c34078108dd086f288b7e6"
ACTION_GET_ROOMS = "406e6e139afea1d05cc36f1515bc1d33ec63b0e6b1"

OUT = Path(__file__).parent.parent
CSV_OUT = OUT / "RoomInfo_RoomViewer.csv"
IMAGES_OUT = OUT / "data-scraping" / "room_images.json"
IMG360_OUT = OUT / "data-scraping" / "room_360_images.json"
RAW_OUT = OUT / "data-scraping" / "raw_roomviewer_data.json"

# --- Mappings (same as before) ---
HALL_NAME = {
    "1901 Hall": "1901", "1903 Hall": "1903", "1967 Hall": "1967",
    "1976 Hall": "1976", "1981 Hall": "1981",
    "2 Dickinson Street": "2Dickinson", "99AlexanderStreet": "99Alexander",
    "Addy Hall": "Addy", "Baker Hall": "Baker", "Blair Hall": "Blair",
    "Bloomberg Hall": "Bloomberg", "Bogle Hall": "Bogle", "Brown Hall": "Brown",
    "Buyers Hall": "Buyers", "Campbell Hall": "Campbell", "Cuyler Hall": "Cuyler",
    "Dod Hall": "Dod", "Edwards Hall": "Edwards", "Feinberg Hall": "Feinberg",
    "Fisher Hall": "Fisher", "Forbes College": "Forbes", "Foulke Hall": "Foulke",
    "Fu Hall": "Fu", "Grousbeck Hall": "Grousbeck", "Hamilton Hall": "Hamilton",
    "Hargadon Hall": "Hargadon", "Hariri Hall": "Hariri", "Henry Hall": "Henry",
    "Holder Hall": "Holder", "Joline Hall": "Joline",
    "José Feliciano": "Jose Feliciano", "Kanji Hall": "Kanji",
    "Kwanza Jones Hall": "Kwanza Jones", "Laughlin Hall": "Laughlin",
    "Lauritzen Hall": "Lauritzen", "Little Hall": "Little",
    "Lockhart Hall": "Lockhart", "Mannion Hall": "Mannion",
    "Murley-Pivirotto": "Murley-Pivirotto", "Patton Hall": "Patton",
    "Pyne Hall": "Pyne", "Scully Hall": "Scully", "Spelman Hall": "Spelman",
    "Walker Hall": "Walker", "Wendell Hall": "Wendell", "Wilf Hall": "Wilf",
    "Witherspoon Hall": "Witherspoon", "Wright Hall": "Wright",
    "Yoseloff Hall": "Yoseloff",
}
REGION = {
    "1901": "SLUMS", "1903": "SLUMS", "1967": "BUTLER", "1976": "BUTLER",
    "1981": "WHIT", "2Dickinson": "MID-CAMPUS", "99Alexander": "FORBES",
    "Addy": "NEW COLLEGE", "Baker": "WHIT", "Blair": "MID-CAMPUS",
    "Bloomberg": "BUTLER", "Bogle": "BUTLER", "Brown": "MID-CAMPUS",
    "Buyers": "ROMA", "Campbell": "ROMA", "Cuyler": "MID-CAMPUS",
    "Dod": "MID-CAMPUS", "Edwards": "MID-CAMPUS", "Feinberg": "SLUMS",
    "Fisher": "WHIT", "Forbes": "FORBES", "Foulke": "MID-CAMPUS",
    "Fu": "NEW COLLEGE", "Grousbeck": "NEW COLLEGE", "Hamilton": "MID-CAMPUS",
    "Hargadon": "WHIT", "Hariri": "NEW COLLEGE", "Henry": "MID-CAMPUS",
    "Holder": "ROMA", "Joline": "MID-CAMPUS", "Jose Feliciano": "NEW COLLEGE",
    "Kanji": "NEW COLLEGE", "Kwanza Jones": "NEW COLLEGE",
    "Laughlin": "MID-CAMPUS", "Lauritzen": "WHIT", "Little": "MID-CAMPUS",
    "Lockhart": "MID-CAMPUS", "Mannion": "NEW COLLEGE",
    "Murley-Pivirotto": "WHIT", "Patton": "MID-CAMPUS", "Pyne": "MID-CAMPUS",
    "Scully": "MID-CAMPUS", "Spelman": "SPELMAN", "Walker": "MID-CAMPUS",
    "Wendell": "WHIT", "Wilf": "BUTLER", "Witherspoon": "ROMA",
    "Wright": "SLUMS", "Yoseloff": "BUTLER",
}
DIST = {
    "1901": [7,3,6,16,8,9,17,5], "1903": [6,3,5,15,8,9,16,5],
    "1967": [7,8,8,10,6,10,13,6], "1976": [7,8,9,11,5,9,13,7],
    "1981": [8,12,13,8,9,14,13,9], "2Dickinson": [5,2,4,15,7,6,16,4],
    "99Alexander": [3,7,2,19,13,3,18,9], "Addy": [9,14,14,8,8,14,14,10],
    "Baker": [8,12,12,8,8,13,14,9], "Blair": [6,5,7,13,6,8,15,5],
    "Bloomberg": [8,8,9,12,5,9,13,7], "Bogle": [8,8,9,12,5,9,13,7],
    "Brown": [5,3,5,14,7,7,15,4], "Buyers": [6,7,7,11,4,9,14,6],
    "Campbell": [6,5,6,12,5,8,14,5], "Cuyler": [5,4,5,14,7,7,15,4],
    "Dod": [6,5,6,14,7,8,15,5], "Edwards": [5,4,5,14,7,7,15,4],
    "Feinberg": [7,4,7,15,8,10,16,6], "Fisher": [8,12,12,8,8,13,14,9],
    "Forbes": [3,8,3,19,13,4,18,10], "Foulke": [5,4,5,14,7,7,15,4],
    "Fu": [8,13,14,10,10,13,18,8], "Grousbeck": [8,13,14,10,10,13,18,8],
    "Hamilton": [5,4,5,14,7,7,15,4], "Hargadon": [8,12,12,8,8,13,14,9],
    "Hariri": [8,13,14,10,10,13,18,8], "Henry": [5,4,5,14,7,7,15,4],
    "Holder": [6,5,6,13,6,8,14,5], "Joline": [5,4,5,14,7,7,15,4],
    "Jose Feliciano": [9,14,14,8,8,14,14,10], "Kanji": [9,14,14,8,8,14,14,10],
    "Kwanza Jones": [9,14,14,8,8,14,14,10], "Laughlin": [5,4,5,14,7,7,15,4],
    "Lauritzen": [8,12,12,8,8,13,14,9], "Little": [5,4,5,14,7,7,15,4],
    "Lockhart": [5,4,5,14,7,7,15,4], "Mannion": [8,13,14,10,10,13,18,8],
    "Murley-Pivirotto": [8,12,12,8,8,13,14,9], "Patton": [5,4,5,14,7,7,15,4],
    "Pyne": [6,5,6,14,7,8,15,5], "Scully": [6,5,6,14,7,7,15,4],
    "Spelman": [7,4,7,15,8,10,16,6], "Walker": [5,4,5,14,7,7,15,4],
    "Wendell": [8,12,13,8,9,14,13,9], "Wilf": [8,8,9,12,5,9,13,7],
    "Witherspoon": [6,5,6,13,6,8,14,5], "Wright": [7,3,7,16,8,10,17,5],
    "Yoseloff": [8,8,9,12,5,9,13,7],
}
AC_YES = {
    "Addy", "Fu", "Grousbeck", "Hariri", "Mannion", "Jose Feliciano",
    "Kanji", "Kwanza Jones", "Bloomberg", "Wilf", "Yoseloff", "Bogle",
    "Baker", "Fisher", "Hargadon", "Lauritzen", "Wendell", "Murley-Pivirotto",
    "1981",
}
ELEV_YES = AC_YES | {"Holder", "Blair", "Feinberg", "Spelman"}

def get_elev(h): return "YES" if h in ELEV_YES else "NO"
def get_ac(h): return "YES" if h in AC_YES else "NO"
def get_bath(h):
    if h in {"Fu","Grousbeck","Hariri","Mannion","Addy","Jose Feliciano","Kanji","Kwanza Jones"}:
        return "Unisex"
    if h in {"Baker","Fisher","Hargadon","Lauritzen","Wendell"}:
        return "Male and Female"
    return "NONE"


def parse_rsc(text):
    """Extract JSON data from RSC response text."""
    for line in text.split("\n"):
        if line.startswith("1:"):
            try:
                return json.loads(line[2:])
            except json.JSONDecodeError:
                pass
    m = re.search(r'\[\{.+?\}\]', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


def parse_rsc_images(rsc_body):
    """Parse the RSC response from a room detail page to extract per-room images.
    Returns dict of {room_number: [image_entries]}"""
    rooms = {}
    # The RSC body contains all rooms for the building in JSON-like structures
    # Extract image objects: {"url":"...","type":"...","caption":"...","is360External":...,"mediaType":"..."}
    # These are grouped by room in the RSC tree

    # Strategy: find all room data blocks by parsing the RSC response
    # The response contains the full getRoomsByBuilding data embedded
    lines = rsc_body.split("\n")
    for line in lines:
        # Try to find JSON arrays of room objects
        match = re.match(r'^\w+:(.*)', line)
        if match:
            candidate = match.group(1)
            if candidate.startswith("["):
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        # Check if these look like room objects
                        first = parsed[0]
                        if isinstance(first, dict) and "number" in first and "images" in first:
                            for room in parsed:
                                num = room.get("number", "")
                                imgs = room.get("images", [])
                                if num and imgs:
                                    rooms[num] = imgs
                except json.JSONDecodeError:
                    pass

    return rooms


async def main():
    print("=" * 60)
    print("Princeton Room Viewer Scraper (Full Images)")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        captured = {}
        rsc_bodies = []

        async def on_response(response):
            action_id = response.request.headers.get("next-action", "")
            if action_id:
                try:
                    body = await response.text()
                    captured.setdefault(action_id, []).append(body)
                except:
                    pass
            # Capture ALL large RSC-like responses from the buildings page
            # These contain the full room+image data
            url = response.url
            if "/buildings" in url and response.request.method == "GET" and response.status == 200:
                try:
                    ct = response.headers.get("content-type", "")
                    body = await response.text()
                    # RSC responses contain room data as "1:[{...}]"
                    if len(body) > 5000 and '"images"' in body:
                        rsc_bodies.append(body)
                except:
                    pass

        page.on("response", on_response)

        # --- Login ---
        print("\n[1] Log in via CAS...")
        await page.goto("https://roomviewer.hres.princeton.edu/")
        for tick in range(180):
            await asyncio.sleep(1)
            if ACTION_GET_COLLEGES in captured:
                break
            if tick % 15 == 14:
                print("    Still waiting...")
        else:
            print("    Timed out.")
            await browser.close()
            return
        await asyncio.sleep(2)
        print("    ✓ Logged in!\n")

        # --- Get colleges ---
        print("[2] Parsing colleges...")
        colleges = None
        for resp in captured.get(ACTION_GET_COLLEGES, []):
            parsed = parse_rsc(resp)
            if isinstance(parsed, list) and len(parsed) > 0:
                colleges = parsed
                break
        if not colleges:
            print("    ERROR: No colleges")
            await browser.close()
            return
        print(f"    ✓ {len(colleges)} colleges\n")

        # --- Discover buildings ---
        print("[3] Discovering buildings...\n")
        all_buildings = []
        for college in colleges:
            cn = college["name"]
            captured.pop(ACTION_GET_BUILDINGS, None)
            await page.goto(f"https://roomviewer.hres.princeton.edu/buildings?college={quote(cn)}", wait_until="domcontentloaded")
            for _ in range(20):
                await asyncio.sleep(0.5)
                if ACTION_GET_BUILDINGS in captured:
                    break
            await asyncio.sleep(0.5)
            bldgs = None
            for resp in captured.get(ACTION_GET_BUILDINGS, []):
                parsed = parse_rsc(resp)
                if isinstance(parsed, list) and len(parsed) > 0:
                    bldgs = parsed
                    break
            if bldgs:
                for b in bldgs:
                    all_buildings.append((cn, b))
                print(f"  {cn}: {len(bldgs)} buildings")
            else:
                print(f"  {cn}: ✗")
        print(f"\n    Total: {len(all_buildings)} buildings\n")

        # --- Scrape rooms ---
        print("[4] Scraping rooms...\n")
        all_rooms = []
        all_images = {}
        images_360 = {}
        raw = {"colleges": colleges, "buildings": [], "rooms": {}}

        for i, (college_name, bldg) in enumerate(all_buildings):
            name = bldg["name"]
            room_count = bldg.get("roomCount", "?")

            # Step A: Get room list from building page
            url = f"https://roomviewer.hres.princeton.edu/buildings?college={quote(college_name)}&building={quote(name)}"
            captured.pop(ACTION_GET_ROOMS, None)
            try:
                await page.goto(url, wait_until="networkidle")
            except:
                continue
            for _ in range(20):
                await asyncio.sleep(0.5)
                if ACTION_GET_ROOMS in captured:
                    break
            await asyncio.sleep(1)

            # Get best room list response
            rooms = None
            best = 0
            for resp in captured.get(ACTION_GET_ROOMS, []):
                parsed = parse_rsc(resp)
                if parsed and isinstance(parsed, list):
                    ic = sum(len(r.get("images", [])) for r in parsed)
                    if ic > best:
                        best = ic
                        rooms = parsed
            if not rooms:
                print(f"  [{i+1}/{len(all_buildings)}] {name} — ✗ no data")
                continue

            # Step B: Navigate to first room detail to get the FULL image set
            # The room detail RSC response contains ALL rooms with complete images
            rsc_bodies.clear()
            first_room = rooms[0]["number"]
            detail_url = f"{url}&room={quote(first_room)}"
            try:
                await page.goto(detail_url, wait_until="networkidle")
            except:
                pass
            await asyncio.sleep(2)

            # Parse RSC response for full image data
            full_images = {}  # room_number -> [images]
            for body in rsc_bodies:
                full_images = parse_rsc_images(body)
                if full_images:
                    break

            # Merge: use full_images where available, fall back to initial data
            if full_images:
                for room in rooms:
                    num = room["number"]
                    if num in full_images:
                        room["images"] = full_images[num]

            # Count image types
            n_360 = sum(1 for r in rooms if any(im.get("type") == "360" for im in r.get("images", [])))
            n_rp = sum(1 for r in rooms if any(im.get("type") == "room_plan" for im in r.get("images", [])))
            n_fp = sum(1 for r in rooms if any(im.get("type") == "floor_plan" for im in r.get("images", [])))

            extra = ""
            if full_images:
                extra = f" [from RSC: 360={n_360}, rp={n_rp}, fp={n_fp}]"
            print(f"  [{i+1}/{len(all_buildings)}] {name} — ✓ {len(rooms)} rooms{extra}")

            raw["buildings"].append(bldg)
            raw["rooms"][name] = rooms

            # Convert to TigerDraw format
            hall = HALL_NAME.get(name, name)
            region = REGION.get(hall, "UNKNOWN")
            dist = DIST.get(hall, [0]*8)

            for room in rooms:
                num = room["number"]
                rid = f"{hall}{num}"

                imgs = room.get("images", [])
                if imgs:
                    all_images[rid] = []
                    for img in imgs:
                        entry = {
                            "url": img.get("url", ""),
                            "type": img.get("type", ""),
                            "caption": img.get("caption", ""),
                            "mediaType": img.get("mediaType", ""),
                            "is360External": img.get("is360External", False),
                        }
                        all_images[rid].append(entry)
                        if entry["is360External"] or entry["type"] == "360":
                            images_360.setdefault(rid, []).append(entry)

                fp = next((im["url"] for im in imgs if im.get("type") == "floor_plan"), "")
                all_rooms.append({
                    "Hall": hall, "Room": num,
                    "Type": room.get("type", ""),
                    "Sqft": room.get("size", room.get("area", 0)),
                    "College": college_name, "Region": region,
                    "Elevator": get_elev(hall), "Bathroom": get_bath(hall),
                    "AC": get_ac(hall), "Floor": room.get("floor", 0),
                    "FilePath": fp,
                    "Wawa": dist[0], "UStore": dist[1],
                    "Nassau Street": dist[2], "Jadwin Gym": dist[3],
                    "Frist": dist[4], "Street": dist[5],
                    "EQuad": dist[6], "Dillon": dist[7],
                    "RoomID": rid,
                })

        # --- Write outputs ---
        print(f"\n[5] Writing {len(all_rooms)} rooms to {CSV_OUT}...")
        all_rooms.sort(key=lambda r: (r["College"], r["Hall"], r["Room"]))
        with open(CSV_OUT, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ID","Hall","Room","Type","Sqft","College","Region",
                        "Elevator","Bathroom","AC","Floor","FilePath",
                        "Wawa","UStore","Nassau Street","Jadwin Gym",
                        "Frist","Street","EQuad","Dillon","RoomID"])
            for idx, r in enumerate(all_rooms, 1):
                w.writerow([idx, r["Hall"], r["Room"], r["Type"], r["Sqft"],
                           r["College"], r["Region"], r["Elevator"], r["Bathroom"],
                           r["AC"], r["Floor"], r["FilePath"],
                           r["Wawa"], r["UStore"], r["Nassau Street"], r["Jadwin Gym"],
                           r["Frist"], r["Street"], r["EQuad"], r["Dillon"], r["RoomID"]])

        with open(IMAGES_OUT, "w") as f:
            json.dump(all_images, f, indent=2)
        with open(IMG360_OUT, "w") as f:
            json.dump(images_360, f, indent=2)
        with open(RAW_OUT, "w") as f:
            json.dump(raw, f, indent=2)

        # --- Summary ---
        total = len(all_rooms)
        n_img = len(all_images)
        n_360 = sum(1 for imgs in all_images.values() if any(i["type"] == "360" for i in imgs))
        n_rp = sum(1 for imgs in all_images.values() if any(i["type"] == "room_plan" for i in imgs))
        n_fp = sum(1 for imgs in all_images.values() if any(i["type"] == "floor_plan" for i in imgs))

        print(f"\n{'='*60}")
        print("DONE!")
        print(f"{'='*60}")
        print(f"  Rooms: {total}")
        print(f"  With 360:        {n_360} ({100*n_360/total:.0f}%)")
        print(f"  With room plan:  {n_rp} ({100*n_rp/total:.0f}%)")
        print(f"  With floor plan: {n_fp} ({100*n_fp/total:.0f}%)")
        print(f"\n  {CSV_OUT}")
        print(f"  {IMAGES_OUT}")
        print(f"  {IMG360_OUT}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
