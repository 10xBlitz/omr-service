#!/bin/bash
# Quick test script for OMR service

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SERVICE_URL="https://omr-service.onrender.com"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}OMR Service Test${NC}"
echo -e "${BLUE}========================================${NC}"

# Test 1: Health check
echo -e "\n${BLUE}1. Testing health endpoint...${NC}"
HEALTH=$(curl -s "${SERVICE_URL}/health")
echo "$HEALTH" | python3 -m json.tool

# Test 2: Process OMR
if [ -z "$1" ]; then
    echo -e "\n${RED}Error: Please provide an image URL${NC}"
    echo "Usage: ./test_local.sh <image_url> [num_questions]"
    echo ""
    echo "Example:"
    echo "  ./test_local.sh https://storage.supabase.co/image.jpg 45"
    exit 1
fi

IMAGE_URL="$1"
NUM_QUESTIONS="${2:-45}"

echo -e "\n${BLUE}2. Testing OMR processing...${NC}"
echo -e "   Image: ${IMAGE_URL}"
echo -e "   Questions: ${NUM_QUESTIONS}"
echo ""

curl -X POST "${SERVICE_URL}/process-omr" \
  -H "Content-Type: application/json" \
  -d "{\"imageUrl\": \"${IMAGE_URL}\", \"numberOfQuestions\": ${NUM_QUESTIONS}}" \
  -w "\n\nHTTP Status: %{http_code}\n" \
  | python3 -m json.tool | tee omr_result.json

echo -e "\n${GREEN}✓ Result saved to omr_result.json${NC}"
