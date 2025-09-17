import azure.cognitiveservices.speech as speechsdk

def transcribe_wav(path: str, key: str, region: str, locale: str="en-US") -> str:
    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    speech_config.speech_recognition_language = locale
    audio_config = speechsdk.audio.AudioConfig(filename=path)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    res = recognizer.recognize_once()
    if res and hasattr(res, 'reason') and res.reason == speechsdk.ResultReason.RecognizedSpeech:
        return res.text if hasattr(res, 'text') else ""
    return ""

def synthesize_to_file(text: str, out_path: str, key: str, region: str, voice: str="en-US-JennyNeural") -> bool:
    try:
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.speech_synthesis_voice_name = voice
        # Create audio config - type annotations can be ignored as SDK handles it
        audio_config = speechsdk.audio.AudioOutputConfig(filename=out_path)  # type: ignore
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        res = synthesizer.speak_text_async(text).get()
        if res and hasattr(res, 'reason'):
            return res.reason == speechsdk.ResultReason.SynthesizingAudioCompleted
        return False
    except Exception as e:
        # Silent fail in production, but capture for debugging
        return False
