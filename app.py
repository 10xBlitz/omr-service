"""
OMR Processing Microservice
Uses OpenCV for accurate bubble detection and fill analysis
Deploy on Render.com (free tier)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import requests
from io import BytesIO
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for Supabase Edge Functions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_image(url: str) -> np.ndarray:
    """Download image from URL and convert to OpenCV format"""
    response = requests.get(url)
    image_bytes = BytesIO(response.content)
    image_array = np.asarray(bytearray(image_bytes.read()), dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    return image


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """Convert to grayscale and apply thresholding"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # Binary threshold
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return thresh


def detect_circles(image: np.ndarray) -> list:
    """Detect circular bubbles using Hough Circle Transform"""
    circles = cv2.HoughCircles(
        image,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=20,  # Minimum distance between circle centers
        param1=50,
        param2=30,
        minRadius=10,
        maxRadius=40
    )

    if circles is not None:
        circles = np.uint16(np.around(circles))
        return circles[0, :].tolist()
    return []


def calculate_fill_density(image: np.ndarray, x: int, y: int, radius: int) -> float:
    """Calculate how filled a bubble is (0.0 = empty, 1.0 = completely filled)"""
    # Create a mask for the circle
    mask = np.zeros(image.shape, dtype=np.uint8)
    cv2.circle(mask, (x, y), radius, 255, -1)

    # Count dark pixels within the circle
    circle_pixels = cv2.bitwise_and(image, image, mask=mask)
    total_pixels = cv2.countNonZero(mask)
    dark_pixels = cv2.countNonZero(circle_pixels)

    if total_pixels == 0:
        return 0.0

    fill_density = dark_pixels / total_pixels
    return fill_density


def group_bubbles_by_rows(circles: list, tolerance: int = 15) -> dict:
    """Group detected circles into rows based on Y coordinates"""
    if not circles:
        return {}

    # Sort by Y coordinate
    sorted_circles = sorted(circles, key=lambda c: c[1])

    rows = {}
    current_row = 0
    current_y = sorted_circles[0][1]

    for circle in sorted_circles:
        x, y, r = circle

        # If Y is significantly different, start a new row
        if abs(y - current_y) > tolerance:
            current_row += 1
            current_y = y

        if current_row not in rows:
            rows[current_row] = []

        rows[current_row].append({"x": x, "y": y, "radius": r})

    return rows


def process_omr_sheet(image_url: str, num_questions: int) -> dict:
    """Main OMR processing function"""
    logger.info(f"Processing OMR sheet: {image_url}")

    # Step 1: Download image
    image = download_image(image_url)
    logger.info(f"Image downloaded: {image.shape}")

    # Step 2: Preprocess
    thresh = preprocess_image(image)

    # Step 3: Detect circles
    circles = detect_circles(thresh)
    logger.info(f"Detected {len(circles)} circles")

    if not circles:
        return {"error": "No bubbles detected in image"}

    # Step 4: Group circles into rows
    rows = group_bubbles_by_rows(circles)
    logger.info(f"Grouped into {len(rows)} rows")

    # Step 5: Analyze each row
    results = []

    for question_num in range(1, num_questions + 1):
        if question_num - 1 >= len(rows):
            # Question row not found
            results.append({
                "questionNumber": question_num,
                "selectedOption": "",
                "confidence": 0.0,
                "ambiguous": False,
                "notes": "Row not detected"
            })
            continue

        row_bubbles = rows[question_num - 1]
        # Sort bubbles by X coordinate (left to right)
        row_bubbles = sorted(row_bubbles, key=lambda b: b["x"])

        # Should have 5 bubbles per question
        if len(row_bubbles) != 5:
            logger.warning(f"Q{question_num}: Expected 5 bubbles, found {len(row_bubbles)}")

        # Analyze fill density for each bubble
        bubble_densities = []
        for idx, bubble in enumerate(row_bubbles[:5]):  # Take first 5
            density = calculate_fill_density(
                thresh,
                bubble["x"],
                bubble["y"],
                bubble["radius"]
            )
            bubble_densities.append({
                "position": idx + 1,
                "density": density,
                "isFilled": density > 0.5  # 50% threshold
            })

        # Determine selected answer
        filled_bubbles = [b for b in bubble_densities if b["isFilled"]]

        if len(filled_bubbles) == 1:
            # Exactly one bubble filled (correct)
            selected = filled_bubbles[0]
            results.append({
                "questionNumber": question_num,
                "selectedOption": str(selected["position"]),
                "confidence": selected["density"],
                "ambiguous": False,
                "notes": f"Clear fill at position {selected['position']}"
            })
        elif len(filled_bubbles) > 1:
            # Multiple bubbles filled (ambiguous)
            results.append({
                "questionNumber": question_num,
                "selectedOption": "",
                "confidence": 0.0,
                "ambiguous": True,
                "notes": f"Multiple bubbles filled: {[b['position'] for b in filled_bubbles]}"
            })
        else:
            # No bubbles filled
            results.append({
                "questionNumber": question_num,
                "selectedOption": "",
                "confidence": 0.0,
                "ambiguous": False,
                "notes": "No answer selected"
            })

    logger.info(f"Processing complete: {len(results)} questions analyzed")

    return {
        "answers": results,
        "totalDetected": len(circles),
        "rowsDetected": len(rows)
    }


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "OMR Processing"}), 200


@app.route('/process-omr', methods=['POST'])
def process_omr():
    """Process OMR sheet endpoint"""
    try:
        data = request.json

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        image_url = data.get('imageUrl')
        num_questions = data.get('numberOfQuestions', 45)

        if not image_url:
            return jsonify({"error": "imageUrl is required"}), 400

        result = process_omr_sheet(image_url, num_questions)

        if "error" in result:
            return jsonify(result), 400

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error processing OMR: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # For local development
    app.run(host='0.0.0.0', port=5000, debug=True)
