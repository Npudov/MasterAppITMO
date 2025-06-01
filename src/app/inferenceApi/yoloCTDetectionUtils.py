from io import BytesIO

from PIL import Image
from ultralytics import YOLO


def load_model(model_path: str) -> YOLO:
    """Загрузка модели YOLO."""
    return YOLO(model_path)


def process_image(image_bytes: bytes) -> Image:
    """Конвертация байтового потока в PIL Image."""
    return Image.open(BytesIO(image_bytes)).convert("RGB")


def image_to_byte_array(image: Image) -> bytes:
    """Преобразование изображения PIL в байты."""
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


'''def draw_yolo_polygons(result, image: Image) -> tuple[list, Image]:
    draw = ImageDraw.Draw(image)
    detections = []
    class_names = result.names

    try:
        font = ImageFont.truetype("arial.ttf", size=12)
    except:
        font = ImageFont.load_default()

    boxes = result.boxes
    masks = result.masks

    if masks:
        for i, polygon in enumerate(masks.xy):
            class_id = int(boxes.cls[i])
            confidence = float(boxes.conf[i])
            class_name = class_names[class_id]

            coords = polygon.tolist()  # [[x1, y1], [x2, y2], ...]
            flat_coords = [coord for point in coords for coord in point]

            # Рисуем полигон
            draw.polygon(flat_coords, outline="red", width=2)

            # Центр полигона
            cx = sum(x for x, _ in coords) / len(coords)
            cy = sum(y for _, y in coords) / len(coords)
            draw.text((cx, cy), f"{class_name} {confidence:.2f}", fill="green", font=font)

            detections.append({
                "class_id": class_id,
                "class_name": class_name,
                "confidence": confidence,
                "polygon": coords
            })
    else:
        # Если масок нет — fallback на bounding boxes
        for i, box in enumerate(boxes.xyxy):
            class_id = int(boxes.cls[i])
            confidence = float(boxes.conf[i])
            class_name = class_names[class_id]
            x1, y1, x2, y2 = map(float, box.tolist())

            draw.rectangle([x1, y1, x2, y2], outline="blue", width=2)
            draw.text((x1, y1 - 10), f"{class_name} {confidence:.2f}", fill="blue", font=font)

            detections.append({
                "class_id": class_id,
                "class_name": class_name,
                "confidence": confidence,
                "bbox": [x1, y1, x2, y2]
            })

    return detections, image


def get_detection_results(model: YOLO, image: Image, scale_factor=1.0):
    results = model(image)
    return draw_yolo_polygons(results[0], image.copy())'''


def get_detection_results(model: YOLO, image: Image):
    results = model(image)
    result = results[0]

    detections = []
    class_names = result.names
    boxes = result.boxes

    for i in range(len(boxes)):
        class_id = int(boxes.cls[i])
        conf = float(boxes.conf[i])
        detections.append({
            "class_id": class_id,
            "class_name": class_names[class_id],
            "confidence": conf
        })

    # Получаем изображение с нанесёнными сегментами/боксами/подписями
    img_annotated = result.plot()  # numpy array (H, W, 3)
    image_pil = Image.fromarray(img_annotated)

    return detections, image_pil
