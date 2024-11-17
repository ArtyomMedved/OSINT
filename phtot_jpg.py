import exifread
from geopy.geocoders import Nominatim

def dms_to_decimal(dms, ref):
    """Convert DMS (Degrees, Minutes, Seconds) to Decimal Degrees."""
    degrees = dms[0].num / dms[0].den
    minutes = dms[1].num / dms[1].den / 60.0
    seconds = dms[2].num / dms[2].den / 3600.0
    result = degrees + minutes + seconds
    if ref in ['S', 'W']:
        result = -result
    return result

def get_address(latitude, longitude):
    """Fetch address using Geopy Nominatim."""
    geolocator = Nominatim(user_agent="geoapiExercises")
    location = geolocator.reverse((latitude, longitude), exactly_one=True, language="ru")
    return location.address if location else 'Адрес не найден'

def extract_metadata(image_path):
    """Extract metadata from an image."""
    with open(image_path, 'rb') as image_file:
        tags = exifread.process_file(image_file, details=True)

    # Extract GPS data
    gps_latitude = tags.get('GPS GPSLatitude')
    gps_latitude_ref = tags.get('GPS GPSLatitudeRef')
    gps_longitude = tags.get('GPS GPSLongitude')
    gps_longitude_ref = tags.get('GPS GPSLongitudeRef')
    latitude = dms_to_decimal(gps_latitude.values, gps_latitude_ref.values) if gps_latitude else None
    longitude = dms_to_decimal(gps_longitude.values, gps_longitude_ref.values) if gps_longitude else None

    # Fetch address if GPS is available
    address = get_address(latitude, longitude) if latitude and longitude else 'Нет GPS-данных'

    # Extract camera data
    make = tags.get('Image Make', 'Unknown')
    model = tags.get('Image Model', 'Unknown')
    software = tags.get('Image Software', 'Unknown')
    datetime = tags.get('Image DateTime', 'Unknown')
    host_computer = tags.get('Image HostComputer', 'Unknown')

    return {
        'latitude': latitude,
        'longitude': longitude,
        'address': address,
        'make': make,
        'model': model,
        'software': software,
        'datetime': datetime,
        'host_computer': host_computer,
    }

def format_metadata(metadata):
    """Format metadata into a readable report."""
    output = ["=" * 50, "ИНФОРМАЦИЯ ОБ ИЗОБРАЖЕНИИ", "=" * 50]

    if metadata['latitude'] and metadata['longitude']:
        output.append("\n📍 GPS-ДАННЫЕ:")
        output.append(f"  Широта: {metadata['latitude']}°")
        output.append(f"  Долгота: {metadata['longitude']}°")
        output.append(f"\n📌 Адрес: {metadata['address']}")
        output.append(f"🌍 Ссылка на Google Maps: https://www.google.com/maps?q={metadata['latitude']},{metadata['longitude']}")

    output.append("\n📱 ИНФОРМАЦИЯ О ТЕЛЕФОНЕ:")
    output.append(f"  Make: {metadata['make']}")
    output.append(f"  Model: {metadata['model']}")
    output.append(f"  Software: {metadata['software']}")
    output.append(f"  DateTime: {metadata['datetime']}")
    output.append(f"  HostComputer: {metadata['host_computer']}")

    output.append("=" * 50)
    return "\n".join(output)

if __name__ == "__main__":
    image_path = "src/img/IMG_7377.JPG"  # Укажите путь к изображению
    metadata = extract_metadata(image_path)
    print(format_metadata(metadata))
