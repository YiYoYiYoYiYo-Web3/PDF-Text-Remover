import fitz  # PyMuPDF
from PIL import Image
import io
import os

def extract_images_from_pdf(pdf_path):
    """
    Convert each page of a PDF to a PIL Image.
    """
    doc = fitz.open(pdf_path)
    images = []
    
    print(f"Extracting images from {pdf_path} (Total pages: {len(doc)})...")
    
    for i, page in enumerate(doc):
        # Render page to an image (pixmap)
        # zoom=2 for better resolution (approx 144 dpi)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) 
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        images.append(img)
        print(f"Processed page {i+1}/{len(doc)}")
        
    return images

def save_images_to_pdf(images, output_path):
    """
    Save a list of PIL Images to a PDF file.
    """
    if not images:
        print("No images to save.")
        return

    print(f"Saving {len(images)} images to {output_path}...")
    
    # Convert all images to RGB (just in case)
    rgb_images = []
    for img in images:
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        else:
            rgb_images.append(img)
            
    if rgb_images:
        rgb_images[0].save(
            output_path, "PDF", resolution=100.0, save_all=True, append_images=rgb_images[1:]
        )
        print("PDF saved successfully.")
    else:
        # If for some reason conversion failed or list is empty
        images[0].convert('RGB').save(
            output_path, "PDF", resolution=100.0, save_all=True, append_images=[i.convert('RGB') for i in images[1:]]
        )
