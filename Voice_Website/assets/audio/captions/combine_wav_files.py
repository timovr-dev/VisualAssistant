import wave
from pydub import AudioSegment


def combine_wav_files(input_file1, input_file2):
    sound1 = AudioSegment.from_wav(input_file1)
    sound2 = AudioSegment.from_wav(input_file2)
    outfile = f"./combined_wav_files/{input_file1[2:-4]}_{input_file2[2:-4]}.wav"

    combined_sounds = sound1 + sound2
    combined_sounds.export(outfile, format="wav")

# Usage example
if __name__ == "__main__":
    caption_paths = ["./animals_caption.wav", "./vehicles_caption.wav", "./people_caption.wav"]
    caption_order_paths = ["./first_image_is_about.wav", "./second_image_is_about.wav", "./third_image_is_about.wav"]
    for caption_order_path in caption_order_paths:
        for caption_path in caption_paths:
            input_file1 = caption_order_path
            input_file2 = caption_path 
            combine_wav_files(input_file1, input_file2)