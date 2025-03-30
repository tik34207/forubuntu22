import os
import random
import logging
import requests
from PIL import Image, ImageDraw
from exif import Image as ExifImage
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

UNSPLASH_ACCESS_KEY = 'Bmnzc4D_qAtof9NADCncwaxGCPSOul26b1pwXUlH2fQ'

def clean_metadata(file_path):
    with open(file_path, 'rb') as img_file:
        img = ExifImage(img_file)
        if "APP1" in img._segments:
            try:
                img.delete_all()
            except Exception as e:
                logging.warning(f"Exception occurred while deleting EXIF data: {e}")
            with open(file_path, 'wb') as new_file:
                new_file.write(img.get_file())

def add_random_emoji(image, settings):
    emoji_files = [f for f in os.listdir('emoji') if os.path.isfile(os.path.join('emoji', f))]
    for _ in range(settings['emoji']['count']):
        emoji_file = random.choice(emoji_files)
        emoji = Image.open(os.path.join('emoji', emoji_file)).convert('RGBA')
        emoji = emoji.resize((settings['emoji']['size'], settings['emoji']['size']), Image.LANCZOS)
        x = random.randint(0, image.width - emoji.width)
        y = random.randint(0, image.height - emoji.height)
        emoji_mask = emoji.split()[3].point(lambda i: i * settings['emoji']['transparency'] / 100)
        image.paste(emoji, (x, y), emoji_mask)
    return image

def add_noise(image, settings):
    draw = ImageDraw.Draw(image)
    width, height = image.size
    factor = settings['noise']['intensity']
    for i in range(width):
        for j in range(height):
            rand = random.randint(-factor, factor)
            r, g, b, a = image.getpixel((i, j))
            r = max(0, min(255, r + rand))
            g = max(0, min(255, g + rand))
            b = max(0, min(255, b + rand))
            draw.point((i, j), (r, g, b, a))
    return image

def get_random_background():
    try:
        url = f'https://api.unsplash.com/photos/random?client_id={UNSPLASH_ACCESS_KEY}'
        response = requests.get(url)
        data = response.json()
        bg_url = data['urls']['full']
        bg_image = Image.open(requests.get(bg_url, stream=True).raw).convert('RGBA')
        logging.info(f"Background image loaded from {bg_url}")
        return bg_image
    except Exception as e:
        logging.error(f"Error loading background image: {e}")
        return None

def add_background(image, settings):
    bg_image = get_random_background()
    if bg_image is not None:
        bg_image = bg_image.resize(image.size)
        bg_image = Image.blend(image, bg_image, settings['background']['transparency'] / 100)
        logging.info("Background image added")
    else:
        logging.warning("No background image added")
    return bg_image

def process_image(file_path, settings):
    clean_metadata(file_path)
    image = Image.open(file_path).convert('RGBA')
    logging.info(f"Original image size: {os.path.getsize(file_path) / 1024:.2f} KB")

    if settings['emoji']['enabled']:
        image = add_random_emoji(image, settings)
    if settings['noise']['enabled']:
        image = add_noise(image, settings)
    if settings['background']['enabled']:
        image = add_background(image, settings)

    if not os.path.exists("processed_images"):
        os.makedirs("processed_images")

    output_path = f"processed_images/unique_{random.randint(1000, 9999)}.jpg"
    image.convert('RGB').save(output_path, "JPEG", quality=85)
    logging.info(f"Processed image saved as: {output_path}")
    logging.info(f"Processed image size: {os.path.getsize(output_path) / 1024:.2f} KB")
    return output_path

def compress_image(file_path):
    image = Image.open(file_path)
    compressed_path = f"compressed_{os.path.basename(file_path)}"
    image.save(compressed_path, optimize=True, quality=85)
    logging.info(f"Compressed image size: {os.path.getsize(compressed_path) / 1024:.2f} KB")
    return compressed_path
