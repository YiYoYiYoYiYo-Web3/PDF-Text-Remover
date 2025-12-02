import os
import sys
import argparse
import time
import json
import shutil
from dotenv import load_dotenv
from pdf_processor import extract_images_from_pdf, save_images_to_pdf
from api_client import APIClient
from ocr_client import OCRClient
from ppt_builder import create_ppt_from_pages
from utils import image_to_base64, extract_url_from_text, download_image_from_url

# Load environment variables
load_dotenv()

# Constants for progress tracking
PROGRESS_FILE = 'progress.json'
TEMP_DIR = '.temp'

# Progress display functions
def print_progress(current, total, stage="Processing", bar_length=40):
    """Print a progress bar to the console."""
    if total == 0:
        return
    
    progress = current / total
    filled_length = int(bar_length * progress)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    percent = round(progress * 100, 1)
    
    sys.stdout.write(f'\r{stage}: [{bar}] {percent}% ({current}/{total})')
    sys.stdout.flush()
    
    if current == total:
        sys.stdout.write('\n')

def process_page_with_retry(client, img, max_retries=5):
    """Process a single page with retry logic."""
    img_b64 = image_to_base64(img)
    
    for attempt in range(max_retries):
        if attempt > 0:
            print(f"  Retry attempt {attempt}/{max_retries-1}...")
            time.sleep(2)  # Wait 2 seconds before retry
        
        # Call API
        result_text = client.process_image(img_b64)
        
        if result_text:
            print(f"  API Response: {result_text[:100]}...")
            
            # Check for URL
            url = extract_url_from_text(result_text)
            if url:
                print(f"  Found image URL: {url}")
                new_img = download_image_from_url(url)
                if new_img:
                    return new_img
            else:
                print("  No URL found in response.")
    
    return None

import threading
import concurrent.futures

def create_temp_dirs(input_path):
    """Create temporary directories for storing intermediate results."""
    # Create main temp dir if not exists
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    
    # Create input-specific subdir based on input filename
    input_basename = os.path.basename(input_path)
    input_temp_dir = os.path.join(TEMP_DIR, os.path.splitext(input_basename)[0])
    
    # Create subdirs for different stages
    os.makedirs(input_temp_dir, exist_ok=True)
    os.makedirs(os.path.join(input_temp_dir, 'original_images'), exist_ok=True)
    os.makedirs(os.path.join(input_temp_dir, 'layouts'), exist_ok=True)
    os.makedirs(os.path.join(input_temp_dir, 'processed_images'), exist_ok=True)
    
    return input_temp_dir

def save_progress(input_path, stage, completed=None, total=None):
    """Save progress to JSON file."""
    # Load existing progress if any
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            progress = json.load(f)
    else:
        progress = {}
    
    # Update progress for this input file
    if input_path not in progress:
        progress[input_path] = {}
    
    progress[input_path]['stage'] = stage
    if completed is not None:
        progress[input_path]['completed'] = completed
    if total is not None:
        progress[input_path]['total'] = total
    
    # Save updated progress
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def load_progress(input_path):
    """Load progress from JSON file."""
    if not os.path.exists(PROGRESS_FILE):
        return None
    
    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        progress = json.load(f)
    
    return progress.get(input_path, None)

def delete_progress(input_path):
    """Delete progress for a specific input file."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            progress = json.load(f)
        
        if input_path in progress:
            del progress[input_path]
            
        # Save updated progress
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

def main():
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("Warning: .env file not found, using default settings.")
    
    # Load environment variables for feature flags
    skip_ocr_env = os.getenv('SKIP_OCR', 'false').lower() == 'true'
    skip_image_gen_env = os.getenv('SKIP_IMAGE_GEN', 'false').lower() == 'true'
    input_pdf_env = os.getenv('INPUT_PDF', '')
    output_path_env = os.getenv('OUTPUT_PATH', '')
    output_format_env = os.getenv('OUTPUT_FORMAT', 'pptx')
    
    # Create argument parser
    parser = argparse.ArgumentParser(description="Remove text from PDF using AI.")
    parser.add_argument("input_pdf", nargs='?', help="Path to the input PDF file", default=input_pdf_env)
    parser.add_argument("--output", help="Path to the output file", default=output_path_env)
    parser.add_argument("--output-format", choices=['pdf', 'pptx'], default=output_format_env,
                        help="Output format: pdf (legacy) or pptx (enhanced, default)")
    parser.add_argument("--skip-ocr", action='store_true',
                        help="Skip OCR text extraction (for legacy PDF workflow)",
                        default=skip_ocr_env)
    parser.add_argument("--skip-image-gen", action='store_true',
                        help="Skip AI image generation, use original images",
                        default=skip_image_gen_env)
    parser.add_argument("--clean", action='store_true',
                        help="Clean all temporary files and progress for the input file")
    
    args = parser.parse_args()
    
    # Get input PDF path from args or env, ensure it exists
    input_path = args.input_pdf
    if not input_path:
        print("Error: No input PDF specified. Use either command line argument or INPUT_PDF in .env")
        return
    
    if not os.path.exists(input_path):
        print(f"Error: File {input_path} not found.")
        return

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        base, ext = os.path.splitext(input_path)
        output_ext = '.pptx' if args.output_format == 'pptx' else '.pdf'
        output_path = f"{base}_no_text{output_ext}"
    
    # Create temporary directories
    input_temp_dir = create_temp_dirs(input_path)
    
    # Clean option handling
    if args.clean:
        print(f"Cleaning temporary files and progress for {input_path}...")
        # Delete input-specific temp dir
        if os.path.exists(input_temp_dir):
            shutil.rmtree(input_temp_dir)
        # Delete progress entry
        delete_progress(input_path)
        print("Clean completed.")
        return
    
    # Load existing progress if any
    progress = load_progress(input_path)
    print(f"Progress: {progress}") if progress else print("No existing progress found.")
    
    # Print feature flags
    print("=" * 60)
    print("Feature Flags:")
    print("=" * 60)
    print(f"Skip OCR: {args.skip_ocr}")
    print(f"Skip Image Generation: {args.skip_image_gen}")
    print(f"Input PDF: {input_path}")
    print(f"Output: {output_path}")
    print(f"Format: {args.output_format.upper()}")
    print("=" * 60)

    print("=" * 60)
    print("PDF Text Remover - Enhanced Workflow with Progress Tracking")
    print("=" * 60)
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Format: {args.output_format.upper()}")
    print(f"Temp Dir: {input_temp_dir}")
    print("=" * 60)

    # Step 1: Extract Images from PDF (with resumption)
    print("\n[Step 1/3] Extracting images from PDF...")
    
    # Check if we can resume from existing images
    original_images_dir = os.path.join(input_temp_dir, 'original_images')
    existing_images = sorted([f for f in os.listdir(original_images_dir) if f.endswith('.png')])
    
    from PIL import Image, UnidentifiedImageError
    images = []
    need_reextract = False
    
    if progress and progress.get('stage') >= 1 and existing_images:
        print(f"  Resuming from {len(existing_images)} existing images")
        # Load existing images
        for img_file in existing_images:
            img_path = os.path.join(original_images_dir, img_file)
            try:
                img = Image.open(img_path)
                # Verify image is not corrupt by accessing a property
                img.verify()
                img = Image.open(img_path)  # Reopen after verify
                images.append(img)
            except (UnidentifiedImageError, IOError, SyntaxError) as e:
                print(f"  ✗ Corrupt image found: {img_file}, will reextract")
                need_reextract = True
                break
    else:
        need_reextract = True
    
    if need_reextract:
        # Extract images from PDF
        try:
            print(f"  Extracting images from PDF...")
            images = extract_images_from_pdf(input_path)
            print(f"  ✓ Extracted {len(images)} pages")
            
            # Save extracted images for resumption
            for i, img in enumerate(images):
                img_path = os.path.join(original_images_dir, f'page_{i+1}.png')
                img.save(img_path, format='PNG')
            
            # Save progress
            save_progress(input_path, 1, completed=len(images), total=len(images))
        except Exception as e:
            print(f"  ✗ Error extracting images: {e}")
            return

    # Initialize clients
    client = APIClient()
    ocr_client = OCRClient() if args.output_format == 'pptx' and not args.skip_ocr else None

    # Step 2: Process pages in parallel - OCR and AI background generation (with resumption)
    print("\n[Step 2/3] Processing pages in parallel...")
    
    # Prepare results lists
    total_pages = len(images)
    layouts = [{"text_blocks": []} for _ in images]
    processed_images = [None] * len(images)
    
    # Check for existing results
    layouts_dir = os.path.join(input_temp_dir, 'layouts')
    processed_images_dir = os.path.join(input_temp_dir, 'processed_images')
    
    existing_layouts = sorted([f for f in os.listdir(layouts_dir) if f.endswith('.json')])
    existing_processed_images = sorted([f for f in os.listdir(processed_images_dir) if f.endswith('.png')])
    
    # Load existing results if any
    from PIL import Image
    pages_need_ocr = []
    pages_need_image_gen = []
    
    for i in range(total_pages):
        # Load existing layout if available
        layout_file = os.path.join(layouts_dir, f'layout_{i+1}.json')
        if os.path.exists(layout_file):
            with open(layout_file, 'r', encoding='utf-8') as f:
                layouts[i] = json.load(f)
            print(f"  ✗ Resuming layout for page {i+1}")
        elif ocr_client:
            pages_need_ocr.append(i)
        
        # Load existing processed image if available
        processed_img_file = os.path.join(processed_images_dir, f'page_{i+1}.png')
        if os.path.exists(processed_img_file):
            processed_images[i] = Image.open(processed_img_file)
            print(f"  ✗ Resuming processed image for page {i+1}")
        elif not args.skip_image_gen:
            pages_need_image_gen.append(i)
    
    # Process OCR in parallel (max 3 workers)
    def process_ocr(index, img):
        """Process OCR for a single page"""
        print(f"  OCR processing page {index+1}/{total_pages}...")
        
        layout_file = os.path.join(layouts_dir, f'layout_{index+1}.json')
        try:
            layout = ocr_client.extract_text_layout(img)
            # Save original image dimensions in layout for coordinate mapping
            original_width, original_height = img.size
            layout['original_size'] = {
                'width': original_width,
                'height': original_height
            }
            
            # Save layout for resumption
            with open(layout_file, 'w', encoding='utf-8') as f:
                json.dump(layout, f, ensure_ascii=False, indent=2)
            
            text_count = len(layout.get('text_blocks', []))
            print(f"  ✓ OCR completed for page {index+1} ({text_count} text blocks)")
            return index, layout
        except Exception as e:
            print(f"  ✗ OCR Error for page {index+1}: {e}")
            return index, None
    
    # Process Image Generation in parallel (max 3 workers)
    def process_image_gen(index, img):
        """Process AI image generation for a single page"""
        print(f"  Image generation processing page {index+1}/{total_pages}...")
        
        processed_img_file = os.path.join(processed_images_dir, f'page_{index+1}.png')
        
        # Generate clean background
        new_img = process_page_with_retry(client, img)
        if not new_img:
            print(f"  ✗ Image generation failed for page {index+1} after retries. Using original image.")
            new_img = img
        else:
            print(f"  ✓ Image generation completed for page {index+1}")
        
        # Save processed image for resumption
        new_img.save(processed_img_file, format='PNG')
        
        return index, new_img
    
    # Run OCR and Image Generation in parallel if needed
    ocr_futures = []
    image_gen_futures = []
    
    # Create separate thread pools for OCR and Image Generation
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ocr_executor, \
         concurrent.futures.ThreadPoolExecutor(max_workers=3) as image_executor:
        
        # Submit OCR tasks
        if pages_need_ocr:
            print(f"  Starting OCR processing for {len(pages_need_ocr)} pages with 3 workers...")
            ocr_futures = [ocr_executor.submit(process_ocr, i, images[i]) for i in pages_need_ocr]
        
        # Submit Image Generation tasks
        if pages_need_image_gen:
            print(f"  Starting Image Generation for {len(pages_need_image_gen)} pages with 3 workers...")
            image_gen_futures = [image_executor.submit(process_image_gen, i, images[i]) for i in pages_need_image_gen]
        
        # Collect OCR results
        for future in concurrent.futures.as_completed(ocr_futures):
            index, layout = future.result()
            if layout:
                layouts[index] = layout
        
        # Collect Image Generation results
        for future in concurrent.futures.as_completed(image_gen_futures):
            index, img = future.result()
            if img:
                processed_images[index] = img
    
    # For pages with skipped image generation, use original images
    if args.skip_image_gen:
        for i in range(total_pages):
            processed_images[i] = images[i]
            processed_img_file = os.path.join(processed_images_dir, f'page_{i+1}.png')
            images[i].save(processed_img_file, format='PNG')
    
    # Save progress
    save_progress(input_path, 2, completed=total_pages, total=total_pages)

    # Step 3: Generate Output
    if args.output_format == 'pptx':
        print("\n[Step 3/3] Creating PowerPoint presentation...")
        try:
            pages_data = [
                {'image': img, 'layout': layout}
                for img, layout in zip(processed_images, layouts)
            ]
            create_ppt_from_pages(pages_data, output_path)
            print(f"✓ PowerPoint saved to {output_path}")
        except Exception as e:
            print(f"✗ Error creating PowerPoint: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n[Step 3/3] Saving as PDF...")
        try:
            save_images_to_pdf(processed_images, output_path)
            print(f"✓ PDF saved to {output_path}")
        except Exception as e:
            print(f"✗ Error saving PDF: {e}")
    
    # Save final progress
    save_progress(input_path, 3, completed=total_pages, total=total_pages)
    print("✓ Progress saved")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)
    print(f"You can resume this process later by running the same command.")
    print(f"To clean temporary files and start fresh, use: python main.py {input_path} --clean")

if __name__ == "__main__":
    main()
