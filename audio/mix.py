from pydub import AudioSegment
from pathlib import Path
import os

def mix_audio_files(audio):
    """
    Takes either a list of audio files or a directory of audio files and mixes them together.
    The mixed audio file is saved in a directory called 'mixed' in the same directory as the input audio.
    """

    if isinstance(audio, str) or isinstance(audio, Path):
        audio_path = Path(audio)
        audio_files = sorted([str(i).lower() for i in audio_path.glob("*.wav")])
    elif isinstance(audio, list):
        audio_files = sorted(audio)

    segments = [AudioSegment.from_file(file) for file in audio_files]
    duration = max([len(segment) for segment in segments])

    mix = AudioSegment.silent(duration=duration)

    for segment in segments:
        mix = mix.overlay(segment)

    mix_path = audio_path / 'mixed'
    os.makedirs(str(mix_path), exist_ok=True)
    mix.export(str(mix_path / 'audio_mixed.wav'), format='wav')


def mix_audio_arrays(list_of_arrays):
    """
    Takes a list of numpy arrays and mixes them together, padding the shorter arrays with zeros.
    """
    # find the longest array
    max_len = max([len(arr) for arr in list_of_arrays])
    # pad the shorter arrays with zeros
    padded_arrays = [np.pad(arr, (0, max_len-len(arr)), 'constant') for arr in list_of_arrays]
    # sum the arrays
    return np.sum(padded_arrays, axis=0)
