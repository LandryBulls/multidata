from pydub import AudioSegment
from pathlib import Path
import os

def mix_audio(audio_directory):
    audio_path = Path(audio_directory)
    audio_files = sorted([str(i) for i in audio_path.glob("*.WAV")])

    segments = [AudioSegment.from_file(file) for file in audio_files]
    duration = max([len(segment) for segment in segments])

    mix = AudioSegment.silent(duration=duration)

    for segment in segments:
        mix = mix.overlay(segment)

    mix_path = audio_path / 'mixed'
    os.makedirs(str(mix_path), exist_ok=True)
    mix.export(str(mix_path / 'audio_mixed.wav'), format='wav')
