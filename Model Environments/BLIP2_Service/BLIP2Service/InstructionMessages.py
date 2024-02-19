from pydantic import BaseModel

class Instruction(BaseModel):
    current_image_filename: str