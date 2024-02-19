//const { i } = require("pos/lexicon");

//const { read } = require("pos/lexicon");

//webkitURL is deprecated but nevertheless
URL = window.URL || window.webkitURL;

var gumStream; 						//stream from getUserMedia()
var recorder; 						//WebAudioRecorder object
var input; 							//MediaStreamAudioSourceNode  we'll be recording
var encodingType = "wav";
var encodeAfterRecord = true;       // when to encode

// shim for AudioContext when it's not avb. 
var AudioContext = window.AudioContext || window.webkitAudioContext;
var audioContext; //new audio context to help us record
var questionAnswerRoundCounter = 0;

//add events to those 2 buttons

var spaceBarPressed = false;
var studyStarted = false;
var fKeyPressed = false;
var nKeyPressed = false;
var isfeedbackState = false;


var microphone_permission_granted = false;


var readInstructionAudio = undefined;

document.getElementById('readInstructions').addEventListener('click', function () {

	// check if audio already playing
	if (readInstructionAudio !== undefined && !readInstructionAudio.paused) {
		readInstructionAudio.pause();
		return;
	}

	var readInstructionPath = "/static/audio/study_instructions.wav";
	readInstructionAudio = new Audio(readInstructionPath);
	readInstructionAudio.volume = 0.5;
	readInstructionAudio.play();
});


document.getElementById('requestMicrophonePermission').addEventListener('click', function () {
	// check if we already have microphone permission
	navigator.mediaDevices.getUserMedia({ audio: true })
	.then(function (stream) {
		microphone_permission_granted = true;
		// say something like please allow microphone access
		var micAlreadyGrantedPath = "";
		console.log(studyStarted)
		if (studyStarted == true) {
			micAlreadyGrantedPath = "/static/audio/microphone_permission_granted.wav"
		}else{
			micAlreadyGrantedPath = "/static/audio/microphone_permission_granted_now_start_study.wav"

		}
		document.getElementById("studyStartButton").disabled = false;
		var micAlreadyGrantedAudio = new Audio(micAlreadyGrantedPath);
		micAlreadyGrantedAudio.volume = 0.5;
		micAlreadyGrantedAudio.play();
	}).catch(function(err) {
		microphone_permission_granted = false;
		//TODO: insert correct wav file
		console.log("please allow microphone access")
		var pleaseAllowMicPermissionPath = "/static/audio/please_allow_microphone_access.wav";
		var pleaseAllowMicPermissionAudio = new Audio(pleaseAllowMicPermissionPath);
		pleaseAllowMicPermissionAudio.volume = 0.5;
		pleaseAllowMicPermissionAudio.play();
		//requestMicrophonePermission();
	});
});


// Add click event listener to the button
document.getElementById('studyStartButton').addEventListener('click', function () {

	console.log("microphone permission granted?")
	console.log(microphone_permission_granted)
	studyStarted = true;

	if (!microphone_permission_granted) {
		//TODO: insert correct wav file
		console.log("please allow microphone permission first")
		var pleaseAllowMicPermissionPath = "/static/audio/grant_microphone_acceess_to_start_study.wav";
		var pleaseAllowMicPermissionAudio = new Audio(pleaseAllowMicPermissionPath);
		pleaseAllowMicPermissionAudio.volume = 0.5;
		pleaseAllowMicPermissionAudio.play();
		return;
	}
	
	// send post request to server


	fetch('/start-study', {
		method: 'POST',
	}).then(response => {
		if(response.ok) {
			return response.blob();
		} else {
			throw new Error('Error uploading file');
		}
	}).then(blob => {
		var audioContext = new (window.AudioContext || window.webkitAudioContext)();
		var source = audioContext.createBufferSource();
		blob.arrayBuffer().then(arrayBuffer => {
			audioContext.decodeAudioData(arrayBuffer, buffer => {
				source.buffer = buffer;
				source.connect(audioContext.destination);
				source.start();
			}, error => {
				console.error('Error decoding audio data', error);
			});
		});
	}).catch(error => {
		console.error(error);
	});

	//var study_started_sound = new Audio("/static/audio/study_started.wav");
	//study_started_sound.volume = 0.5;
	//study_started_sound.play();
	//stream.getTracks().forEach(track => track.stop());
	// disable study start button

	document.getElementById("studyStartButton").disabled = true;
	//document.getElementById("studyStartButton").style.backgroundColor = "gray";


});

document.addEventListener("keydown", function(event) {
  // instruction
  if (event.key === " ") {
    event.preventDefault();

	if (!spaceBarPressed && event.target == document.body && studyStarted == true) {
		console.log("start recording");
		startRecording();
		spaceBarPressed = true;
	}
  }


  // feedback
  if (event.key === "f") {
    event.preventDefault();

	if (!fKeyPressed && studyStarted == true) {
		console.log("start recording");
		startRecording();
		fKeyPressed = true;
	}
  }

  // next image
  // feedback
  if (event.key === "n") {
    event.preventDefault();

	if (!nKeyPressed && studyStarted == true) {
		console.log("n pressed");
		nextImage();
		nKeyPressed = true;
	}
  }

});

document.addEventListener("keyup", function(event) {
  if (event.key === " " && studyStarted == true) {
	console.log("space bar released");
	stopRecording();
    spaceBarPressed = false;
  }

  if (event.key === "f" && fKeyPressed == true && studyStarted == true) {
	console.log("F key released");
	stopRecording(isFeedback=true);
	fKeyPressed = false;
  }

  if (event.key === "n" && nKeyPressed == true && studyStarted == true) {
	console.log("n key released");
	nKeyPressed = false;
  }
});


document.getElementById('upload-image').addEventListener('click', function() {

	// play press sounds
	var pressSound = new Audio("/static/audio/press_sound.wav");
	pressSound.volume = 0.2;
	pressSound.play();

    var fileInput = document.getElementById('select-image');
    var file = fileInput.files[0];
    var formData = new FormData();
    formData.append('image', file);


	var waitingSound = new Audio("/static/audio/waiting_sound.wav");
	waitingSound.loop = true;
	waitingSound.volume = 0.2;
	waitingSound.play();

	fetch('/upload-image', {
		method: 'POST',
		body: formData
	})
	.then(response => {
		if (!response.ok) {
			waitingSound.loop = false;
			waitingSound.pause();
			throw new Error('Upload failed');
		}
		// response is okay

		waitingSound.loop = false;
		waitingSound.pause();

		fileInput.value = null;  // Reset file input
		return response.blob();
	})
	.then(blob => {
		var url = window.URL.createObjectURL(blob);
		var audio = new Audio(url);
		audio.play();
	})
	.catch(error => console.error(error));


});


function nextImage() {
    fetch('/next-image', {
        method: 'POST',
    }).then(response => {
        console.log("Audio response: ")
        console.log(response.ok)
        if(response.ok) {
            var contentDisposition = response.headers.get('Content-Disposition');
            var filename = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)[1];
            console.log("Filename: " + filename);
            if(filename.includes("start_custom_image_upload")) {
				// add here what will happen when the user has to upload custom images
				// Deactivate the input element
				document.getElementById("select-image").disabled = false;

				// Deactivate the button element
				document.getElementById("upload-image").disabled = false;
            }
            return response.blob();
        } else {
            throw new Error('Error uploading file');
        }
    }).then(blob => {
        var audioContext = new (window.AudioContext || window.webkitAudioContext)();
        var source = audioContext.createBufferSource();
        blob.arrayBuffer().then(arrayBuffer => {
            audioContext.decodeAudioData(arrayBuffer, buffer => {
                source.buffer = buffer;
                source.connect(audioContext.destination);
                source.start();
            }, error => {
                console.error('Error decoding audio data', error);
            });
        });
    }).catch(error => {
        console.error(error);
    });
}



function startRecording() {
	console.log("startRecording() called");

    var constraints = { audio: true, video:false }

	navigator.mediaDevices.getUserMedia(constraints).then(function(stream) {
		audioContext = new AudioContext();

		//update the format 

		gumStream = stream;
		input = audioContext.createMediaStreamSource(stream);
		
		recorder = new WebAudioRecorder(input, {
		  workerDir: "static/js/", // must end with slash
		  encoding: encodingType,
		  numChannels:2, //2 is the default, mp3 encoding supports only 2
		  onEncoderLoading: function(recorder, encoding) {
		    // show "loading encoder..." display
		  },
		  onEncoderLoaded: function(recorder, encoding) {
		    // hide "loading encoder..." display
		  }
		});


		recorder.setOptions({
		  timeLimit:120,
		  encodeAfterRecord:encodeAfterRecord,
	      ogg: {quality: 0.5},
	      mp3: {bitRate: 160}
	    });

		//start the recording process
		recorder.startRecording();

		var pressSound = new Audio("/static/audio/press_sound.wav");
		pressSound.volume = 0.2;
		pressSound.play();


	}).catch(function(err) {
	});

}



function stopRecording(isFeedback=false) {
    //stop microphone access
    gumStream.getAudioTracks()[0].stop();


	var releaseSound = new Audio("/static/audio/release_sound.wav");
	releaseSound.volume = 0.2;
	releaseSound.play();

    recorder.onComplete = function(recorder, blob) { 
		// Get the current date and time
		const currentDate = new Date();

		// Format the date and time as a string
		const formattedDate = currentDate.toLocaleString().replace(/[ ,:]/g, '_');

		// Create a new filename with the current date and time
		const filename = `audio_${formattedDate}.wav`;

		// Create the File object with the new filename
		let file = new File([blob], filename, {
			type: 'audio/wav'
		});

		// send feedback voice message
		if (isFeedback) {
			let data = new FormData();
				data.append('file', file);
				fetch('/feedback', {
					method: 'POST',
					body: data,
				}).then(response => {
					if(response.ok) {
						return response.blob();
					} else {
						throw new Error('Error uploading file');
					}
				}).then(blob => {
					var audioContext = new (window.AudioContext || window.webkitAudioContext)();
					var source = audioContext.createBufferSource();
					blob.arrayBuffer().then(arrayBuffer => {
						audioContext.decodeAudioData(arrayBuffer, buffer => {
							source.buffer = buffer;
							source.connect(audioContext.destination);
							source.start();
						}, error => {
							console.error('Error decoding audio data', error);
						});
					});
				}).catch(error => {
					console.error(error);
				});
		}else{ // send instruction for Visual Assistant
		let data = new FormData();
		data.append('file', file);
		var waitingSound = new Audio("/static/audio/waiting_sound.wav");
		waitingSound.loop = true;
		waitingSound.volume = 0.2;
		waitingSound.play();
		fetch('/upload', {
			method: 'POST',
			body: data,
		}).then(response => {
			if(response.ok) {
				waitingSound.loop = false;
				waitingSound.pause();
				return response.blob();
			} else {
				throw new Error('Error uploading file');
			}
		}).then(blob => {
			var audioContext = new (window.AudioContext || window.webkitAudioContext)();
			var source = audioContext.createBufferSource();

			blob.arrayBuffer().then(arrayBuffer => {
				audioContext.decodeAudioData(arrayBuffer, buffer => {
					source.buffer = buffer;
					source.connect(audioContext.destination);
					source.start();

					console.log("questionAnswerRoundCounter: " + questionAnswerRoundCounter);
				}, error => {
					console.error('Error decoding audio data', error);
				});
			});
		}).catch(error => {
			waitingSound.loop = false;
			waitingSound.pause();
			console.error(error);
		});
	}
    }
    
    //tell the recorder to finish the recording (stop recording + encode the recorded audio)
    recorder.finishRecording();

}

