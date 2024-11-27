# Menu Processor with OpenAI Vision

A Streamlit application that processes restaurant menu images using OpenAI's GPT-4 Vision API to extract and structure menu item data.

## Features

- Supports both PDF and image (JPG/PNG) uploads
- Converts PDF pages to images for processing
- Extracts menu items with detailed attributes:
  - Item name
  - Prices (including multiple price options)
  - Price labels (e.g., Half/Full portions)
  - Item descriptions
  - Dietary labels (veg/non-veg/spicy)
- Provides editable data table interface
- Exports processed data in JSON and CSV formats
- Handles temporary file management with session-based cleanup

## Technical Stack

- **Frontend**: Streamlit
- **Image Processing**: pdf2image, Pillow
- **AI Integration**: OpenAI GPT-4 Vision API
- **Data Processing**: Pandas
- **Deployment**: Streamlit Cloud

## Usage

1. Enter OpenAI API key in the sidebar
2. Upload menu PDF/images
3. Select specific images to process
4. Review and edit extracted data
5. Download in preferred format (JSON/CSV)

## Live Demo

Access the deployed application at: https://menu-generator-zilliondines.streamlit.app/

## Requirements

- OpenAI API key with GPT-4 Vision access
- Python packages: streamlit, openai, pdf2image, Pillow, pandas
