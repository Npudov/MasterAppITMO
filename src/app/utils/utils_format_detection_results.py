
def format_detection_results(detections):
    """Форматирует результаты детекции для отображения"""
    if not detections.get("detections"):
        return "Объекты не обнаружены"

    #text = f"Обнаружено (масштаб x{scale:.1f}):\n"
    text = f"Обнаружено:\n"
    # Сортировка по confidence в убывающем порядке
    sorted_detections = sorted(
        detections["detections"],
        key=lambda x: x["confidence"],
        reverse=True
    )

    # Формируем текст результатов
    for det in sorted_detections:
        text += f"- {det['class_name']}: {det['confidence']:.2f}\n"

    return text
