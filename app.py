"""
OMR Processing Microservice - Row-by-Row AI Approach
Crops individual question rows and uses AI to detect filled bubbles
Much more accurate than analyzing entire sheet at once
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import requests
from io import BytesIO
import logging
import os
import base64
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_image(url: str) -> np.ndarray:
    """Download image from URL"""
    logger.info(f"Downloading: {url[:100]}...")
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Failed to decode image")

    logger.info(f"Image loaded: {image.shape}")
    return image


def detect_answer_grid_bounds(image: np.ndarray) -> dict:
    """
    Detect the bounds of the answer grid area
    Returns approximate coordinates for the main answer area
    """
    height, width = image.shape[:2]

    # Korean OMR sheets typically have:
    # - Top 15-20%: Student info (ignore)
    # - Middle 60-70%: Answer grid
    # - Bottom 10-15%: Instructions (ignore)

    # Start after student info section
    grid_start_y = int(height * 0.15)
    grid_end_y = int(height * 0.85)

    # Answer columns are usually in the middle-right area
    grid_start_x = int(width * 0.15)
    grid_end_x = int(width * 0.95)

    return {
        'x': grid_start_x,
        'y': grid_start_y,
        'width': grid_end_x - grid_start_x,
        'height': grid_end_y - grid_start_y
    }


def extract_question_rows(image: np.ndarray, num_questions: int) -> list:
    """
    Divide the answer grid into individual question rows
    Returns list of cropped images, one per question
    """
    grid_bounds = detect_answer_grid_bounds(image)

    x = grid_bounds['x']
    y = grid_bounds['y']
    width = grid_bounds['width']
    height = grid_bounds['height']

    # Extract grid region
    grid_image = image[y:y+height, x:x+width]

    # Calculate row height based on number of questions
    # Assume max 20 questions per column for Korean OMR
    rows_per_column = min(num_questions, 20)
    row_height = height // rows_per_column

    question_rows = []

    for q in range(num_questions):
        # Determine which column this question is in
        column_idx = q // rows_per_column
        row_in_column = q % rows_per_column

        # Calculate column offset (for multi-column layouts)
        column_width = width // 2  # Assume 2 main columns
        col_x = column_idx * column_width

        # Calculate row position
        row_y = row_in_column * row_height

        # Add some padding to ensure we get the full row
        padding = int(row_height * 0.1)
        row_y_start = max(0, row_y - padding)
        row_y_end = min(grid_image.shape[0], row_y + row_height + padding)
        row_x_start = max(0, col_x)
        row_x_end = min(grid_image.shape[1], col_x + column_width)

        # Crop the row
        row_img = grid_image[row_y_start:row_y_end, row_x_start:row_x_end]

        if row_img.size > 0:
            question_rows.append(row_img)
        else:
            # Fallback: use a blank image
            question_rows.append(np.zeros((50, width, 3), dtype=np.uint8))

    logger.info(f"Extracted {len(question_rows)} question rows")
    return question_rows


def image_to_base64(image: np.ndarray) -> str:
    """Convert OpenCV image to base64 string"""
    _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 95])
    base64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_str}"


def analyze_row_with_ai(row_image: np.ndarray, question_number: int, api_key: str) -> dict:
    """
    Use OpenAI to analyze a single question row
    Much simpler task = higher accuracy
    """
    # Convert row to base64
    base64_image = image_to_base64(row_image)

    # Simple, focused prompt for a single row
    prompt = f"""This is ONE row from a Korean OMR answer sheet for question {question_number}.

You will see 5 answer bubbles numbered ① ② ③ ④ ⑤ (or 1 2 3 4 5).

FILLED bubble = SOLID BLACK or DARK SHADED inside
EMPTY bubble = Pink/orange circle with visible number

Look at the 5 bubbles from LEFT to RIGHT.
Which position (1, 2, 3, 4, or 5) is FILLED/DARK?

Return JSON:
{{"selectedOption": "X", "confidence": 0.95}}

Where X is "1", "2", "3", "4", or "5" for the filled bubble, or "" if none filled."""

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": base64_image, "detail": "high"}}
                        ]
                    }
                ],
                "max_tokens": 50,
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            parsed = json.loads(content)

            selected = parsed.get('selectedOption', '')
            confidence = parsed.get('confidence', 0.8)

            logger.info(f"Q{question_number}: {selected} (conf: {confidence})")

            return {
                'questionNumber': question_number,
                'selectedOption': selected,
                'confidence': float(confidence),
                'ambiguous': False,
                'notes': 'Row-by-row AI'
            }
        else:
            logger.error(f"AI error Q{question_number}: {response.status_code}")
            return {
                'questionNumber': question_number,
                'selectedOption': '',
                'confidence': 0.0,
                'ambiguous': False,
                'notes': f'AI error: {response.status_code}'
            }

    except Exception as e:
        logger.error(f"Exception Q{question_number}: {e}")
        return {
            'questionNumber': question_number,
            'selectedOption': '',
            'confidence': 0.0,
            'ambiguous': False,
            'notes': f'Error: {str(e)}'
        }


def process_omr_sheet(image_url: str, num_questions: int) -> dict:
    """Main processing function"""
    logger.info(f"Processing {num_questions} questions with row-by-row AI")

    # Get OpenAI API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    # Download image
    image = download_image(image_url)

    # Extract individual question rows
    question_rows = extract_question_rows(image, num_questions)

    # Analyze each row with AI in parallel (faster!)
    results = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_question = {
            executor.submit(analyze_row_with_ai, row_img, idx + 1, api_key): idx + 1
            for idx, row_img in enumerate(question_rows)
        }

        for future in as_completed(future_to_question):
            question_num = future_to_question[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Q{question_num} failed: {e}")
                results.append({
                    'questionNumber': question_num,
                    'selectedOption': '',
                    'confidence': 0.0,
                    'ambiguous': False,
                    'notes': f'Error: {str(e)}'
                })

    # Sort results by question number
    results.sort(key=lambda x: x['questionNumber'])

    logger.info(f"Completed {len(results)} questions")

    return {
        'answers': results,
        'totalDetected': len(results),
        'rowsDetected': num_questions
    }


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'version': 'row-by-row-ai'}), 200


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
