from io import BytesIO

from PIL import Image
from ultralytics import YOLO


def load_model(model_path: str) -> YOLO:
    """Загрузка модели YOLO."""
    return YOLO(model_path)


def process_image(image_bytes: bytes) -> Image:
    """Конвертация байтового потока в PIL Image."""
    return Image.open(BytesIO(image_bytes)).convert("RGB")


def get_inference_results(model: YOLO, image: Image) -> dict:
    """Запуск классификации и возврат результатов."""
    results = model(image)

    probs = results[0].probs

    # Получаем все вероятности и имена классов
    all_confidences = probs.data.tolist()  # Вероятности для всех классов
    class_names = model.names  # Словарь с именами классов

    # Формируем список всех классов с их вероятностями
    all_classes = [
        {
            "class_id": int(class_id),
            "class_name": class_names[class_id],
            "confidence": float(confidence)
        }
        for class_id, confidence in enumerate(all_confidences)
    ]

    # Находим класс с максимальной вероятностью
    top_class = int(probs.top1)
    top_confidence = float(probs.top1conf)

    return {
        "top_class": top_class,
        "top_confidence": top_confidence,
        "top_class_name": class_names[top_class],
        "all_classes": all_classes,
        "class_names": list(class_names.values())  # Все имена классов для справки
    }