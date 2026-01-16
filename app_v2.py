"""
OMR Processing Microservice V2
Template-based approach for Korean CSAT OMR sheets
Focuses on grid detection and darkness analysis instead of circle detection
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import requests
from io import BytesIO
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_image(url: str) -> np.ndarray:
    """Download image from URL and convert to OpenCV format"""
    logger.info(f"Downloading image from: {url}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        logger.info(f"Image downloaded: {len(response.content)} bytes")

        image_bytes = BytesIO(response.content)
        image_array = np.asarray(bytearray(image_bytes.read()), dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Failed to decode image")

        logger.info(f"Image shape: {image.shape}")
        return image

    except Exception as e:
        logger.error(f"Download error: {e}")
        raise


def preprocess_for_grid(image: np.ndarray) -> tuple:
    """Preprocess image for grid detection"""
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply bilateral filter to reduce noise while preserving edges
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)

    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )

    return gray, thresh


def detect_answer_grid_regions(image: np.ndarray, thresh: np.ndarray) -> list:
    """
    Detect answer grid regions by finding rectangular contours
    Korean OMR sheets have bordered answer sections
    """
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours by area and aspect ratio
    grid_regions = []
    img_area = image.shape[0] * image.shape[1]

    for contour in contours:
        area = cv2.contourArea(contour)

        # Grid regions are typically 5-30% of image area
        if area < img_area * 0.02 or area > img_area * 0.5:
            continue

        x, y, w, h = cv2.boundingRect(contour)

        # Answer grids are wider than tall (multiple columns)
        aspect_ratio = w / h if h > 0 else 0

        if 0.8 < aspect_ratio < 3.0 and w > 200 and h > 300:
            grid_regions.append({
                'x': x, 'y': y, 'w': w, 'h': h,
                'area': area
            })

    # Sort by position (left to right, top to bottom)
    grid_regions.sort(key=lambda r: (r['y'], r['x']))

    logger.info(f"Detected {len(grid_regions)} potential answer grid regions")
    return grid_regions


def extract_answers_from_grid(image: np.ndarray, gray: np.ndarray,
                               grid: dict, num_questions: int) -> list:
    """
    Extract answers from a single grid region
    Uses grid-based sampling instead of circle detection
    """
    x, y, w, h = grid['x'], grid['y'], grid['w'], grid['h']

    # Extract grid region
    grid_img = gray[y:y+h, x:x+w]

    # Apply threshold to get binary image
    _, grid_thresh = cv2.threshold(grid_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Estimate number of rows and columns
    # Korean OMR typically has 2-3 columns with ~20 rows each
    estimated_rows_per_column = min(num_questions, 20)
    num_columns = 2  # Usually 2 main sections (문번 + 답란) per column set

    # Calculate cell dimensions
    row_height = h // estimated_rows_per_column

    # For each question, sample the answer area
    results = []

    # Simplified approach: divide horizontally into sections
    # Assume 2 main column sets (Q1-20 left, Q21+ right if exists)
    questions_per_section = min(num_questions, 20)

    for q in range(1, num_questions + 1):
        # Determine which section (left or right column set)
        section_idx = (q - 1) // questions_per_section
        question_in_section = ((q - 1) % questions_per_section)

        # Estimate row position
        row_y = int(question_in_section * row_height)

        if row_y + row_height > h:
            row_y = h - row_height

        # Extract row
        row_img = grid_thresh[row_y:row_y + row_height, :]

        if row_img.size == 0:
            results.append({
                'questionNumber': q,
                'selectedOption': '',
                'confidence': 0.0,
                'notes': 'Could not extract row'
            })
            continue

        # Divide row into 5 answer positions
        # Skip first part (question number area)
        answer_start = int(w * 0.2)  # First 20% is question number
        answer_width = w - answer_start
        bubble_width = answer_width // 5

        densities = []
        for pos in range(5):
            bubble_x = answer_start + (pos * bubble_width)
            bubble_region = row_img[:, bubble_x:bubble_x + bubble_width]

            if bubble_region.size == 0:
                densities.append(0.0)
                continue

            # Calculate darkness (white pixels in inverted image = dark in original)
            darkness = np.sum(bubble_region > 0) / bubble_region.size
            densities.append(darkness)

        # Find darkest bubble
        if not densities or max(densities) < 0.1:
            # No clear answer
            results.append({
                'questionNumber': q,
                'selectedOption': '',
                'confidence': 0.0,
                'ambiguous': False,
                'notes': 'No answer detected'
            })
        else:
            max_density = max(densities)
            selected_pos = densities.index(max_density) + 1

            # Check for ambiguous (multiple dark bubbles)
            dark_count = sum(1 for d in densities if d > max_density * 0.7)
            ambiguous = dark_count > 1

            results.append({
                'questionNumber': q,
                'selectedOption': str(selected_pos) if not ambiguous else '',
                'confidence': float(max_density),
                'ambiguous': ambiguous,
                'notes': f'Density: {max_density:.2f}' + (' - Multiple marks' if ambiguous else '')
            })

    return results


def process_omr_sheet(image_url: str, num_questions: int) -> dict:
    """Main OMR processing function"""
    logger.info(f"Processing OMR with {num_questions} questions")

    # Download image
    image = download_image(image_url)

    # Preprocess
    gray, thresh = preprocess_for_grid(image)

    # Detect grid regions
    grid_regions = detect_answer_grid_regions(image, thresh)

    if not grid_regions:
        # Fallback: use entire image as one grid
        logger.warning("No grid regions detected, using full image")
        grid_regions = [{
            'x': 0, 'y': int(image.shape[0] * 0.2),  # Skip top 20% (headers)
            'w': image.shape[1], 'h': int(image.shape[0] * 0.7)
        }]

    # Extract answers from the largest/best grid region
    main_grid = max(grid_regions, key=lambda g: g['area'] if 'area' in g else g['w'] * g['h'])

    results = extract_answers_from_grid(image, gray, main_grid, num_questions)

    logger.info(f"Extracted {len(results)} answers")

    return {
        'answers': results,
        'totalDetected': len(results),
        'gridRegions': len(grid_regions)
    }


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'version': 'v2-grid-based'}), 200


@app.route('/process-omr', methods=['POST'])
def process_omr():
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'No JSON data'}), 400

        image_url = data.get('imageUrl')
        num_questions = data.get('numberOfQuestions', 45)

        if not image_url:
            return jsonify({'error': 'imageUrl required'}), 400

        result = process_omr_sheet(image_url, num_questions)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
