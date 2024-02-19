import torch
import whisper

class TranscribeModel:

    def __init__(self, english=True, whisper_model_size="base"):
        self.english = english
        self.whisper_model_size = whisper_model_size
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.whisper_model = whisper.load_model(self.whisper_model_size).to(self.device)

    def _is_whisper_result_valid(self, result):

        result = result.strip()

        if result == "":
            return False

        return True


    def transcribe(self, file_path):

        if self.english:
            result = self.whisper_model.transcribe(file_path, language='english')
            predicted_text = result["text"]
        else:
            result = self.whisper_model.transcribe(file_path)
            predicted_text = result["text"]

        if self._is_whisper_result_valid(predicted_text):
            return predicted_text

