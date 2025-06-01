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
