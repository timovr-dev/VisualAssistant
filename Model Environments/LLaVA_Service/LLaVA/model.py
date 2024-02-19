
# FastAPI libraries 
from fastapi import FastAPI, UploadFile, File
import shutil
import uvicorn
from InstructionMessages import Instruction # local file so far

#LLaVA libraries
import sys
sys.path.append("/LLaVA/LLaVA_repository")

import torch
from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN, DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN
from llava.conversation import conv_templates, SeparatorStyle
from llava.model.builder import load_pretrained_model
from llava.utils import disable_torch_init
from llava.mm_utils import tokenizer_image_token, get_model_name_from_path, KeywordsStoppingCriteria

from PIL import Image

import requests
import os
from PIL import Image
from io import BytesIO



class LLaVAAssistant:

    def __init__(self):
        self.api = FastAPI(title="BVI Visual Assistant Generator API")
        # Setting arguments
        self.args = {
            "model_path": "liuhaotian/llava-v1.5-7b", # 7b or 13b
            "model_base": None,
            "load_8bit": False,
            "load_4bit": True,
            "conv_mode": None,
            "debug": False
        }
        self.image_base_folder = os.path.join("/LLaVA", "images")
        self.image_id_to_path = {
            "0": "/LLaVA/images/animals.jpg",
            "1": "/LLaVA/images/people.jpg",
            "2": "/LLaVA/images/vehicles.jpg",
        }

        # loading the LLaVA model
        disable_torch_init()
        model_name = get_model_name_from_path(self.args['model_path'])
        print(f"Loading model {model_name}...")
        self.tokenizer, self.model, self.image_processor, context_len = load_pretrained_model(self.args['model_path'], self.args['model_base'], model_name, self.args['load_8bit'], self.args['load_4bit'])

        if 'llama-2' in model_name.lower():
            conv_mode = "llava_llama_2"
        elif "v1" in model_name.lower():
            conv_mode = "llava_v1"
        elif "mpt" in model_name.lower():
            conv_mode = "mpt"
        else:
            conv_mode = "llava_v0"

        if self.args['conv_mode'] is not None and conv_mode != self.args['conv_mode']:
            print('[WARNING] the auto inferred conversation mode is {}, while `--conv-mode` is {}, using {}'.format(conv_mode, self.args['conv_mode'], self.args['conv_mode']))
        else:
            self.args['conv_mode'] = conv_mode

        self.conv = conv_templates[self.args['conv_mode']].copy()
    
    def _load_image(self, image_file):
        if image_file.startswith('http') or image_file.startswith('https'):
            response = requests.get(image_file)
            image = Image.open(BytesIO(response.content)).convert('RGB')
        else:
            image = Image.open(image_file).convert('RGB')
        return image

    def _change_image(self, image_file):
        image = self._load_image(image_file)
        image_tensor = self.image_processor.preprocess(image, return_tensors='pt')['pixel_values'].half().cuda()
        conv = conv_templates[self.args['conv_mode']].copy()
        return conv, image, image_tensor
    
    def _transform_to_llava_format(self, conversation_history:str):
        # Split the input string using "|||" as the separator
        temp_conversation_history = list()
        conversation_history_parts = conversation_history.split("|||")
        if conversation_history_parts in [[], ['']]:
            return []
        # Remove any empty conversation_history_parts resulting from leading/trailing "|||" or consecutive "|||"
        conversation_history_parts = [part.strip() for part in conversation_history_parts if part.strip()]
        # Create a list of tuples
        for idx, part in enumerate(conversation_history_parts):
            if idx % 2 == 0: # USER message
                if idx == 0: # first USER message
                    llava_part = ["USER", f"<image>\n{part}"]
                else:
                    llava_part = ["USER", f"{part}"]
            else: # ASSISTANT message
                llava_part = ["ASSISTANT", f"{part}</s>"]
            temp_conversation_history.append(llava_part)
        return temp_conversation_history


    def setup_routes(self):
        @self.api.post("/")
        async def predict(data:Instruction):
            print("data: ", data)
            #data = data.dict()
            conversation_history = data.conversation_history
            current_instruction = data.current_instruction
            current_image_filename = data.current_image_filename
            # prepare the data for the LLaVA model

            # maybe also check if the image id is even possible
            # check if image id is string between 0 and 2

            image_path = os.path.join(self.image_base_folder, current_image_filename)
            print(f"image_path: {image_path}")
            self.conv, self.image, self.image_tensor = self._change_image(image_path)


            # TODO: check on google colab in detail how the conversation_history string is constructed and do it the same way
            llava_conversation_history = self._transform_to_llava_format(conversation_history)
            if llava_conversation_history == []: # no history and therefore first instruction
                llava_current_instruction = ["USER", f"<image>\n{current_instruction.strip()}"]
            else:
                llava_current_instruction  = ["USER", f"{current_instruction.strip()}"]# if whisper can't understand the instruction than you have None type has no strip function error crash

            llava_conversation_history.append(llava_current_instruction)
            llava_conversation_history.append(["ASSISTANT", None])
            self.conv.messages = llava_conversation_history

            # input data into LLaVA
            prompt = self.conv.get_prompt()

            input_ids = tokenizer_image_token(prompt, self.tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(0).cuda()
            stop_str = self.conv.sep if self.conv.sep_style != SeparatorStyle.TWO else self.conv.sep2
            keywords = [stop_str]
            stopping_criteria = KeywordsStoppingCriteria(keywords, self.tokenizer, input_ids)

            with torch.inference_mode():
                output_ids = self.model.generate(
                    input_ids,
                    images=self.image_tensor,
                    do_sample=True,
                    temperature=0.2,
                    max_new_tokens=2024,
                    use_cache=True,
                    stopping_criteria=[stopping_criteria])

            output = self.tokenizer.decode(output_ids[0, input_ids.shape[1]:]).strip()
            output = output.replace("\n", "").replace("</s>", "")
            print(f"ASSISTANT: {output}")

            if self.args['debug']:
                print("\n", {"prompt": prompt, "outputs": output}, "\n")

            return {"answer": output}

        
        @self.api.post("/uploadimage/")
        async def upload_image(image: UploadFile = File(...)):
            with open(f'images/{image.filename}', 'wb') as buffer:
                shutil.copyfileobj(image.file, buffer)
                # add path to image_id_to_path
                self.image_id_to_path[image.filename] = f"/LLaVA/images/{image.filename}"
                print(f"image_id_to_path: {self.image_id_to_path}")
            
            return {"filename": image.filename}

def main():
    visual_assistant = LLaVAAssistant()
    visual_assistant.setup_routes()
    uvicorn.run(visual_assistant.api, host="0.0.0.0", port=80)


if __name__ == "__main__":
    main()