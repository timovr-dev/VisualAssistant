//const { i } = require("pos/lexicon");

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

var recordButton = document.getElementById("recordButton");
var stopButton = document.getElementById("stopButton");


var questionAnswerRoundCounter = 0;

//add events to those 2 buttons
//recordButton.addEventListener("click", startRecording);
//stopButton.addEventListener("click", stopRecording);

var spaceBarPressed = false;
var studyStarted = true;
var fKeyPressed = false;
var isfeedbackState = false;

var study_started_sound = new Audio("/static/audio/study_started.wav");
        study_started_sound.volume = 0.5;
        study_started_sound.play();
// Function to request microphone permission

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
});


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
	  	//enable the record button if getUSerMedia() fails
    	recordButton.disabled = false;
    	stopButton.disabled = true;
	});

	//disable the record button
    recordButton.disabled = true;
    stopButton.disabled = false;
}



function stopRecording(isFeedback=false) {
    //stop microphone access
    gumStream.getAudioTracks()[0].stop();

    //disable the stop button
    stopButton.disabled = true;
    recordButton.disabled = false;

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

