"""
Generate room_positions.json from visually-extracted room positions.

Each building has:
- polygon: geographic coordinates [lat, lng]
- drawing_bounds: (x, y, w, h) of actual drawing area in the image
- image_size: (width, height) of the source image
- orientation: how the floor plan maps to geography
  'NE_right' means right side of image = NE, left = SW (most Yeh/NCW buildings)
- rooms: dict of room_no -> (px, py) pixel position in full image
"""

import json
import math

# ===== BUILDING DATA =====
# Each entry: polygon coords, drawing bounds, image size, rooms by floor

BUILDINGS = {}

# ===== HARIRI HALL (Yeh College) =====
# Polygon runs NE to SW. Building is long, oriented roughly NE-SW.
# In the floor plan: left = NW/W end, right = E/NE end
# Top of image = north side of building, bottom = south side
HARIRI_POLYGON = [
    [40.3428141, -74.6543544], [40.3427746, -74.6543364],
    [40.3426632, -74.6547579], [40.3425660, -74.6547137],
    [40.3426433, -74.6544202], [40.3426774, -74.6542922],
    [40.3427154, -74.6543097], [40.3428083, -74.6539583],
    [40.3429069, -74.6540032], [40.3428141, -74.6543544],
]
HARIRI_DRAW_BOUNDS = (50, 300, 2850, 1200)  # x, y, w, h in 3400x2200 image

BUILDINGS["HARIRI"] = {
    "polygon": HARIRI_POLYGON,
    "draw_bounds": HARIRI_DRAW_BOUNDS,
    "image_size": (3400, 2200),
    "floors": {
        "3": {
            # Top row (north side) - left to right
            "A317": (350, 880), "A318": (520, 840),
            "A320A": (800, 780), "A320": (920, 780), "A320B": (1070, 780),
            # Bottom row (south side) - left to right
            "A316B": (240, 1130), "A316": (420, 1130),
            "A316A": (580, 1130), "A315": (850, 1130),
            # Middle section - top row
            "A301A": (1530, 820), "A301": (1670, 820), "A301B": (1820, 820),
            "A303A": (2000, 820), "A303": (2120, 820),
            # Middle section - bottom
            "A311A": (1630, 1000), "A311B": (1800, 1000),
            # Right section (NE end)
            "A304": (2350, 830), "A305": (2480, 830), "A306": (2620, 800),
            "A308": (2560, 1070),
        },
    }
}

# ===== ADDY HALL (New College West) =====
ADDY_POLYGON = [
    [40.3426246, -74.6556793], [40.3425674, -74.6557058],
    [40.3425532, -74.6556531], [40.3425154, -74.6556706],
    [40.3424554, -74.6554483], [40.3424560, -74.6551458],
    [40.34231, -74.65509], [40.34236, -74.65493],
    [40.3425200, -74.6549952], [40.3425198, -74.6550154],
    [40.3425554, -74.6550156], [40.3425553, -74.6550527],
    [40.3425833, -74.6550528], [40.3425828, -74.6553948],
    [40.3425542, -74.6553947], [40.3425541, -74.6554169],
    [40.3426246, -74.6556793],
]

# ===== MANNION HALL (Yeh College) =====
# Building is L-shaped. Main body runs E-W, wing goes south on east end.
# In floor plan: left=west, right=east, top=north, bottom=south
MANNION_POLYGON = [
    [40.3415058, -74.6539918], [40.3415069, -74.6536476],
    [40.3415479, -74.6536486], [40.3415478, -74.6533825],
    [40.3416558, -74.6533867], [40.3416545, -74.6537323],
    [40.3416263, -74.6537317], [40.3416233, -74.6539069],
    [40.3416781, -74.6539285], [40.3416333, -74.6540997],
    [40.3415968, -74.6540699], [40.3415283, -74.6543114],
    [40.3414308, -74.6542706], [40.3415058, -74.6539918],
]
MANNION_DRAW_BOUNDS = (50, 300, 2700, 1300)  # approximate for 3400x2200

BUILDINGS["MANNION"] = {
    "polygon": MANNION_POLYGON,
    "draw_bounds": MANNION_DRAW_BOUNDS,
    "image_size": (3400, 2200),
    "floors": {
        "1": {
            # Top row (north) - west to east
            "D103C": (200, 890), "D103D": (350, 890), "D104B": (470, 890),
            "D104": (620, 890), "D107": (1050, 780),
            # Middle row
            "D103": (230, 990),
            # North-east section (upper)
            "D109": (1300, 850), "D110": (1470, 900),
            "D112A": (1720, 850), "D112": (1850, 850), "D112B": (2000, 850),
            "D113": (2150, 880),
            # Bottom row (south) - west to east
            "D103B": (200, 1280), "D103A": (370, 1280),
            "D102B": (500, 1280), "D102": (680, 1280),
            # South-east section
            "D125B": (1210, 1080), "D125": (1300, 1080), "D125A": (1420, 1080),
            "D123": (1750, 1100), "D122": (1900, 1150),
            "D115": (2350, 1090), "D115A": (2550, 1100),
            "D118": (2300, 1250), "D117": (2450, 1320),
        },
    }
}

# ===== FU HALL (Yeh College) =====
FU_POLYGON = [
    [40.3426433, -74.6544202], [40.3426774, -74.6542922],
    [40.3424389, -74.6541827], [40.3424712, -74.6540617],
    [40.3424341, -74.6540446], [40.3424995, -74.6537954],
    [40.3424024, -74.6537515], [40.3423369, -74.6540007],
    [40.3423700, -74.6540152], [40.3423166, -74.6542153],
    [40.3423054, -74.6542129], [40.3422355, -74.6543235],
    [40.3421467, -74.6544640], [40.3421125, -74.6545180],
    [40.3421950, -74.6546079], [40.3423880, -74.6543028],
]

# ===== GROUSBECK HALL (Yeh College) =====
GROUSBECK_POLYGON = [
    [40.3416333, -74.6540997], [40.3416781, -74.6539285],
    [40.3417794, -74.6535625], [40.3419149, -74.6536294],
    [40.3419153, -74.6534899], [40.3420222, -74.6534951],
    [40.3420237, -74.6537130], [40.3419828, -74.6537144],
    [40.3419817, -74.6541569], [40.3419756, -74.6541998],
    [40.3422355, -74.6543235], [40.3421467, -74.6544640],
    [40.3419492, -74.6543724], [40.3419167, -74.6544333],
    [40.3418066, -74.6543522], [40.3418446, -74.6542028],
    [40.3416333, -74.6540997],
]


def pixel_to_geo(px, py, draw_bounds, polygon):
    """Convert pixel position to lat/lng.

    Maps the drawing area to the polygon's bounding box.
    Assumes: image-left = min_lng, image-right = max_lng,
             image-top = max_lat, image-bottom = min_lat
    (standard geographic orientation with north up)
    """
    dx, dy, dw, dh = draw_bounds

    # Normalize to 0-1 within drawing area
    norm_x = max(0, min(1, (px - dx) / dw)) if dw > 0 else 0.5
    norm_y = max(0, min(1, (py - dy) / dh)) if dh > 0 else 0.5

    # Get polygon bounding box
    lats = [c[0] for c in polygon]
    lngs = [c[1] for c in polygon]
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)

    # Standard mapping: x -> longitude, y (inverted) -> latitude
    lat = max_lat - norm_y * (max_lat - min_lat)
    lng = min_lng + norm_x * (max_lng - min_lng)

    return round(lat, 7), round(lng, 7)


def generate_positions():
    """Generate room_positions.json from visual data."""
    output = {}

    for building_name, data in BUILDINGS.items():
        polygon = data["polygon"]
        draw_bounds = data["draw_bounds"]
        building_rooms = {}

        for floor_key, rooms in data["floors"].items():
            for room_no, (px, py) in rooms.items():
                lat, lng = pixel_to_geo(px, py, draw_bounds, polygon)
                building_rooms[room_no] = [lat, lng]

        if building_rooms:
            output[building_name] = building_rooms
            print(f"{building_name}: {len(building_rooms)} rooms positioned")

    return output


if __name__ == "__main__":
    positions = generate_positions()

    output_path = "static/assets/js/room_positions.json"
    with open(output_path, 'w') as f:
        json.dump(positions, f, indent=2)

    total = sum(len(v) for v in positions.values())
    print(f"\nTotal: {total} rooms across {len(positions)} buildings")
    print(f"Saved to {output_path}")
