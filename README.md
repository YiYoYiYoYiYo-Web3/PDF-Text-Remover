# PDF Text Remover Agent - Enhanced

An intelligent PDF text remover that extracts text layout, generates clean backgrounds using AI, and recreates the document as an editable PowerPoint presentation.

**[中文版本 README](README_zh.md)**

## Important Note

⚠️ **OCR Stability Warning**: Currently, the OCR functionality (text extraction and merging) is unstable. By default, only ImageGen (background generation) is enabled. To use OCR features, please modify the environment variables in the `.env` file.

## Features

### Enhanced Workflow (PPTX Output)
1. **Text Extraction**: Uses OpenCV + Tesseract OCR to extract text content, positions, and formatting
2. **AI Text Merging**: Combines detected text blocks into meaningful text using OpenAI-compatible API
3. **Parallel Processing**: OCR and AI background generation run simultaneously for faster processing (max 6 concurrent processes)
4. **Clean Background Generation**: Removes text from images while preserving backgrounds
5. **Layout Preservation**: Recreates document as PowerPoint with accurate text positioning using coordinate mapping
6. **Editable Output**: Text is searchable, selectable, and editable in the final PPTX
7. **Progress Tracking**: Saves intermediate results to resume interrupted processes
8. **Image Corruption Detection**: Automatically detects and reprocesses corrupt images

### Legacy Workflow (PDF Output)
- Simple image-to-image text removal
- Outputs rasterized PDF with no editable text

## Prerequisites

- Python 3.8+
- Tesseract OCR Engine (download from https://github.com/tesseract-ocr/tesseract)
- Chinese language pack for Tesseract (download from https://github.com/tesseract-ocr/tessdata)
- OpenAI-compatible API (for text merging)
- Image generation API (local or cloud)

## Installation

1. **Install Tesseract OCR**:
   - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - macOS: `brew install tesseract`
   - Linux: `sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim`

2. **Clone the repository and navigate to the directory**:
```bash
cd TextRemover
```

3. **Install Python dependencies**:
```bash
pip install pymupdf requests pillow python-dotenv openai python-pptx opencv-python pytesseract
```

4. **Configure environment variables**:
```bash
cp .env.example .env
```

Edit `.env` file with your configuration:
```env
# OpenAI-compatible API for text merging
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4-vision-preview

# Image generation API
IMAGE_API_BASE=http://localhost:8000/v1/chat/completions
IMAGE_API_KEY=han1234

# Tesseract OCR Path (Windows only)
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Usage

### Enhanced Mode (Default - PPTX Output)

Process a PDF and output as PowerPoint:
```bash
python main.py input.pdf
```

This will create `input_no_text.pptx` with:
- Clean backgrounds (text removed)
- Text overlays at original positions
- Preserved formatting and layout

### Custom Output Path

```bash
python main.py input.pdf --output presentation.pptx
```

### Legacy Mode (PDF Output)

For simple image-based output without text extraction:
```bash
python main.py input.pdf --output-format pdf
```

### Skip OCR (Faster, No Text Preservation)

```bash
python main.py input.pdf --skip-ocr
```

### Clean Temporary Files

```bash
python main.py input.pdf --clean
```
Removes all temporary files and progress for the input file

## Project Structure

### Core Modules

- **`main.py`**: Main orchestration script with parallel processing
- **`ocr_client.py`**: Text extraction using OpenCV + Tesseract OCR, with AI text merging
- **`api_client.py`**: Clean background generation using I2I API
- **`ppt_builder.py`**: PowerPoint creation with text overlays and coordinate mapping
- **`pdf_processor.py`**: PDF to image conversion
- **`utils.py`**: Helper functions for image processing and URL extraction

### Test Scripts

- **`test_ocr.py`**: Test text extraction independently
- **`test_ppt.py`**: Test PowerPoint generation with sample data
- **`test_two_stage.py`**: Test full I2I workflow

### Configuration

- **`.env`**: API credentials and configuration (create from `.env.example`)
- **`.env.example`**: Template for environment variables

## Workflow Details

### Enhanced Workflow Steps

```
┌─────────────────────┐
│  Input PDF File     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Extract PNG Images  │  (PyMuPDF)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐   ┌─────────────────────┐
│ Parallel Processing │   │                    │
│ ┌─────────────────┐ │   │                    │
│ │ OCR Text        │ │   │                    │
│ │ Extraction      │ │   │                    │
│ │ - OpenCV +      │ │   │                    │
│ │   Tesseract     │ │   │                    │
│ └─────────────────┘ │   │                    │
│           │         │   │                    │
│           ▼         │   │                    │
│ ┌─────────────────┐ │   │                    │
│ │ AI Text         │ │   │                    │
│ │ Merging         │ │   │                    │
│ │ (OpenAI-compat) │ │   │                    │
│ └─────────────────┘ │   │                    │
└──────────┬──────────┘   │                    │
           │              │                    │
           ▼              │                    │
┌─────────────────────┐   │                    │
│ Generate Clean BG   │   │                    │
│ (I2I API)           │   │                    │
└──────────┬──────────┘   │                    │
           │              │                    │
           ▼              │                    │
┌─────────────────────┐   │                    │
│ Create PowerPoint   │   │                    │
│ - Image backgrounds │   │                    │
│ - Text overlays     │   │                    │
│ - Coordinate        │   │                    │
│   mapping           │   │                    │
└──────────┬──────────┘   │                    │
           │              │                    │
           ▼              │                    │
┌─────────────────────┐   │                    │
│  Output PPTX File   │   │                    │
└─────────────────────┘   └─────────────────────┘
```

### Processing Steps in Detail

1. **Extract Images**: Convert PDF pages to high-resolution PNG images
2. **Parallel Page Processing**: For each page:
   - **OCR Extraction**: Use Tesseract to detect text elements with bounding boxes
   - **AI Text Merging**: Combine detected text blocks into meaningful text segments
   - **Background Generation**: Generate clean background using I2I API
3. **PowerPoint Creation**: Create slides with:
   - Clean background images
   - Merged text placed using coordinate mapping
   - Preserved text formatting
4. **Output**: Generate final editable PPTX file

## Testing

### Test OCR Extraction
```bash
python test_ocr.py
```
Requires `stage1_with_text.jpg` (run `test_two_stage.py` first)

### Test PowerPoint Generation
```bash
python test_ppt.py
```
Creates `test_output.pptx` with sample data

### Test I2I API
```bash
python test_two_stage.py
```
Generates image with text, then removes text

## Configuration Details

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_BASE` | OpenAI-compatible API endpoint | `https://api.openai.com/v1` |
| `OPENAI_API_KEY` | API key for vision model | Required |
| `OPENAI_MODEL` | Vision model name | `gpt-4-vision-preview` |
| `IMAGE_API_BASE` | I2I API endpoint | `http://localhost:8000/v1/chat/completions` |
| `IMAGE_API_KEY` | API key for I2I | `han1234` |

### Retry Logic

The agent automatically retries failed API calls:
- **Max retries**: 3 attempts per page
- **Retry delay**: 2 seconds between attempts
- **Fallback**: Uses original image if all retries fail

## Troubleshooting

### OCR Client Initialization Fails

**Error**: `OPENAI_API_KEY not found in environment variables`

**Solution**: Create `.env` file with required credentials:
```bash
cp .env.example .env
# Edit .env with your API keys
```

### No Text Extracted

**Possible causes**:
1. Vision model doesn't support image analysis
2. API rate limits exceeded
3. Image quality too low

**Solutions**:
- Verify model supports vision (e.g., `gpt-4-vision-preview`)
- Check API usage limits
- Use higher resolution source PDFs

### I2I API Fails

**Error**: `No available tokens for image generation`

**Solution**: Check I2I API server status and token availability

### Output PPTX Text Positioning Incorrect

**Causes**:
- OCR bounding box inaccuracies
- Coordinate system mismatches

**Workaround**: Manual adjustment in PowerPoint

## Advanced Usage

### Process Multiple PDFs

```bash
for file in *.pdf; do
    python main.py "$file"
done
```

### Custom Processing Script

```python
from pdf_processor import extract_images_from_pdf
from ocr_client import OCRClient
from api_client import APIClient
from ppt_builder import create_ppt_from_pages
from utils import image_to_base64, extract_url_from_text, download_image_from_url

# Extract images
images = extract_images_from_pdf("input.pdf")

# Extract text layouts
ocr = OCRClient()
layouts = [ocr.extract_text_layout(img) for img in images]

# Generate clean backgrounds
api = APIClient()
clean_images = []
for img in images:
    img_b64 = image_to_base64(img)
    result = api.process_image(img_b64)
    url = extract_url_from_text(result)
    clean_img = download_image_from_url(url) if url else img
    clean_images.append(clean_img)

# Create PPTX
pages_data = [
    {'image': img, 'layout': layout}
    for img, layout in zip(clean_images, layouts)
]
create_ppt_from_pages(pages_data, "output.pptx")
```

## License

GNU Affero General Public License v3.0

## Contributing

Contributions welcome! Please submit issues and pull requests.
