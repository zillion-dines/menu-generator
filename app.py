import streamlit as st
from pdf2image import convert_from_bytes
from PIL import Image
from openai import OpenAI
import pandas as pd
import io
import os
import json
import base64
import shutil
import uuid
import tempfile

def get_session_temp_folder():
    """Create a unique temporary folder for each user session"""
    if 'temp_folder' not in st.session_state:
        # Create a unique folder name using UUID
        unique_folder = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
        st.session_state.temp_folder = unique_folder
        if not os.path.exists(unique_folder):
            os.makedirs(unique_folder)
    return st.session_state.temp_folder

def cleanup_temp_folder():
    """Clean up the temporary folder for the current session"""
    if 'temp_folder' in st.session_state:
        folder_path = st.session_state.temp_folder
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        del st.session_state.temp_folder

def save_images(images, folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    saved_image_paths = []
    for i, image in enumerate(images):
        image_path = os.path.join(folder, f"image_{i+1}.jpg")
        image.save(image_path, "JPEG")
        saved_image_paths.append(image_path)
    return saved_image_paths

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def process_image_with_openai(image_path, client):
    base64_image = encode_image_to_base64(image_path)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a menu analysis expert. Extract menu items from the image and format them into structured JSON data. 
                    For each menu item, provide:
                    - name: The name of the dish
                    - prices: Array of prices (if multiple options exist)
                    - priceLabels: Array of labels corresponding to prices (e.g., "Half", "Full")
                    - description: Brief description of the dish if available, otherwise provide a simple description
                    - labels: Array of relevant labels (e.g., "veg", "non-veg", "spicy", etc.)
                    
                    Return ONLY a JSON array of menu items without any additional text."""
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract menu items from this image and format them according to the specified JSON structure. Ensure prices are numbers, not strings."},
                        {
                            "type": "image_url",
                            "image_url": {
                                'url': f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4096
        )
        
        try:
            content = response.choices[0].message.content
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return []
        except json.JSONDecodeError:
            st.error("Failed to parse JSON response from OpenAI")
            return []
            
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return []

def json_to_dataframe(menu_items):
    flattened_items = []
    for item in menu_items:
        flat_item = {
            'Name': item['name'],
            'Description': item['description'],
            'Labels': ', '.join(item['labels']),
        }
        for i, (price, label) in enumerate(zip(item['prices'], item['priceLabels'])):
            flat_item[f'Price ({label})'] = price
        flattened_items.append(flat_item)
    return pd.DataFrame(flattened_items)

# Initialize session state for storing the API key
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''

# Streamlit App
st.title("Menu Processor with OpenAI Vision")

# API Key input in sidebar
with st.sidebar:
    api_key = st.text_input("Enter your OpenAI API Key:", type="password", value=st.session_state.api_key)
    if api_key:
        st.session_state.api_key = api_key

# Check if API key is provided
if not st.session_state.api_key:
    st.warning("Please enter your OpenAI API key in the sidebar to continue.")
    st.stop()

# Initialize OpenAI client with the provided API key
client = OpenAI(api_key=st.session_state.api_key)

# Get session-specific temp folder
temp_folder = get_session_temp_folder()

# File Upload
uploaded_file = st.file_uploader("Upload a PDF or JPEG/PNG images", type=["pdf", "jpg", "jpeg", "png"])

# Clear temp folder when new file is uploaded
if uploaded_file and 'last_uploaded_file' in st.session_state:
    if st.session_state.last_uploaded_file != uploaded_file.name:
        cleanup_temp_folder()
        temp_folder = get_session_temp_folder()

if uploaded_file:
    st.session_state.last_uploaded_file = uploaded_file.name
    images = []
    if uploaded_file.type == "application/pdf":
        with st.spinner("Converting PDF to images..."):
            images = convert_from_bytes(uploaded_file.read())
    else:
        with st.spinner("Loading image..."):
            images = [Image.open(uploaded_file)]

    image_paths = save_images(images, temp_folder)
    st.success("Images extracted successfully!")
    st.write(f"Extracted {len(image_paths)} image(s).")

    # Image Selection
    selected_images = st.multiselect(
        "Select images to process:",
        options=image_paths,
        format_func=lambda x: os.path.basename(x),
    )

    if selected_images:
        cols = st.columns(min(len(selected_images), 3))
        for idx, img_path in enumerate(selected_images):
            col = cols[idx % 3]
            with col:
                st.image(img_path, caption=f"Image {idx + 1}", use_container_width=True)
        
        if st.button("Start Processing"):
            all_menu_items = []
            
            for img_path in selected_images:
                with st.spinner(f"Processing {os.path.basename(img_path)}..."):
                    menu_items = process_image_with_openai(img_path, client)
                    all_menu_items.extend(menu_items)
            
            if all_menu_items:
                with st.expander("View Raw JSON"):
                    st.json(all_menu_items)
                
                menu_df = json_to_dataframe(all_menu_items)
                st.write("### Edit Menu Data")
                edited_df = st.data_editor(menu_df)
                
                st.write("### Download Options")
                
                json_str = json.dumps(all_menu_items, indent=2)
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name="menu_items.json",
                    mime="application/json"
                )
                
                csv_buffer = io.StringIO()
                edited_df.to_csv(csv_buffer, index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv_buffer.getvalue(),
                    file_name="menu_items.csv",
                    mime="text/csv"
                )

# Register cleanup function to run on session end
st.session_state['cleanup_temp_folder'] = cleanup_temp_folder