"""Helper functions to convert exif data into better formats"""

orientation2angle = {
   'Horizontal (normal)': (None, 0),
   'Mirrored horizontal': ('H', 0),
   'Rotated 180': (None, 180),
   'Mirrored vertical': ('V', 0),
   'Mirrored horizontal then rotated 90 CCW': ('H', -90),
   'Rotated 90 CCW': (None, -90),
   'Mirrored horizontal then rotated 90 CW': ('H', 90),
   'Rotated 90 CW': (None, 90),
}


def exif_position(exif):
    """Reads exifread tags and extracts a float tuple (lat, lon)"""
    lat = exif.get("GPS GPSLatitude")
    lon = exif.get("GPS GPSLongitude")
    if None in (lat, lon): return None, None

    lat = dms_to_float(lat)
    lon = dms_to_float(lon)
    if None in (lat, lon): return None, None

    if exif.get('GPS GPSLatitudeRef').printable == 'S': lat *= -1
    if exif.get('GPS GPSLongitudeRef').printable == 'S': lon *= -1

    return lat, lon


def dms_to_float(p):
    """Converts exifread data points to decimal GPX floats"""
    try:
        degree = p.values[0]
        minute = p.values[1]
        second = p.values[2]
        return (
            float(degree.num)/float(degree.den) +
            float(minute.num)/float(minute.den)/60 +
            float(second.num)/float(second.den)/3600
        )
    except AttributeError:
        return None


def exif_string(exif, key):
    p = exif.get(key)
    if p:
        return p.printable.strip()


def exif_int(exif, key):
    p = exif.get(key)
    if p:
        return int(p.printable or 0)


def exif_ratio(exif, key):
    p = exif.get(key)
    try:
        if p:
            p = p.values[0]
            return int(p.num), int(p.den)
    except AttributeError:
        if isinstance(p, int):
            return p


def exif_orientation(exif):
    orientation = exif.get("Image Orientation")
    if orientation is None: return None, None, 0

    mirror, angle = orientation2angle.get(orientation.printable)
    return orientation.printable, mirror, angle
