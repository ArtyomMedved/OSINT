import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from PIL import Image
from geopy.geocoders import Nominatim
import piexif
import exifread
from pillow_heif import register_heif_opener

# Регистрация HEIC
register_heif_opener()

SAVE_PATH = 'images'

if not os.path.exists(SAVE_PATH):
    os.makedirs(SAVE_PATH)

def rational_to_float(rational):
    """Преобразует рациональные числа EXIF в float."""
    return rational[0] / rational[1] if rational[1] != 0 else 0

def convert_to_decimal(degrees, minutes, seconds):
    """Преобразует градусы, минуты и секунды в десятичный формат."""
    degrees = rational_to_float(degrees)
    minutes = rational_to_float(minutes)
    seconds = rational_to_float(seconds)
    return degrees + minutes / 60 + seconds / 3600

def dms_to_decimal(dms, ref):
    """Convert DMS (Degrees, Minutes, Seconds) to Decimal Degrees."""
    degrees = dms[0].num / dms[0].den
    minutes = dms[1].num / dms[1].den / 60.0
    seconds = dms[2].num / dms[2].den / 3600.0
    result = degrees + minutes + seconds
    if ref in ['S', 'W']:
        result = -result
    return result

def get_address(lat, lon):
    """Получает адрес по координатам с использованием geopy."""
    geolocator = Nominatim(user_agent="geo_exif_locator")
    location = geolocator.reverse((lat, lon), language="en")
    return location.address if location else "Адрес не найден"

def extract_exif_heic(file_path):
    try:
        img = Image.open(file_path)
        exif_data = piexif.load(img.info.get("exif", b""))

        gps_data = exif_data.get("GPS")
        if gps_data:
            latitude = gps_data.get(piexif.GPSIFD.GPSLatitude)
            longitude = gps_data.get(piexif.GPSIFD.GPSLongitude)
            latitude_ref = gps_data.get(piexif.GPSIFD.GPSLatitudeRef, b'N').decode('utf-8')
            longitude_ref = gps_data.get(piexif.GPSIFD.GPSLongitudeRef, b'E').decode('utf-8')

            if latitude and longitude:
                decimal_lat = convert_to_decimal(*latitude)
                decimal_lon = convert_to_decimal(*longitude)

                if latitude_ref == 'S':
                    decimal_lat = -decimal_lat
                if longitude_ref == 'W':
                    decimal_lon = -decimal_lon

                address = get_address(decimal_lat, decimal_lon)
                google_maps_link = f"https://www.google.com/maps?q={decimal_lat},{decimal_lon}"

                return {
                    'latitude': decimal_lat,
                    'longitude': decimal_lon,
                    'address': address,
                    'google_maps_link': google_maps_link,
                    'make': exif_data.get("0th", {}).get(piexif.ImageIFD.Make, 'Unknown'),
                    'model': exif_data.get("0th", {}).get(piexif.ImageIFD.Model, 'Unknown'),
                    'software': exif_data.get("0th", {}).get(piexif.ImageIFD.Software, 'Unknown'),
                    'datetime': exif_data.get("0th", {}).get(piexif.ImageIFD.DateTime, 'Unknown')
                }
        return None
    except Exception as e:
        print(f"Ошибка при обработке HEIC файла: {e}")
        return None

def extract_exif_jpg_png(file_path):
    try:
        with open(file_path, 'rb') as image_file:
            tags = exifread.process_file(image_file, details=True)
        
        gps_latitude = tags.get('GPS GPSLatitude')
        gps_latitude_ref = tags.get('GPS GPSLatitudeRef')
        gps_longitude = tags.get('GPS GPSLongitude')
        gps_longitude_ref = tags.get('GPS GPSLongitudeRef')
        
        latitude = dms_to_decimal(gps_latitude.values, gps_latitude_ref.values) if gps_latitude else None
        longitude = dms_to_decimal(gps_longitude.values, gps_longitude_ref.values) if gps_longitude else None

        address = get_address(latitude, longitude) if latitude and longitude else 'Нет GPS-данных'

        # Генерация ссылки на Google Maps
        google_maps_link = f"https://www.google.com/maps?q={latitude},{longitude}" if latitude and longitude else None

        return {
            'latitude': latitude,
            'longitude': longitude,
            'address': address,
            'google_maps_link': google_maps_link,  # Добавляем ссылку
            'make': tags.get('Image Make', 'Unknown'),
            'model': tags.get('Image Model', 'Unknown'),
            'datetime': tags.get('Image DateTime', 'Unknown'),
            'software': tags.get('Image Software', 'Unknown')
        }
    except Exception as e:
        print(f"Ошибка при обработке JPG/PNG файла: {e}")
        return None



def extract_metadata(image_path):
    if image_path.lower().endswith(('heic', 'heif')):
        return extract_exif_heic(image_path)
    elif image_path.lower().endswith(('jpg', 'jpeg', 'png')):
        return extract_exif_jpg_png(image_path)
    return None

def format_metadata(metadata):
    output = ["=" * 50, "ИНФОРМАЦИЯ ОБ ИЗОБРАЖЕНИИ", "=" * 50]

    # Проверяем наличие GPS-данных
    if metadata.get('latitude') and metadata.get('longitude'):
        output.append("\n📍 GPS-ДАННЫЕ:")
        output.append(f"  Широта: {metadata['latitude']}°")
        output.append(f"  Долгота: {metadata['longitude']}°")
        output.append(f"\n📌 Адрес: {metadata.get('address', 'Адрес не найден')}")
        if 'google_maps_link' in metadata:
            output.append(f"🌍 Ссылка на Google Maps: {metadata['google_maps_link']}")

    # Информация о телефоне
    output.append("\n📱 ИНФОРМАЦИЯ О ТЕЛЕФОНЕ:")
    output.append(f"  Make: {metadata.get('make', 'Unknown')}")
    output.append(f"  Model: {metadata.get('model', 'Unknown')}")
    output.append(f"  Software: {metadata.get('software', 'Unknown')}")
    output.append(f"  DateTime: {metadata.get('datetime', 'Unknown')}")

    output.append("=" * 50)
    return "\n".join(output)

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Здравствуйте! Пожалуйста, отправьте мне фотографию (не сжатую), и я покажу вам, где она была сделана.')

async def handle_image(update: Update, context: CallbackContext) -> None:
    if update.message.photo:
        # Если сообщение содержит фото
        photo = update.message.photo[-1]
        file = await photo.get_file()
        file_name = file.file_id + ".jpg"
    elif update.message.document:
        # Если сообщение содержит файл
        document = update.message.document
        file = await document.get_file()
        file_name = document.file_name
    else:
        await update.message.reply_text('Отправьте изображение или файл.')
        return

    # Создаем путь для сохранения файла
    file_path = os.path.join(SAVE_PATH, file_name)
    await file.download_to_drive(file_path)

    try:
        # Обработка метаданных
        metadata = extract_metadata(file_path)
        if metadata:
            metadata_report = format_metadata(metadata)
            await update.message.reply_text(f'Изображение сохранено! Вот метаданные:\n{metadata_report}')
        else:
            await update.message.reply_text('Не удалось извлечь метаданные изображения.')
    finally:
        # Удаление файла после обработки
        if os.path.exists(file_path):
            os.remove(file_path)


def main() -> None:
    TOKEN = '7932231776:AAE1Qx4ZieIqj7YscZNZMxCtxTFPByhTVco'

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO | filters.ATTACHMENT, handle_image))  # Обработка и фото, и файлов

    application.run_polling()

if __name__ == '__main__':
    main()
