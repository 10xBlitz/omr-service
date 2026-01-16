#!/usr/bin/env python3
"""
Test script for OMR service
Usage: python test_service.py <image_url> [num_questions]
"""

import requests
import sys
import json

def test_omr_service(image_url, num_questions=45, service_url="https://omr-service.onrender.com"):
    """Test the OMR processing service"""

    print(f"Testing OMR Service: {service_url}")
    print(f"Image URL: {image_url}")
    print(f"Number of questions: {num_questions}")
    print("-" * 80)

    # Test health endpoint first
    print("\n1. Testing health endpoint...")
    try:
        health_response = requests.get(f"{service_url}/health")
        print(f"   Status: {health_response.status_code}")
        print(f"   Response: {health_response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
        return

    # Test OMR processing
    print("\n2. Testing OMR processing...")
    try:
        response = requests.post(
            f"{service_url}/process-omr",
            json={
                "imageUrl": image_url,
                "numberOfQuestions": num_questions
            },
            timeout=60
        )

        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\n   ✅ Success!")
            print(f"   Total Detected: {result.get('totalDetected')}")
            print(f"   Rows Detected: {result.get('rowsDetected')}")
            print(f"   Answers Found: {len(result.get('answers', []))}")

            # Show first 10 answers
            print(f"\n   First 10 Answers:")
            for ans in result.get('answers', [])[:10]:
                status = "✓" if ans.get('selectedOption') else "○"
                print(f"      {status} Q{ans['questionNumber']}: {ans.get('selectedOption', 'empty')} "
                      f"(confidence: {ans.get('confidence', 0):.2f}) - {ans.get('notes', '')}")

            if len(result.get('answers', [])) > 10:
                print(f"   ... and {len(result['answers']) - 10} more")

            # Save full result to file
            with open('omr_test_result.json', 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n   Full result saved to: omr_test_result.json")

        else:
            print(f"   ❌ Error: {response.text}")

    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_service.py <image_url> [num_questions]")
        print("\nExample:")
        print("  python test_service.py https://your-storage.supabase.co/image.jpg 45")
        sys.exit(1)

    image_url = sys.argv[1]
    num_questions = int(sys.argv[2]) if len(sys.argv) > 2 else 45

    test_omr_service(image_url, num_questions)
