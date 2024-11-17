import piexif
from pillow_heif import register_heif_opener
from PIL import Image
from geopy.geocoders import Nominatim

# Регистрация HEIC
register_heif_opener()

# Путь к вашему HEIC-файлу
file_path = "src/img/IMG_0798.HEIC"

def rational_to_float(rational):
    """Преобразует рациональные числа EXIF в float."""
    return rational[0] / rational[1] if rational[1] != 0 else 0

def convert_to_decimal(degrees, minutes, seconds):
    """Преобразует градусы, минуты и секунды в десятичный формат."""
    degrees = rational_to_float(degrees)
    minutes = rational_to_float(minutes)
    seconds = rational_to_float(seconds)
    return degrees + minutes / 60 + seconds / 3600

def get_address(lat, lon):
    """Получает адрес по координатам с использованием geopy."""
    geolocator = Nominatim(user_agent="geo_exif_locator")
    location = geolocator.reverse((lat, lon), language="en")
    return location.address if location else "Адрес не найден"

def extract_exif(file_path):
    try:
        # Открываем изображение
        img = Image.open(file_path)

        # Получаем EXIF данные
        exif_data = piexif.load(img.info.get("exif", b""))

        print("=" * 50)
        print("ИНФОРМАЦИЯ ОБ ИЗОБРАЖЕНИИ")
        print("=" * 50)

        # Выводим GPS данные
        gps_data = exif_data.get("GPS")
        if gps_data:
            print("\n📍 GPS-ДАННЫЕ:")
            latitude = gps_data.get(piexif.GPSIFD.GPSLatitude)
            longitude = gps_data.get(piexif.GPSIFD.GPSLongitude)
            latitude_ref = gps_data.get(piexif.GPSIFD.GPSLatitudeRef, b'N').decode('utf-8')
            longitude_ref = gps_data.get(piexif.GPSIFD.GPSLongitudeRef, b'E').decode('utf-8')
            
            if latitude and longitude:
                # Преобразование координат в десятичный формат
                decimal_lat = convert_to_decimal(*latitude)
                decimal_lon = convert_to_decimal(*longitude)
                
                # Учет направлений (N/S, E/W)
                if latitude_ref == 'S':
                    decimal_lat = -decimal_lat
                if longitude_ref == 'W':
                    decimal_lon = -decimal_lon
                
                print(f"  Широта: {decimal_lat}°")
                print(f"  Долгота: {decimal_lon}°")

                # Получаем адрес и ссылку на карты
                address = get_address(decimal_lat, decimal_lon)
                google_maps_link = f"https://www.google.com/maps?q={decimal_lat},{decimal_lon}"
                print(f"\n📌 Адрес: {address}")
                print(f"🌍 Ссылка на Google Maps: {google_maps_link}")
            else:
                print("  GPS координаты отсутствуют.")
        else:
            print("\n📍 GPS-ДАННЫЕ: отсутствуют.")

        # Выводим информацию о телефоне
        print("\n📱 ИНФОРМАЦИЯ О ТЕЛЕФОНЕ:")
        phone_info_tags = {
            piexif.ImageIFD.Make: "Make",
            piexif.ImageIFD.Model: "Model",
            piexif.ImageIFD.Software: "Software",
            piexif.ImageIFD.DateTime: "DateTime",
            piexif.ImageIFD.HostComputer: "HostComputer",
            piexif.ExifIFD.PixelXDimension: "PixelXDimension",
            piexif.ExifIFD.PixelYDimension: "PixelYDimension",
            piexif.ExifIFD.LensMake: "LensMake",
            piexif.ExifIFD.LensModel: "LensModel",
        }

        for ifd, tag_name in phone_info_tags.items():
            for tag, value in exif_data.get("0th", {}).items():
                if tag == ifd:
                    print(f"  {tag_name}: {value}")

        print("\n" + "=" * 50)

    except Exception as e:
        print(f"Ошибка при обработке файла: {e}")

# Вызов функции
extract_exif(file_path)
