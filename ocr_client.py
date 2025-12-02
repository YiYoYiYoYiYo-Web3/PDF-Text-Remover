import os
import json
import cv2
import numpy as np
import pytesseract
import time
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables (if any)
load_dotenv()

class OCRClient:
    def __init__(self):
        """Initialize OpenCV, Tesseract OCR client, and OpenAI client for text merging."""
        # Configure Tesseract executable path if needed (Windows)
        tesseract_path = os.getenv('TESSERACT_PATH', '')
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Initialize OpenAI client for text merging
        api_base = os.getenv('OPENAI_API_BASE')
        api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL')
        
        if api_key:
            self.openai_client = OpenAI(
                api_key=api_key,
                base_url=api_base
            )
            print("[DEBUG OCR] OpenAI client initialized for text merging")
        else:
            self.openai_client = None
            print("[DEBUG OCR] No OpenAI API key found, skipping text merging")
        
        print("[DEBUG OCR] OCRClient initialized with OpenCV+Tesseract")
    
    def merge_text_blocks(self, text_blocks):
        """
        Merge detected text blocks into meaningful text blocks using OpenAI.
        
        Args:
            text_blocks: List of text blocks from OCR detection
            
        Returns:
            List: Merged text blocks
        """
        if not self.openai_client or not text_blocks:
            return text_blocks
        
        max_retries = 3  # Number of retries for AI merge
        
        for attempt in range(max_retries):
            try:
                print(f"[DEBUG OCR] Merging {len(text_blocks)} text blocks with AI (attempt {attempt+1}/{max_retries})...")
                
                # Prepare text blocks for AI input
                text_blocks_str = json.dumps(text_blocks, ensure_ascii=False, indent=2)
                
                # Use multi-line string with format method to avoid f-string issues
                prompt = """You are a text block merging expert. Please analyze the following text blocks detected by OCR and merge them into meaningful text blocks based on their positions and content.

Text blocks:
{text_blocks}

Instructions:
1. Merge adjacent text blocks that belong to the same line or paragraph
2. Calculate the merged bounding box to include all merged blocks
3. Preserve the original text content exactly
4. Use the average font information from merged blocks
5. Return ONLY a valid JSON array of merged text blocks in the same format as input
6. Do not add any additional text or explanations
7. Do not modify the text content
8. Ensure the JSON is properly formatted with correct quotes and commas
9. Do not use any escaped characters incorrectly

Example output format:
[
  {{
    "text": "完整的句子或段落",
    "bbox": {{"x": 100, "y": 50, "width": 300, "height": 50}},
    "font": {{
      "family": "Arial",
      "size": 14,
      "weight": "normal",
      "color": "#000000"
    }}
  }}
]""".format(text_blocks=text_blocks_str)
                
                # Call OpenAI-compatible API
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1  # Lower temperature for more deterministic results
                    # Removed max_tokens to allow full response
                )
                
                # Get and parse response
                content = response.choices[0].message.content
                print(f"[DEBUG OCR] AI merge response: {content[:500]}...")
                
                # Parse JSON from response
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                # Clean up any potential issues
                content = content.strip()
                
                # Try to fix common JSON issues
                try:
                    # First attempt with strict mode
                    merged_blocks = json.loads(content)
                except json.JSONDecodeError:
                    # Try with non-strict mode (handles some formatting issues)
                    try:
                        merged_blocks = json.loads(content, strict=False)
                    except json.JSONDecodeError:
                        # Try to fix truncated JSON by closing open structures
                        content_fixed = content
                        
                        # Count open/close brackets and braces
                        open_brackets = content_fixed.count('[') - content_fixed.count(']')
                        open_braces = content_fixed.count('{') - content_fixed.count('}')
                        
                        # Close any open structures
                        if open_braces > 0:
                            content_fixed += '}' * open_braces
                        if open_brackets > 0:
                            content_fixed += ']' * open_brackets
                        
                        # Try again with fixed content
                        print(f"[DEBUG OCR] Attempting to fix truncated JSON (added {open_braces} braces, {open_brackets} brackets)...")
                        merged_blocks = json.loads(content_fixed, strict=False)
                print(f"[DEBUG OCR] Merged to {len(merged_blocks)} text blocks")
                
                return merged_blocks
                
            except json.JSONDecodeError as e:
                print(f"[ERROR OCR] JSON parsing error during text merging (attempt {attempt+1}/{max_retries}): {e}")
                print(f"[ERROR OCR] Raw response: {content[:1000] if 'content' in locals() else 'No content'}")
                if attempt < max_retries - 1:
                    print(f"[DEBUG OCR] Retrying text merging...")
                    time.sleep(1)  # Wait 1 second before retry
            except Exception as e:
                print(f"[ERROR OCR] Failed to merge text blocks (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"[DEBUG OCR] Retrying text merging...")
                    time.sleep(1)  # Wait 1 second before retry
        
        # Return original blocks if all retries fail
        print(f"[ERROR OCR] All {max_retries} attempts failed, using original text blocks...")
        return text_blocks
    
    def extract_text_layout(self, image):
        """
        Extract text, positions, and formatting from an image using Tesseract.
        
        Args:
            image: PIL Image object
            
        Returns:
            dict: Text layout information in JSON format
            {
                "text_blocks": [
                    {
                        "text": "Sample text",
                        "bbox": {"x": 100, "y": 50, "width": 200, "height": 30},
                        "font": {
                            "family": "Arial",
                            "size": 14,
                            "weight": "normal",  # normal, bold
                            "color": "#000000"
                        }
                    }
                ]
            }
        """
        try:
            print(f"[DEBUG OCR] Processing image of size: {image.size} pixels")
            
            # Verify image is not corrupt
            image.verify()
            image = image.copy()  # Create a fresh copy after verify
            
            # Convert PIL Image to numpy array (OpenCV format) and grayscale
            img_array = np.array(image)
            gray_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Step 2: Perform OCR with Tesseract
            # Configure Tesseract for Chinese + English recognition with optimized settings
            # Use simpler configuration for better Chinese recognition
            custom_config = r'--oem 3 --psm 3 -l chi_sim+eng '
            
            # Get detailed OCR results with bounding boxes
            ocr_results = pytesseract.image_to_data(
                gray_img, 
                config=custom_config, 
                output_type=pytesseract.Output.DICT
            )
            
            print(f"[DEBUG OCR] Tesseract OCR completed, found {len(ocr_results['text'])} text elements")
            
            # Step 3: Process OCR results
            text_blocks = []
            height, width = gray_img.shape
            
            # Debug: Show all OCR results including confidence scores
            print(f"[DEBUG OCR] Raw OCR results for page:")
            for i in range(len(ocr_results['text'])):
                text = ocr_results['text'][i].strip()
                confidence = int(ocr_results['conf'][i])
                
                # Only show non-empty text results
                if text:
                    print(f"[DEBUG OCR]   [{i}] Text: '{text}' | Confidence: {confidence}%")
                
                # Skip empty text or low confidence results
                if not text or confidence < 60:
                    if text:
                        print(f"[DEBUG OCR]   Skipping low confidence text: '{text}' (confidence: {confidence}%)")
                    continue
                
                # Get bounding box coordinates
                x = ocr_results['left'][i]
                y = ocr_results['top'][i]
                w = ocr_results['width'][i]
                h = ocr_results['height'][i]
                
                # Ensure coordinates are within image bounds
                x = max(0, x)
                y = max(0, y)
                w = min(width - x, w)
                h = min(height - y, h)
                
                # Estimate font size based on bounding box height
                # Approximate conversion: 1 pixel ≈ 0.75 point
                font_size = round(h * 0.75, 1)
                
                # Create text block entry
                text_block = {
                    "text": text,
                    "bbox": {
                        "x": x,
                        "y": y,
                        "width": w,
                        "height": h
                    },
                    "font": {
                        "family": "Arial",  # Tesseract doesn't provide font family
                        "size": font_size,
                        "weight": "normal",  # Tesseract doesn't provide font weight
                        "color": "#000000"  # Tesseract doesn't provide font color
                    }
                }
                
                print(f"[DEBUG OCR]   Adding text block: '{text}' at position ({x}, {y})")
                text_blocks.append(text_block)
            
            print(f"[DEBUG OCR] Processed {len(text_blocks)} valid text blocks")
            
            # Merge text blocks using AI
            merged_blocks = self.merge_text_blocks(text_blocks)
            
            # Return in the expected format
            layout_data = {
                "text_blocks": merged_blocks
            }
            
            return layout_data
            
        except Exception as e:
            print(f"[ERROR OCR] Unexpected error during OCR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return {"text_blocks": []}
