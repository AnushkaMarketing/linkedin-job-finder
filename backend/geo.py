from math import radians, sin, cos, atan2, sqrt
from .models import Point, Job, Preferences


def distance(a: Point, b: Point) -> float:
    """Haversine great-circle kilometres; not driving distance."""
    la, lb = radians(a.latitude), radians(b.latitude)
    dlat, dlon = lb - la, radians(b.longitude - a.longitude)
    h = min(1, max(0, sin(dlat / 2)**2 + cos(la) * cos(lb) * sin(dlon / 2)**2))
    return 6371.0088 * 2 * atan2(sqrt(h), sqrt(1 - h))


def location_fit(job: Job, prefs: Preferences) -> tuple[bool, float | None, str]:
    if job.work_mode == 'remote':
        return True, None, 'Remote; confirm geographic/work-authorization restrictions'
    if not prefs.origin or not job.coordinates:
        return not prefs.strict_radius, None, 'Unknown office distance'
    d = distance(prefs.origin, job.coordinates)
    if job.coordinates.precision != 'office':
        return not prefs.strict_radius, round(d, 1), 'Approximate locality distance; office unverified'
    return d <= prefs.radius_km, round(d, 1), 'Within radius (straight-line)' if d <= prefs.radius_km else 'Outside radius'
