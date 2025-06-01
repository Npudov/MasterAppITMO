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


'''def scale_image_and_annotations(image, detections, scale_factor=1.0):
    """Масштабирует изображение и все аннотации (боксы, текст)"""
    # Масштабируем изображение
    new_width = int(image.width * scale_factor)
    new_height = int(image.height * scale_factor)
    scaled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Масштабируем координаты боксов
    scaled_detections = []
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        scaled_box = [
            x1 * scale_factor,
            y1 * scale_factor,
            x2 * scale_factor,
            y2 * scale_factor
        ]
        scaled_detections.append({
            **det,
            "box": scaled_box
        })

    return scaled_image, scaled_detections'''


'''def get_detection_results(model: YOLO, image: Image, scale_factor=1.0):
    """Запуск детекции объектов и возврат результатов + изображения с box'ами."""
    # Сначала масштабируем само изображение
    new_width = int(image.width * scale_factor)
    new_height = int(image.height * scale_factor)
    scaled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    results = model(image)

    boxes = results[0].boxes

    class_names = model.names

    # Подготовка шрифта (увеличиваем размер пропорционально scale_factor)
    try:
        font = ImageFont.truetype("arial.ttf", size=8)
    except:
        font = ImageFont.load_default()

    # Создаем копию изображения для рисования
    image_with_boxes = scaled_image.copy()
    draw = ImageDraw.Draw(image_with_boxes)

    detections = []

    for box in boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        x1 *= scale_factor
        y1 *= scale_factor
        x2 *= scale_factor
        y2 *= scale_factor

        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        class_name = class_names[class_id]
        #label = f"{class_name} {confidence:.2f}"

        # Получаем размеры текста
        #text_bbox = draw.textbbox((0, 0), label, font=font)
        #text_width = text_bbox[2] - text_bbox[0]
        #text_height = text_bbox[3] - text_bbox[1]

        # Координаты для текста (чуть выше или ниже бокса)
        #text_x = x1 + 2
        #text_y = y1 - text_height - 2 if y1 - text_height > 0 else y1 + 2

        # Подложка под текст
        #draw.rectangle(
        #    [text_x - 1, text_y - 1, text_x + text_width + 1, text_y + text_height + 1],
        #    fill='black'
        #)

        draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
        # Рисуем текст
        #draw.text((text_x, text_y), label, fill="green", font=font)

        draw.text(((x1 + x2) / 2, (y1 + y2) / 2), f"{class_name} {confidence:.2f}", fill="green", font=font)

        detections.append({
            "class_id": class_id,
            "class_name": class_name,
            "confidence": confidence,
            "box": [x1, y1, x2, y2]
        })

        # Масштабируем результат
        #if scale_factor != 1.0:
        #    image_with_boxes, detections = scale_image_and_annotations(
        #        image_with_boxes,
        #        detections,
        #        scale_factor
        #    )

    return detections, image_with_boxes'''


def get_detection_results(model: YOLO, image: Image):
    """Запуск детекции объектов и возврат результатов + изображения с box'ами."""

    # Масштабируем изображение, если нужно
    '''if scale_factor != 1.0:
        new_width = int(image.width * scale_factor)
        new_height = int(image.height * scale_factor)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)'''

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
