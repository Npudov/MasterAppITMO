import pathlib

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from src.app.inferenceApi.yoloClassificationUtils import *

# Загрузка модели YOLO для классификации
model = load_model(f"{pathlib.Path(__file__).resolve().parent}/weights/best_classification_yolo_nano.pt")

app = FastAPI(title="YOLO Classification Scoliosis API")


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """API endpoint для классификации изображения."""
    image_bytes = await file.read()
    image = process_image(image_bytes)

    # Предсказание
    result = get_inference_results(model, image)

    return JSONResponse(content=result)
