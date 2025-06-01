import pathlib
import json
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse

from src.app.inferenceApi.yoloCTDetectionUtils import *

model = load_model(f"{pathlib.Path(__file__).resolve().parent}/weights/best_ct_detection_yolo_small.pt")

app = FastAPI(title="YOLO CT Object Detection API")


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    """API endpoint для Object Detection."""
    image_bytes = await file.read()
    image = process_image(image_bytes)

    detections, image_with_boxes = get_detection_results(model, image)

    img_byte_arr = image_to_byte_array(image_with_boxes)

    return StreamingResponse(
        BytesIO(img_byte_arr),
        media_type="image/jpeg",
        headers={"X-Detection-Results": json.dumps({"detections": detections}),
                 }
    )