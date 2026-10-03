from __future__ import annotations

from aeris_schemas import LocationPoint

# Representative cities + coarse India grid (demo / benchmark coverage, not official stations)
CITIES: list[LocationPoint] = [
    LocationPoint(location_id="IN-DL-DEL", name="New Delhi", latitude=28.6139, longitude=77.2090, region="North", elevation_m=216),
    LocationPoint(location_id="IN-MH-MUM", name="Mumbai", latitude=19.0760, longitude=72.8777, region="West", elevation_m=14),
    LocationPoint(location_id="IN-WB-KOL", name="Kolkata", latitude=22.5726, longitude=88.3639, region="East", elevation_m=9),
    LocationPoint(location_id="IN-TN-CHE", name="Chennai", latitude=13.0827, longitude=80.2707, region="South", elevation_m=6),
    LocationPoint(location_id="IN-KA-BLR", name="Bengaluru", latitude=12.9716, longitude=77.5946, region="South", elevation_m=920),
    LocationPoint(location_id="IN-TS-HYD", name="Hyderabad", latitude=17.3850, longitude=78.4867, region="South", elevation_m=542),
    LocationPoint(location_id="IN-GJ-AHM", name="Ahmedabad", latitude=23.0225, longitude=72.5714, region="West", elevation_m=53),
    LocationPoint(location_id="IN-RJ-JAI", name="Jaipur", latitude=26.9124, longitude=75.7873, region="North", elevation_m=431),
    LocationPoint(location_id="IN-UP-LKO", name="Lucknow", latitude=26.8467, longitude=80.9462, region="North", elevation_m=123),
    LocationPoint(location_id="IN-PB-CHD", name="Chandigarh", latitude=30.7333, longitude=76.7794, region="North", elevation_m=350),
    LocationPoint(location_id="IN-AS-GHY", name="Guwahati", latitude=26.1445, longitude=91.7362, region="Northeast", elevation_m=55),
    LocationPoint(location_id="IN-KL-KOY", name="Kochi", latitude=9.9312, longitude=76.2673, region="South", elevation_m=1),
    LocationPoint(location_id="IN-OD-BBS", name="Bhubaneswar", latitude=20.2961, longitude=85.8245, region="East", elevation_m=45),
    LocationPoint(location_id="IN-MP-BHO", name="Bhopal", latitude=23.2599, longitude=77.4126, region="Central", elevation_m=527),
    LocationPoint(location_id="IN-CG-RPR", name="Raipur", latitude=21.2514, longitude=81.6296, region="Central", elevation_m=298),
    LocationPoint(location_id="IN-JK-SNG", name="Srinagar", latitude=34.0837, longitude=74.7973, region="North", elevation_m=1585),
    LocationPoint(location_id="IN-GA-PNJ", name="Panaji", latitude=15.4909, longitude=73.8278, region="West", elevation_m=7),
    LocationPoint(location_id="IN-BR-PAT", name="Patna", latitude=25.5941, longitude=85.1376, region="East", elevation_m=53),
    LocationPoint(location_id="IN-UK-DDN", name="Dehradun", latitude=30.3165, longitude=78.0322, region="North", elevation_m=640),
    LocationPoint(location_id="IN-AP-VSK", name="Visakhapatnam", latitude=17.6868, longitude=83.2185, region="South", elevation_m=45),
]


def india_grid(step: float = 3.5) -> list[LocationPoint]:
    pts: list[LocationPoint] = []
    lat = 8.0
    n = 0
    while lat <= 35.0:
        lon = 68.0
        while lon <= 96.0:
            if 8 <= lat <= 37 and 68 <= lon <= 97:
                n += 1
                region = (
                    "Northeast"
                    if lon > 90
                    else "South"
                    if lat < 16
                    else "West"
                    if lon < 76
                    else "North"
                    if lat > 26
                    else "Central"
                    if lon < 84
                    else "East"
                )
                pts.append(
                    LocationPoint(
                        location_id=f"GRID-{n:03d}",
                        name=f"Grid {lat:.1f}N {lon:.1f}E",
                        latitude=round(lat, 2),
                        longitude=round(lon, 2),
                        region=region,
                        elevation_m=None,
                        admin_level="grid",
                    )
                )
            lon += step
        lat += step
    return pts


def all_locations() -> list[LocationPoint]:
    seen = {(c.latitude, c.longitude) for c in CITIES}
    extra = []
    for g in india_grid():
        if (g.latitude, g.longitude) not in seen:
            extra.append(g)
    return CITIES + extra


def neighbors_map(locations: list[LocationPoint], k: int = 4) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for a in locations:
        d = sorted(
            locations,
            key=lambda b: (a.latitude - b.latitude) ** 2 + (a.longitude - b.longitude) ** 2,
        )
        out[a.location_id] = [x.location_id for x in d[1 : k + 1]]
    return out
