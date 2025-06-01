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


def get_detection_results(model: YOLO, image: Image):
    """Запуск детекции объектов и возврат результатов + изображения с box'ами."""

    # Прогон через модель
    results = model(image)
    result = results[0]

    detections = []
    boxes = result.boxes
    class_names = model.names

    for i in range(len(boxes)):
        class_id = int(boxes.cls[i])
        conf = float(boxes.conf[i])
        x1, y1, x2, y2 = boxes.xyxy[i].tolist()

        detections.append({
            "class_id": class_id,
            "class_name": class_names[class_id],
            "confidence": conf,
            "box": [x1, y1, x2, y2]
        })

    # Получаем изображение с нанесёнными боксами и метками
    img_annotated = result.plot()
    image_with_boxes = Image.fromarray(img_annotated)

    return detections, image_with_boxes
