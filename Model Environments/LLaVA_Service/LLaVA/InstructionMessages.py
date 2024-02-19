from pydantic import BaseModel

class Instruction(BaseModel):
    conversation_history: str
    current_instruction: str
    current_image_filename: str