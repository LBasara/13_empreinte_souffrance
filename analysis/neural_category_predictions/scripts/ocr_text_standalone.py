"""This module extracts helpful standalone functions
otherwise hidden in classes with bloated __init___
"""

import os
import requests
from urllib.parse import urlparse
import time
from models.lewagon_ocr.OpenFoodFactsCategorizer.data import get_data_from_ocr

def get_image_folder_url(barcode):
    """Returns the image folder for given barcode

    Args:
        barcode (str): product barcode

    Returns:
        str: The folder url containing pictures on OFF website
    """
    product_url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    response = requests.get(product_url)
    if response.status_code != 200:
        print(f"[ERROR] Product API returned {response.status_code} for barcode {barcode}")
        return None

    data = response.json()
    if data.get("status") != 1:
        print(f"[ERROR] Product not found for barcode {barcode}")
        return None

    front_img_url = data.get("product", {}).get("image_front_url")
    if not front_img_url:
        print(f"[ERROR] No front image found for product {barcode}")
        return None

    parsed = urlparse(front_img_url)
    folder_path = os.path.dirname(parsed.path)
    folder_url = f"{parsed.scheme}://{parsed.netloc}{folder_path}"
    return folder_url


def lewagon_off_ocr_text(barcode, n_images=3):
    """Returns OCR text from the first n images of the product

    Args:
        barcode (str): product barcode
        n_images (int, optional): MAximum number of images. Defaults to 3.

    Returns:
        str: Joined text of first n_images
    """

    text = []
    for i in range(1, n_images + 1):
        try:
            url = get_image_folder_url(barcode)
            if url:
                url = f'{url}/{i}.json'
                ocr_text_per_page = get_data_from_ocr(url)
                text.append(ocr_text_per_page)
        except Exception as e:
            print(f"[ERROR] Unable to get OCR text from page number {i}: {e}")
            continue
    if text:
        return ' '.join(text)
    else:
        print(f"[ERROR] No OCR text found for {barcode}")
        return None


def get_ocr(row):
    """Returns OCR for the row (same if it exists, fetches it otherwise)

    Args:
        row (pd.Series): The row of a OFF database dataframe

    Returns:
        str: ocr description
    """
    if not isinstance(row["ocr_text"], str):
        time.sleep(0.2)
        return lewagon_off_ocr_text(row["code"])
    else:
        return row["ocr_text"]
