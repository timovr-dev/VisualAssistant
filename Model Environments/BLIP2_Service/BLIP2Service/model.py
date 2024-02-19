import sys
sys.path.append("/BLIP2Service/")

# FastAPI libraries 
from fastapi import FastAPI, UploadFile, File
import shutil
import uvicorn
from InstructionMessages import Instruction # local file so far

#BLIP2 libraries
import os
import torch
from PIL import Image
from lavis.models import load_model_and_preprocess

class BLIP2Assistant:

    def __init__(self):
        self.api = FastAPI(title="BVI Visual Assistant Generator API")

        # BLIP2 setup
        self.image_base_folder = os.path.join("/BLIP2Service", "images")
        self.device = torch.device("cuda") if torch.cuda.is_available() else "cpu"
        self.model, self.vis_processors, _ = load_model_and_preprocess(name="blip_caption", model_type="base_coco", is_eval=True, device=self.device)


    def _load_image(self, image_path):
        raw_image = Image.open(image_path).convert('RGB')   
        image = self.vis_processors["eval"](raw_image).unsqueeze(0).to(self.device)
        return image


    def setup_routes(self):
        @self.api.post("/")
        async def predict(data:Instruction):
            print("data: ", data)
            current_image_filename = data.current_image_filename


            image_path = os.path.join(self.image_base_folder, current_image_filename)
            image = self._load_image(image_path)

            output = self.model.generate({"image": image})[0]
            print(f"output: {output}")
            return {"answer": output}

        
        @self.api.post("/uploadimage/")
        async def upload_image(image: UploadFile = File(...)):
            destination_path = os.path.join(self.image_base_folder, image.filename)
            with open(destination_path, 'wb') as buffer:
                shutil.copyfileobj(image.file, buffer)
            
            return {"filename": image.filename}

def main():
    visual_assistant = BLIP2Assistant()
    visual_assistant.setup_routes()
    uvicorn.run(visual_assistant.api, host="0.0.0.0", port=80)


if __name__ == "__main__":
    main()