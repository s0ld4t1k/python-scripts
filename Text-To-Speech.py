from gtts import gTTS

text='привет чмошники как вы там'
language='ru'

tts=gTTS(text=text, lang=language)
tts.save("voice.mp3")
print('Audio saved successfully!')