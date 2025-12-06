import math
from typing import Dict, List, Tuple, Any
R_EARTH = 6371000.0
def haversine(nodes, a, b):
    lat1, lon1 = nodes[a]
    lat2, lon2 = nodes[b]
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlamb = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlamb / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R_EARTH * c
