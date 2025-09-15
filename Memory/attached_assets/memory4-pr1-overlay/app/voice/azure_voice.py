import azure.cognitiveservices.speech as speechsdk

def transcribe_wav(path: str, key: str, region: str, locale: str="en-US") -> str:
    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    speech_config.speech_recognition_language = locale
    audio_config = speechsdk.audio.AudioConfig(filename=path)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    res = recognizer.recognize_once()
    return res.text if res.reason == speechsdk.ResultReason.RecognizedSpeech else ""

def synthesize_to_file(text: str, out_path: str, key: str, region: str, voice: str="en-US-JennyNeural") -> bool:
    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    speech_config.speech_synthesis_voice_name = voice
    audio_config = speechsdk.audio.AudioOutputConfig(filename=out_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    res = synthesizer.speak_text_async(text).get()
    return res.reason == speechsdk.ResultReason.SynthesizingAudioCompleted
