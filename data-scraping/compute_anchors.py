"""
Compute precise anchor points for each building by analyzing the actual
GeoJSON polygon shape and matching it to the floor plan orientation.

For each building:
1. Extract the full polygon from buildings.js GeoJSON
2. Compute the oriented bounding box (minimum area rectangle)
3. Identify which corners correspond to the floor plan's top-left/top-right/bottom-left
4. Output precise anchor points
"""

import json
import math
import numpy as np

def load_geojson_buildings():
    """Load building polygons from buildings.js"""
    with open('static/assets/js/buildings.js') as f:
        content = f.read()
    json_str = content.split('var buildingData = ', 1)[1].rstrip(';').strip()
    data = json.loads(json_str)

    buildings = {}
    for feature in data['features']:
        name = feature['properties'].get('name', '')
        if not name:
            continue
        geom = feature['geometry']
        if geom['type'] == 'Polygon':
            coords = geom['coordinates'][0]
        elif geom['type'] == 'MultiPolygon':
            largest = max(geom['coordinates'], key=lambda p: len(p[0]))
            coords = largest[0]
        else:
            continue
        # Convert [lng, lat] to [lat, lng]
        buildings[name] = [[c[1], c[0]] for c in coords]
    return buildings

# Also load manual polygon coordinates from map.html
MANUAL_POLYGONS = {
    "HARIRI": [[40.3428141, -74.6543544], [40.3427746, -74.6543364], [40.3426632, -74.6547579], [40.3425660, -74.6547137], [40.3426433, -74.6544202], [40.3426774, -74.6542922], [40.3427154, -74.6543097], [40.3428083, -74.6539583], [40.3429069, -74.6540032], [40.3428141, -74.6543544]],
    "ADDY": [[40.3426246, -74.6556793], [40.3425674, -74.6557058], [40.3425532, -74.6556531], [40.3425154, -74.6556706], [40.3424554, -74.6554483], [40.3424560, -74.6551458], [40.34231, -74.65509], [40.34236, -74.65493], [40.3425200, -74.6549952], [40.3425198, -74.6550154], [40.3425554, -74.6550156], [40.3425553, -74.6550527], [40.3425833, -74.6550528], [40.3425828, -74.6553948], [40.3425542, -74.6553947], [40.3425541, -74.6554169], [40.3426246, -74.6556793]],
    "KANJI": [[40.34231, -74.65509], [40.3422334, -74.6550387], [40.3421863, -74.6550395], [40.3421876, -74.6551721], [40.3420906, -74.6555405], [40.3420510, -74.6555225], [40.3420441, -74.6555486], [40.3419840, -74.6555213], [40.3420890, -74.6551271], [40.3420866, -74.6548778], [40.3422534, -74.6548751], [40.34236, -74.65493]],
    "JONES": [[40.3416393, -74.6554748], [40.3417346, -74.6550971], [40.3417377, -74.6547468], [40.3416375, -74.6547453], [40.3416367, -74.6548059], [40.3415861, -74.6548063], [40.3413924, -74.6547118], [40.3413566, -74.6548382], [40.3415660, -74.6549404], [40.3416360, -74.6549411], [40.3416347, -74.6550537], [40.3415392, -74.6554313], [40.3416393, -74.6554748]],
    "MANNION": [[40.3415058, -74.6539918], [40.3415069, -74.6536476], [40.3415479, -74.6536486], [40.3415478, -74.6533825], [40.3416558, -74.6533867], [40.3416545, -74.6537323], [40.3416263, -74.6537317], [40.3416233, -74.6539069], [40.3416781, -74.6539285], [40.3416333, -74.6540997], [40.3415968, -74.6540699], [40.3415283, -74.6543114], [40.3414308, -74.6542706], [40.3415058, -74.6539918]],
    "FU": [[40.3426433, -74.6544202], [40.3426774, -74.6542922], [40.3424389, -74.6541827], [40.3424712, -74.6540617], [40.3424341, -74.6540446], [40.3424995, -74.6537954], [40.3424024, -74.6537515], [40.3423369, -74.6540007], [40.3423700, -74.6540152], [40.3423166, -74.6542153], [40.3423054, -74.6542129], [40.3422355, -74.6543235], [40.3421467, -74.6544640], [40.3421125, -74.6545180], [40.3421950, -74.6546079], [40.3423880, -74.6543028]],
    "GROUSBECK": [[40.3416333, -74.6540997], [40.3416781, -74.6539285], [40.3417794, -74.6535625], [40.3419149, -74.6536294], [40.3419153, -74.6534899], [40.3420222, -74.6534951], [40.3420237, -74.6537130], [40.3419828, -74.6537144], [40.3419817, -74.6541569], [40.3419756, -74.6541998], [40.3422355, -74.6543235], [40.3421467, -74.6544640], [40.3419492, -74.6543724], [40.3419167, -74.6544333], [40.3418066, -74.6543522], [40.3418446, -74.6542028], [40.3416333, -74.6540997]],
    "FELICIANO": [[40.3411594, -74.6553403], [40.3410456, -74.6552885], [40.3411370, -74.6548667], [40.3413121, -74.6545923], [40.3413924, -74.6547118], [40.3413566, -74.6548382], [40.3412586, -74.6549876], [40.3411594, -74.6553403]],
    "1981": [[40.3438121, -74.6575976], [40.3438571, -74.6574527], [40.3436404, -74.6573320], [40.3437140, -74.6571013], [40.3437467, -74.6571201], [40.3437692, -74.6570423], [40.3436792, -74.6569941], [40.3436567, -74.6570423], [40.3436199, -74.6570289], [40.3434952, -74.6574339], [40.3436915, -74.6575385]],
    "WILF": [[40.3444908, -74.6552935], [40.3442578, -74.6551111], [40.3443130, -74.6549904], [40.3445521, -74.6551675], [40.3445399, -74.6551970], [40.3444908, -74.6552935]],
}


def polygon_bbox(coords):
    """Get axis-aligned bounding box."""
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    return {
        'min_lat': min(lats), 'max_lat': max(lats),
        'min_lng': min(lngs), 'max_lng': max(lngs),
    }


def polygon_centroid(coords):
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    return [sum(lats)/len(lats), sum(lngs)/len(lngs)]


def compute_oriented_bbox(coords):
    """Compute the minimum area oriented bounding box of a polygon.
    Returns 4 corners of the OBB as [lat, lng] pairs."""
    points = np.array(coords)

    # Use PCA to find principal axes
    centroid = points.mean(axis=0)
    centered = points - centroid
    cov = np.cov(centered.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)

    # Sort by eigenvalue (largest first = long axis)
    idx = eigenvalues.argsort()[::-1]
    eigenvectors = eigenvectors[:, idx]

    # Project points onto principal axes
    projected = centered @ eigenvectors

    min_proj = projected.min(axis=0)
    max_proj = projected.max(axis=0)

    # Reconstruct corners in original space
    corners_proj = np.array([
        [min_proj[0], min_proj[1]],  # min-min
        [max_proj[0], min_proj[1]],  # max-min
        [max_proj[0], max_proj[1]],  # max-max
        [min_proj[0], max_proj[1]],  # min-max
    ])

    corners = (corners_proj @ eigenvectors.T) + centroid

    # Return corners and the principal direction angle
    angle = math.atan2(eigenvectors[1, 0], eigenvectors[0, 0])

    return corners.tolist(), math.degrees(angle), eigenvectors


def compute_anchors_for_building(name, coords, floor_plan_rotation_hint=None):
    """
    Compute anchor points (top_left, top_right, bottom_left) that map
    the floor plan drawing area to the geographic building footprint.

    The floor plan's x-axis (left-right) should map along the building's
    long axis, and the y-axis (top-bottom) along the short axis.
    """
    bbox = polygon_bbox(coords)
    corners, angle, eigvecs = compute_oriented_bbox(coords)

    # The OBB corners are ordered: [min-min, max-min, max-max, min-max]
    # We need to figure out which corner maps to top-left, top-right, bottom-left
    # of the floor plan.

    # The long axis (eigvec 0) is the direction the building runs.
    # In most floor plans, the building's long axis maps to the x-axis (left-right).

    # corners[0] = one end of long axis, short axis min
    # corners[1] = other end of long axis, short axis min
    # corners[2] = other end of long axis, short axis max
    # corners[3] = one end of long axis, short axis max

    # For standard orientation (north roughly up in floor plan):
    # top_left = NW-ish corner, top_right = NE-ish or far end, bottom_left = SW-ish

    # Pad the OBB slightly (5% margin) so rooms aren't right at the edge
    centroid = polygon_centroid(coords)
    padded_corners = []
    for c in corners:
        padded_corners.append([
            centroid[0] + 1.05 * (c[0] - centroid[0]),
            centroid[1] + 1.05 * (c[1] - centroid[1]),
        ])
    corners = padded_corners

    return {
        'corners': corners,
        'angle': angle,
        'bbox': bbox,
        'centroid': centroid,
    }


# Name mapping from GeoJSON names to our DB names
GEOJSON_TO_DB = {
    "Joline Hall": "JOLINE",
    "Blair Hall": "BLAIR",
    "Edwards Hall": "EDWARDS",
    "Hamilton Hall": "HAMILTON",
    "Buyers Hall": "BUYERS",
    "Holder Hall": "HOLDER",
    "Witherspoon Hall": "WITHERSPOON",
    "Bloomberg Hall": "BLOOMBERG",
}


if __name__ == '__main__':
    geojson = load_geojson_buildings()

    all_buildings = {}

    # Add GeoJSON buildings
    for gj_name, db_name in GEOJSON_TO_DB.items():
        if gj_name in geojson:
            all_buildings[db_name] = geojson[gj_name]

    # Add manual polygon buildings
    for db_name, coords in MANUAL_POLYGONS.items():
        if db_name not in all_buildings:
            all_buildings[db_name] = coords

    print("Building anchor analysis:")
    print("=" * 70)

    for name in sorted(all_buildings.keys()):
        coords = all_buildings[name]
        result = compute_anchors_for_building(name, coords)
        corners = result['corners']
        bbox = result['bbox']

        print(f"\n{name}:")
        print(f"  BBox: lat [{bbox['min_lat']:.6f}, {bbox['max_lat']:.6f}], lng [{bbox['min_lng']:.6f}, {bbox['max_lng']:.6f}]")
        print(f"  Angle: {result['angle']:.1f}°")
        print(f"  OBB corners [lat, lng]:")
        for i, c in enumerate(corners):
            print(f"    corner[{i}]: [{c[0]:.7f}, {c[1]:.7f}]")

        # Determine which corner is NW, NE, SW, SE
        # NW = max lat, min lng; NE = max lat, max lng; etc.
        by_lat = sorted(range(4), key=lambda i: corners[i][0], reverse=True)
        by_lng = sorted(range(4), key=lambda i: corners[i][1])

        # Top 2 by lat = "north" side, then sort by lng
        north = sorted(by_lat[:2], key=lambda i: corners[i][1])
        south = sorted(by_lat[2:], key=lambda i: corners[i][1])

        nw, ne = north[0], north[1]
        sw, se = south[0], south[1]

        print(f"  NW (top_left):     [{corners[nw][0]:.7f}, {corners[nw][1]:.7f}]")
        print(f"  NE (top_right):    [{corners[ne][0]:.7f}, {corners[ne][1]:.7f}]")
        print(f"  SW (bottom_left):  [{corners[sw][0]:.7f}, {corners[sw][1]:.7f}]")
        print(f"  SE (bottom_right): [{corners[se][0]:.7f}, {corners[se][1]:.7f}]")

        # Output Python dict for visual_room_positions.py
        # For most buildings: image-left = NW end, image-right = SE end
        # top_left = NW, top_right = NE or SE (depending on building orientation)
        # This is building-specific and depends on floor plan layout
        print(f"  # Suggested anchors (left=west, right=east, top=north):")
        print(f"  'top_left':    [{corners[nw][0]:.7f}, {corners[nw][1]:.7f}],")
        print(f"  'top_right':   [{corners[ne][0]:.7f}, {corners[ne][1]:.7f}],")
        print(f"  'bottom_left': [{corners[sw][0]:.7f}, {corners[sw][1]:.7f}],")
