import os
import json
import base64
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from bs4 import BeautifulSoup, Tag
from pathlib import Path
import re
from typing import List, Dict, Optional


from pdf2image import convert_from_path


def process_pdf(doc_path):
    """Convert PDF to list of OpenCV images"""
    pil_images = convert_from_path(doc_path)

    cv2_images = []
    for pil_img in pil_images:
        cv2_img = np.array(pil_img)
        cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_RGB2BGR)
        cv2_images.append(cv2_img)

    return cv2_images


def readb64(uri):
    encoded_data = uri
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def encode_bbox(array):
    retval, buffer = cv2.imencode(".jpg", array)
    jpg_as_bytes = base64.b64encode(buffer)
    return jpg_as_bytes


def cosine_similarity(centoid1, centoid2):
    centoid1, centoid2 = map(np.array, (centoid1, centoid2))
    dot_product = np.dot(centoid1, centoid2)
    magnitude1, magnitude2 = map(np.linalg.norm, (centoid1, centoid2))
    return dot_product / (magnitude1 * magnitude2)


def convert_doc(pdf_path):

    images = convert_from_path(pdf_path)

    for i in range(len(images)):

        images[i].save("page" + str(i) + ".jpg", "JPEG")


# Function to draw bounding boxes and text on images based on HTML content
def draw_bbox(image_path, resized_width, resized_height, full_predict):
    if image_path.startswith("http"):
        response = requests.get(image_path)
        image = Image.open(BytesIO(response.content))
    else:
        image = Image.open(image_path)
    original_width = image.width
    original_height = image.height

    # Parse the provided HTML content
    soup = BeautifulSoup(full_predict, "html.parser")

    elements_with_bbox = soup.find_all(attrs={"data-bbox": True})

    filtered_elements = []
    for el in elements_with_bbox:
        if el.name == "ol":
            continue
        elif el.name == "li" and el.parent.name == "ol":
            filtered_elements.append(el)
        else:
            filtered_elements.append(el)

    image = image.resize((resized_width, resized_height))
    draw = ImageDraw.Draw(image)

    # Draw bounding boxes and text for each element
    for element in filtered_elements:
        bbox_str = element["data-bbox"]
        text = element.get_text(strip=True)
        x1, y1, x2, y2 = map(int, bbox_str.split())

        # Calculate scaling factors
        scale_x = resized_width / original_width
        scale_y = resized_height / original_height

        # Scale coordinates accordingly
        x1_resized = int(x1 / scale_x)
        y1_resized = int(y1 / scale_y)
        x2_resized = int(x2 / scale_x)
        y2_resized = int(y2 / scale_y)

        if x1_resized > x2_resized:
            x1_resized, x2_resized = x2_resized, x1_resized
        if y1_resized > y2_resized:
            y1_resized, y2_resized = y2_resized, y1_resized

        draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
        # TODO: add font argument
        draw.text((x1_resized, y2_resized), text, fill="black")

    image.show()


# Function to clean and format HTML content
def clean_and_format_html(full_predict):
    soup = BeautifulSoup(full_predict, "html.parser")

    # Regular expression pattern to match 'color' styles in style attributes
    color_pattern = re.compile(r"\bcolor:[^;]+;?")

    for tag in soup.find_all(style=True):
        original_style = tag.get("style", "")
        new_style = color_pattern.sub("", original_style)
        if not new_style.strip():
            del tag["style"]
        else:
            new_style = new_style.rstrip(";")
            tag["style"] = new_style

    for attr in ["data-bbox", "data-polygon"]:
        for tag in soup.find_all(attrs={attr: True}):
            del tag[attr]

    classes_to_update = ["formula.machine_printed", "formula.handwritten"]
    for tag in soup.find_all(class_=True):
        if isinstance(tag, Tag) and "class" in tag.attrs:
            new_classes = [cls if cls not in classes_to_update else "formula" for cls in tag.get("class", [])]
            tag["class"] = list(dict.fromkeys(new_classes))  # Deduplicate and update class names

    for div in soup.find_all("div", class_="image caption"):
        div.clear()
        div["class"] = ["image"]

    classes_to_clean = ["music sheet", "chemical formula", "chart"]
    for class_name in classes_to_clean:
        for tag in soup.find_all(class_=class_name):
            if isinstance(tag, Tag):
                tag.clear()
                if "format" in tag.attrs:
                    del tag["format"]
    output = []
    for child in soup.body.children:
        if isinstance(child, Tag):
            output.append(str(child))
            output.append("\n")
        elif isinstance(child, str) and not child.strip():
            continue
    complete_html = f"""```html\n<html><body>\n{" ".join(output)}</body></html>\n```"""
    return complete_html


def find_closest_elements(bboxes: List, query_point: tuple, page_num: int = 0, top_k: int = 1) -> List[Dict]:
    page_bboxes = [bbox for bbox in bboxes if bbox.get("page_num", 0) == page_num and not bbox.get("ignore", False)]

    if not page_bboxes:
        return []

    distances = []
    for idx, bbox in enumerate(page_bboxes):
        centroid = bbox["centroid"]

        similarity = cosine_similarity(query_point, centroid)

        distances.append(
            {
                "box_index": idx,
                "box": bbox,
                "centroid": centroid,
                "cosine_similarity": float(similarity),
            }
        )

    distances.sort(key=lambda x: (1 - x["cosine_similarity"]))

    results = []
    for item in distances[:top_k]:
        result = {
            "element": {
                "name": item.get("name", "unknown"),
                "box": item["box"],
                "page_num": item.get("page_num", 0),
                "description": item.get("description", ""),
                "text": item.get("text", ""),
            },
            "centroid": item["centroid"],
            "cosine_similarity": item["cosine_similarity"],
        }
        results.append(result)

    return results


def downsample_image(image: np.ndarray, downsample_factor: int = 6) -> Image.Image:
    if not isinstance(image, np.ndarray):
        raise TypeError(f"Expected numpy array, got {type(image)}")

    image = Image.fromarray(image)
    output_size = (
        max(1, image.width // downsample_factor),
        max(1, image.height // downsample_factor),
    )
    return image.resize(output_size, Image.Resampling.LANCZOS)


def save_json(data: List[Dict], output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
