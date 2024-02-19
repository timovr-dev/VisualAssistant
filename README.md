# Visual Assistant

<img width="1131" alt="Capture" src="https://github.com/timovr-dev/VisualAssistant/assets/67631060/7999c715-38ff-4143-b6c5-633d1f492e87">

## Workflow

1. **User Input:**
   - The user provides input through speech.
   - The Speech-to-Text Service converts the spoken words into textual format.

2. **Question Processing:**
   - The Textual Question and Image are processed by a Multimodal Large Language Model.
   - An Image Captioning Model generates a caption for the image.

3. **Answer Generation:**
   - The Multimodal Large Language Model generates an Image Answer based on the Textual Question and Image.
   - A caption is also provided for the image.

4. **Output:**
    - The Text-to-Speech Service converts the Image Answer into audible speech for the user to hear.

## Components

### Speech-to-Text Service
Converts spoken language into written text.

### Multimodal Large Language Model
Processes both textual questions and images to generate appropriate responses.

### Image Captioning Model
Generates descriptive captions for images.

### Text-to-Speech Service
Converts written text answers into audible speech.

# Software Architecture
<img width="1223" alt="Capture" src="https://github.com/timovr-dev/VisualAssistant/assets/67631060/2181c280-7004-40f5-9dc7-0df03a01b056">
