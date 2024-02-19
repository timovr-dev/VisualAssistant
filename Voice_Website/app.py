from flask import Flask, render_template, request, redirect, session
from flask import send_file

from datetime import datetime
from threading import Thread
from pprint import pprint
import os
import requests
import azure.cognitiveservices.speech as speechsdk
from werkzeug.utils import secure_filename
from transcribe import TranscribeModel

import random


transcribeModel = TranscribeModel(english=True, whisper_model_size="base")

app = Flask(__name__)
app.config['CONVERSATIONS_FOLDER'] = os.path.join('.', 'conversations')
app.config['AUDIO_FOLDER'] = os.path.join('.', 'assets', 'audio')
app.secret_key = b'secretkey'


session_counter = 1
feedback_limit = 10


custom_image_id = 3

# initialize the heighest participant number by looking at the currently existing conversations to not overwrite already existing conversations
highest_participant_number = 0
for folder_name in os.listdir(app.config['CONVERSATIONS_FOLDER']):
    if folder_name.startswith("participant_"):
        try:
            participant_number = int(folder_name.split("_")[-1])
            highest_participant_number = max(highest_participant_number, participant_number)
        except ValueError:
            continue 


LLAVA_SERVER_IP = "127.0.0.1"
LLAVA_SERVER_PORT = 5002

LLAVA_SERVER_URL = f"http://{LLAVA_SERVER_IP}:{LLAVA_SERVER_PORT}"
LLAVA_IMAGE_UPLOAD_URL = f"{LLAVA_SERVER_URL}/uploadimage/"


BLIP2_SERVER_IP = "127.0.0.1"
BLIP2_SERVER_PORT = 5003

BLIP2_SERVER_URL = f"http://{BLIP2_SERVER_IP}:{BLIP2_SERVER_PORT}"
BLIP2_IMAGE_UPLOAD_URL = f"{BLIP2_SERVER_URL}/uploadimage/"


caption_wav_files = [
    ["first_image_is_about_animals_caption.wav", "second_image_is_about_animals_caption.wav", "third_image_is_about_animals_caption.wav"], # first picture
    ["first_image_is_about_people_caption.wav", "second_image_is_about_people_caption.wav", "third_image_is_about_people_caption.wav"], # second picture
    ["first_image_is_about_vehicles_caption.wav", "second_image_is_about_vehicles_caption.wav", "third_image_is_about_vehicles_caption.wav"], # third picture
]

# # text to speech variables
speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'),
                                    region=os.environ.get('SPEECH_REGION'))
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
ssml_narrator_template = """<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
    <voice name="en-US-DavisNeural" style="general">
        <<TEXT>>
    </voice>
</speak>"""

@app.route('/upload', methods=['POST'])
def upload(): # handles instructions

    if 'file' not in request.files:
        return 'No file part'
    user_audio_file = request.files['file']
    if user_audio_file.filename == '':
        return 'No selected file'
    if user_audio_file:
        print(f"current_image_filename: {session['current_image_filename']}")
        instruction_time = str(datetime.now().strftime("%H-%M-%S"))
        instruction_filename = instruction_time + "_instruction" + ".wav"
        instruction_path = os.path.join(session['session_folder_path'], instruction_filename)
        user_audio_file.save(instruction_path)
        instruction = transcribeModel.transcribe(instruction_path)


        # if new user then initialize a new chat history and create a new folder for the wav files
        conversation_history = session['conversation_history']
        current_image_filename = session['current_image_filename']
        model_data = {'current_instruction' : instruction, 'conversation_history': conversation_history, 'current_image_filename': current_image_filename}
        pprint(model_data)
        response = requests.post(LLAVA_SERVER_URL, json=model_data)

        if response.status_code == 200:
            response_json = response.json()
            if not session['conversation_history']:
                session['conversation_history'] += f"{instruction}|||{response_json['answer']}"
            else:
                session['conversation_history'] += f"|||{instruction}|||{response_json['answer']}"

            print(f"Asisstant Answer: {response_json['answer']}")
            ssml_narrator = ssml_narrator_template.replace("<<TEXT>>", response_json['answer'])

            print("before azure api call")
            speech_synthesis_result = speech_synthesizer.speak_ssml(ssml_narrator)
            speech_synthesis_result_audio = speech_synthesis_result.audio_data
            print("after azure api call")

            response_time = str(datetime.now().strftime("%H-%M-%S"))
            response_filename = response_time + "_response" + ".wav"
            response_path = os.path.join(session['session_folder_path'], response_filename)

            transcript_file_path = os.path.join(session['session_folder_path'], "transcript.txt")
            with open(transcript_file_path, 'a') as file:
                file.write(f"[{instruction_time}]>> Blind User: {instruction} \n[{response_time}]>> Visual Assistant: {response_json['answer']} \n\n")

            #output_file_path = f"{app.config['RESPONSES_FOLDER']}/{response_filename}"
            with open(response_path, mode='bw') as f:
                f.write(speech_synthesis_result_audio)
            return send_file(
                response_path, 
                mimetype="audio/wav", 
                as_attachment=True, 
                download_name="test.wav")
        else:
            print(f"POST request failed with status code {response.status_code}")

@app.route('/feedback', methods=['POST'])
def feedback():
    if 'file' not in request.files:
        return 'No file part'
    user_audio_file = request.files['file']
    if user_audio_file.filename == '':
        return 'No selected file'
    if user_audio_file:
        pass
        #filename = secure_filename(user_audio_file.filename)

        feedback_filename = str(datetime.now().strftime("%H-%M-%S")) + "_feedback" + ".wav"
        feedback_path = os.path.join(session['session_folder_path'], feedback_filename)
        user_audio_file.save(feedback_path)
        feedback_received_notification_path = os.path.join(app.config['AUDIO_FOLDER'], "feedback_received.wav")

        feedback = transcribeModel.transcribe(feedback_path)
        transcript_file_path = os.path.join(session['session_folder_path'], "transcript.txt")
        with open(transcript_file_path, 'a') as file:
            file.write(f"FEEDBACK >> {feedback}\n\n")

        return send_file(
            feedback_received_notification_path, 
            mimetype="audio/wav", 
            as_attachment=True, 
            download_name="test.wav")


@app.route('/start-study', methods=['POST'])
def start_study():
    global highest_participant_number
        # intializations
    if 'conversation_history' not in session:  
        print("New Session Initialized")
        session['conversation_history'] = ""
        highest_participant_number += 1
        session['participant_id'] = highest_participant_number
        session['custom_image_id'] = 0
        session['round'] = 1

        # select randomly the order of images that the BVI will interact with
        image_filenames = ["0.jpg", "1.jpg", "2.jpg"]
        random.shuffle(image_filenames)
        first_image_filename = image_filenames.pop(0)
        image_filenames = [str(x) for x in image_filenames]
        str_image_filenames = '-'.join(image_filenames)
        session['image_filenames'] = str_image_filenames
        session['current_image_filename'] = first_image_filename

        # createa folder for this session 
        session_folder_path = f"{app.config['CONVERSATIONS_FOLDER']}/participant_{session['participant_id']}"
        session['session_folder_path'] = session_folder_path
        os.mkdir(session_folder_path)

        # create folder for custom images
        os.mkdir(os.path.join(session_folder_path, "custom_images"))

        # create a transcript file
        transcript_file_path = os.path.join(session_folder_path, "transcript.txt")
        with open(transcript_file_path, 'w') as file:
            file.write(f"NEXT IMAGE >> {first_image_filename} <<\n\n")

        # send audio notifcation that the study has started
        study_started_notification_path = os.path.join(app.config['AUDIO_FOLDER'], "study_started.wav")
        
        pprint(caption_wav_files)


        first_image_id = int(first_image_filename.split(".")[0])
        first_audio_start_file = caption_wav_files[first_image_id][0]
        first_audio_start_path = os.path.join(app.config['AUDIO_FOLDER'], "captions", "combined_wav_files", first_audio_start_file)

        return send_file(
            first_audio_start_path, 
            mimetype="audio/wav", 
            as_attachment=True, 
            download_name="test.wav")


@app.route('/next-image', methods=['POST'])
def next_image():
    current_session_round = session['round'] + 1

    if current_session_round > 4:
        print("START CUSTOM IMAGE UPLOAD")
        end_static_study_audio = os.path.join(app.config['AUDIO_FOLDER'] , "start_custom_image_upload_short.wav")
        response = send_file(
            end_static_study_audio, 
            mimetype="audio/wav", 
            as_attachment=True, 
            download_name="custom_image_upload_start.wav")
        response.headers["Content-Disposition"] = "attachment; filename=start_custom_image_upload.wav"
        session['round'] = current_session_round
        return response

    # end of the static image tests, the BVI will now upload custom images
    if current_session_round == 4:
        print("START CUSTOM IMAGE UPLOAD")
        end_static_study_audio = os.path.join(app.config['AUDIO_FOLDER'] , "start_custom_image_upload.wav")
        response = send_file(
            end_static_study_audio, 
            mimetype="audio/wav", 
            as_attachment=True, 
            download_name="custom_image_upload_start.wav")
        response.headers["Content-Disposition"] = "attachment; filename=start_custom_image_upload.wav"
        session['round'] = current_session_round
        return response



    session['conversation_history'] = ""
    remaining_image_filenames = session['image_filenames'].split("-")[1:] 
    next_image_filename = session['image_filenames'].split("-")[0]
    session['image_filenames'] = '-'.join(remaining_image_filenames)
    session['current_image_filename'] = next_image_filename



    transcript_file_path = os.path.join(session['session_folder_path'], "transcript.txt")
    with open(transcript_file_path, 'a') as file:
        file.write(f"NEXT IMAGE >> {next_image_filename} <<\n\n")

    #new_caption_path = os.path.join(app.config['AUDIO_FOLDER'], f"{new_image_id}.wav")

    next_image_id = int(next_image_filename.split(".")[0])
    new_caption_path = os.path.join(app.config['AUDIO_FOLDER'], caption_wav_files[next_image_id][0])
    study_started_notification_path = os.path.join(app.config['AUDIO_FOLDER'], "study_started.wav")
    
    next_audio_caption_file = caption_wav_files[next_image_id][current_session_round - 1]

    next_audio_caption_path = os.path.join(app.config['AUDIO_FOLDER'], "captions", "combined_wav_files", next_audio_caption_file)
    session['round'] = current_session_round

    response = send_file(
        next_audio_caption_path, 
        mimetype="audio/wav", 
        as_attachment=True, 
        download_name="caption.wav")
    response.headers["Content-Disposition"] = "attachment; filename=caption.wav"

    return response


def _upload_image(image_file_path, image_upload_url):
    with open(image_file_path, 'rb') as f:
        r = requests.post(image_upload_url, files={'image': f})
        return r.status_code == 200

# upload image 
@app.route('/upload-image', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        return {'status': 'No image file part in the request.'}, 400
    file = request.files['image']
    if file.filename == '':
        return {'status': 'No selected file.'}, 400
    if file:
        filename = secure_filename(file.filename)
        # change filename to become and index
        
        session['custom_image_id'] += 1
        unique_filename = f"{session['participant_id']}-{session['custom_image_id']}"
        new_filename = f"{unique_filename}{os.path.splitext(filename)[1]}"
        session['current_image_filename'] = new_filename

        image_file_path = os.path.join(session['session_folder_path'], "custom_images", new_filename)
        file.save(image_file_path)

        if not _upload_image(image_file_path, LLAVA_IMAGE_UPLOAD_URL):
            return {'status': 'Connection to LLaVA Upload Server Error'}, 400
        
        if not _upload_image(image_file_path, BLIP2_IMAGE_UPLOAD_URL):
            return {'status': 'Connection to BLIP2 Upload Server Error'}, 400
        
        # Caption generation
        model_data = {'current_image_filename': new_filename}
        response = requests.post(BLIP2_SERVER_URL, json=model_data)

        if not (response.status_code == 200):
            return {'status': 'Connection to BLIP2 Caption Server Error'}, 400

        caption = response.json()['answer']
        print(f"Caption: {caption}")
        narrator_text = f"The uploaded image is about, {caption}"
        ssml_narrator = ssml_narrator_template.replace("<<TEXT>>", narrator_text)

        print("before azure api call")
        speech_synthesis_result = speech_synthesizer.speak_ssml(ssml_narrator)
        speech_synthesis_result_audio = speech_synthesis_result.audio_data
        print("after azure api call")

        caption_generation_time = str(datetime.now().strftime("%H-%M-%S"))
        caption_filename = caption_generation_time + "_caption" + ".wav"
        caption_path = os.path.join(session['session_folder_path'], caption_filename)

        transcript_file_path = os.path.join(session['session_folder_path'], "transcript.txt")
        with open(transcript_file_path, 'a') as file:
            file.write(f"[UPLOADED CUSTOM IMAGE NAME]> {new_filename} \n[INITIAL CAPTION]>> {caption} \n\n")

        with open(caption_path, mode='bw') as f:
            f.write(speech_synthesis_result_audio)

        return send_file(
            caption_path, 
            mimetype="audio/wav", 
            as_attachment=True, 
            download_name="test.wav")



@app.route("/", methods=["GET", "POST"])
def index():
    transcript = ""
    if request.method == "POST":
        return "Audio received2", 200
    return render_template('index.html', transcript=transcript)


if __name__ == "__main__":
    app.run(debug=True, threaded=True)