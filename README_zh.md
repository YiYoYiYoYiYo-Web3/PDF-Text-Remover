# PDF Text Remover Agent - 增强版

一个智能PDF文本去除工具，使用AI提取文本布局，生成干净的背景，并将文档重新创建为可编辑的PowerPoint演示文稿。

## 重要说明

⚠️ **OCR稳定性警告**：目前，OCR功能（文本提取和合并）不稳定。默认情况下，仅启用ImageGen（背景生成）。要使用OCR功能，请修改`.env`文件中的环境变量。

## 功能特性

### 增强型工作流程（PPTX输出）
1. **文本提取**：使用OpenCV + Tesseract OCR提取文本内容、位置和格式
2. **AI文本合并**：使用OpenAI兼容API将检测到的文本块合并为有意义的文本
3. **并行处理**：OCR和AI背景生成同时运行，提高处理速度（最多6个并发进程）
4. **干净背景生成**：在保留背景的同时移除图像中的文本
5. **布局保留**：使用坐标映射将文档重新创建为PowerPoint，文本位置准确
6. **可编辑输出**：最终PPTX中的文本可搜索、可选择、可编辑
7. **进度跟踪**：保存中间结果，以便恢复中断的进程
8. **图像损坏检测**：自动检测并重新处理损坏的图像

### 传统工作流程（PDF输出）
- 简单的图像到图像文本去除
- 输出无编辑文本的光栅化PDF

## 前置条件

- Python 3.8+
- Tesseract OCR引擎（从https://github.com/tesseract-ocr/tesseract下载）
- Tesseract中文语言包（从https://github.com/tesseract-ocr/tessdata下载）
- OpenAI兼容API（用于文本合并）
- 图像生成API（本地或云端）

## 安装

1. **安装Tesseract OCR**：
   - Windows：从https://github.com/UB-Mannheim/tesseract/wiki下载
   - macOS：`brew install tesseract`
   - Linux：`sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim`

2. **克隆仓库并导航到目录**：
```bash
cd TextRemover
```

3. **安装Python依赖**：
```bash
pip install pymupdf requests pillow python-dotenv openai python-pptx opencv-python pytesseract
```

4. **配置环境变量**：
```bash
cp .env.example .env
```

编辑`.env`文件并配置您的参数：
```env
# 用于文本合并的OpenAI兼容API
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4-vision-preview

# 图像生成API
IMAGE_API_BASE=http://localhost:8000/v1/chat/completions
IMAGE_API_KEY=han1234

# Tesseract OCR路径（仅Windows）
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## 使用方法

### 增强模式（默认 - PPTX输出）

处理PDF并输出为PowerPoint：
```bash
python main.py input.pdf
```

这将创建`input_no_text.pptx`，包含：
- 干净的背景（文本已移除）
- 原始位置的文本覆盖
- 保留的格式和布局

### 自定义输出路径

```bash
python main.py input.pdf --output presentation.pptx
```

### 传统模式（PDF输出）

用于没有文本提取的简单基于图像的输出：
```bash
python main.py input.pdf --output-format pdf
```

### 跳过OCR（更快，无文本保存）

```bash
python main.py input.pdf --skip-ocr
```

### 清理临时文件

```bash
python main.py input.pdf --clean
```
删除输入文件的所有临时文件和进度记录

## 项目结构

### 核心模块

- **`main.py`**：具有并行处理的主编排脚本
- **`ocr_client.py`**：使用OpenCV + Tesseract OCR进行文本提取，并带有AI文本合并
- **`api_client.py`**：使用I2I API生成干净的背景
- **`ppt_builder.py`**：创建带有文本覆盖和坐标映射的PowerPoint
- **`pdf_processor.py`**：PDF到图像的转换
- **`utils.py`**：用于图像处理和URL提取的辅助函数

### 测试脚本

- **`test_ocr.py`**：独立测试文本提取
- **`test_ppt.py`**：使用示例数据测试PowerPoint生成
- **`test_two_stage.py`**：测试完整的I2I工作流程

### 配置

- **`.env`**：API凭证和配置（从`.env.example`创建）
- **`.env.example`**：环境变量模板

## 工作流程详情

### 增强型工作流程步骤

```
┌─────────────────────┐
│  输入PDF文件        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 提取PNG图像         │  (PyMuPDF)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐   ┌─────────────────────┐
│ 并行处理            │   │                    │
│ ┌─────────────────┐ │   │                    │
│ │ OCR文本提取      │ │   │                    │
│ │ - OpenCV +      │ │   │                    │
│ │   Tesseract     │ │   │                    │
│ └─────────────────┘ │   │                    │
│           │         │   │                    │
│           ▼         │   │                    │
│ ┌─────────────────┐ │   │                    │
│ │ AI文本合并       │ │   │                    │
│ │ (OpenAI兼容)     │ │   │                    │
│ └─────────────────┘ │   │                    │
└──────────┬──────────┘   │                    │
           │              │                    │
           ▼              │                    │
┌─────────────────────┐   │                    │
│ 生成干净背景        │   │                    │
│ (I2I API)           │   │                    │
└──────────┬──────────┘   │                    │
           │              │                    │
           ▼              │                    │
┌─────────────────────┐   │                    │
│ 创建PowerPoint      │   │                    │
│ - 图像背景          │   │                    │
│ - 文本覆盖          │   │                    │
│ - 坐标映射          │   │                    │
└──────────┬──────────┘   │                    │
           │              │                    │
           ▼              │                    │
┌─────────────────────┐   │                    │
│  输出PPTX文件       │   │                    │
└─────────────────────┘   └─────────────────────┘
```

### 详细处理步骤

1. **提取图像**：将PDF页面转换为高分辨率PNG图像
2. **并行页面处理**：对每个页面：
   - **OCR提取**：使用Tesseract检测带有边界框的文本元素
   - **AI文本合并**：将检测到的文本块组合为有意义的文本段
   - **背景生成**：使用I2I API生成干净的背景
3. **PowerPoint创建**：创建带有以下内容的幻灯片：
   - 干净的背景图像
   - 使用坐标映射放置的合并文本
   - 保留的文本格式
4. **输出**：生成最终的可编辑PPTX文件

## 测试

### 测试OCR提取
```bash
python test_ocr.py
```
需要`stage1_with_text.jpg`（先运行`test_two_stage.py`）

### 测试PowerPoint生成
```bash
python test_ppt.py
```
使用示例数据创建`test_output.pptx`

### 测试I2I API
```bash
python test_two_stage.py
```
生成带有文本的图像，然后移除文本

## 配置详情

### 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `OPENAI_API_BASE` | OpenAI兼容API端点 | `https://api.openai.com/v1` |
| `OPENAI_API_KEY` | 视觉模型的API密钥 | 必填 |
| `OPENAI_MODEL` | 视觉模型名称 | `gpt-4-vision-preview` |
| `IMAGE_API_BASE` | I2I API端点 | `http://localhost:8000/v1/chat/completions` |
| `IMAGE_API_KEY` | I2I的API密钥 | `han1234` |

### 重试逻辑

代理会自动重试失败的API调用：
- **最大重试次数**：每页3次尝试
- **重试延迟**：尝试之间间隔2秒
- **回退方案**：如果所有重试失败，则使用原始图像

## 故障排除

### OCR客户端初始化失败

**错误**：`OPENAI_API_KEY not found in environment variables`

**解决方案**：创建带有所需凭证的`.env`文件：
```bash
cp .env.example .env
# 编辑.env文件，添加您的API密钥
```

### 未提取到文本

**可能原因**：
1. 视觉模型不支持图像分析
2. 超出API速率限制
3. 图像质量过低

**解决方案**：
- 验证模型支持视觉（例如，`gpt-4-vision-preview`）
- 检查API使用限制
- 使用更高分辨率的源PDF

### I2I API失败

**错误**：`No available tokens for image generation`

**解决方案**：检查I2I API服务器状态和令牌可用性

### 输出PPTX文本位置不正确

**原因**：
- OCR边界框不准确
- 坐标系不匹配

**解决方法**：在PowerPoint中手动调整

## 高级用法

### 处理多个PDF

```bash
for file in *.pdf; do
    python main.py "$file"
done
```

### 自定义处理脚本

```python
from pdf_processor import extract_images_from_pdf
from ocr_client import OCRClient
from api_client import APIClient
from ppt_builder import create_ppt_from_pages
from utils import image_to_base64, extract_url_from_text, download_image_from_url

# 提取图像
images = extract_images_from_pdf("input.pdf")

# 提取文本布局
ocr = OCRClient()
layouts = [ocr.extract_text_layout(img) for img in images]

# 生成干净的背景
api = APIClient()
clean_images = []
for img in images:
    img_b64 = image_to_base64(img)
    result = api.process_image(img_b64)
    url = extract_url_from_text(result)
    clean_img = download_image_from_url(url) if url else img
    clean_images.append(clean_img)

# 创建PPTX
pages_data = [
    {'image': img, 'layout': layout}
    for img, layout in zip(clean_images, layouts)
]
create_ppt_from_pages(pages_data, "output.pptx")
```

## 许可证

GNU Affero General Public License v3.0

## 贡献

欢迎贡献！请提交问题和拉取请求。