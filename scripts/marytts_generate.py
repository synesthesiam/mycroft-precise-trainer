#!/usr/bin/env python3
import argparse
import io
import re
import shlex
import subprocess
import typing
import wave
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np
import requests
import scipy.io.wavfile

# -----------------------------------------------------------------------------


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"


@dataclass
class Voice:
    name: str
    locale: str
    gender: Gender


VOICES: typing.List[Voice] = [
    Voice(name="cmu-slt-hsmm", locale="en-US", gender=Gender.FEMALE),
    Voice(name="dfki-prudence-hsmm", locale="en-GB", gender=Gender.FEMALE),
    Voice(name="dfki-poppy-hsmm", locale="en-GB", gender=Gender.FEMALE),
    Voice(name="dfki-spike-hsmm", locale="en-GB", gender=Gender.MALE),
    Voice(name="dfki-obadiah-hsmm", locale="en-GB", gender=Gender.MALE),
    Voice(name="cmu-rms-hsmm", locale="en-US", gender=Gender.MALE),
    Voice(name="cmu-bdl-hsmm", locale="en-US", gender=Gender.MALE),
]

XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<maryxml version="0.5" xml:lang="{locale}">
<p>
  <prosody rate="{rate}" pitch="{pitch}">
    <s>
      <phrase>{text}</phrase>
    </s>
  </prosody>
</p>
</maryxml>"""

DEFAULT_PARAMS: typing.Dict[str, str] = {"AUDIO": "WAVE", "OUTPUT_TYPE": "AUDIO"}

RATES = range(-30, 30 + 1, 15)
PITCHES = range(-30, 30 + 1, 10)
NOISES = [0, 300, 500]
EFFECTS = {"Reverb": "reverb -w 0 0 0 0 0 5", "Quiet": "vol 0.3", "None": ""}

URL = "http://localhost:59125/process"

# -----------------------------------------------------------------------------


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(prog="marytts_generate.py")
    parser.add_argument("text", help="Words to generate")
    parser.add_argument("output_dir", help="Output directory")
    parser.add_argument("--phonemes", help="MaryTTS phonemes to use for pronunciation")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    text = args.text.strip()
    text_dashes = re.sub("\s+", "-", text.replace("'", "").strip())

    for voice in VOICES:
        for rate in RATES:
            for pitch in PITCHES:
                # Generate non-noisy
                base_wav_path = (
                    output_dir
                    / f"{text_dashes}_{voice.name}_r{rate}_p{pitch}_n0_eNone.wav"
                )

                if not base_wav_path.exists():
                    base_wav_data = get_wav(
                        text,
                        voice.name,
                        voice.locale,
                        rate,
                        pitch,
                        phonemes=args.phonemes,
                    )
                    write_wav(base_wav_data, base_wav_path)
                    print(base_wav_path)

                wav_rate, wav_frames = scipy.io.wavfile.read(base_wav_path)

                # Add effects/noise
                for effect, effect_params in EFFECTS.items():
                    for noise in NOISES:
                        noisy_wav_path = (
                            output_dir
                            / f"{text_dashes}_{voice.name}_r{rate}_p{pitch}_n{noise}_e{effect}.wav"
                        )

                        if noisy_wav_path.is_file():
                            # Already exists
                            continue

                        if noise != 0:
                            wav_noisy = wav_frames + (
                                noise * np.random.randn(len(wav_frames))
                            )
                            wav_noisy = wav_noisy.astype("int16")
                        else:
                            # No noise
                            wav_noisy = wav_frames

                        if effect != "None":
                            # Apply effect
                            with io.BytesIO() as wav_io:
                                scipy.io.wavfile.write(wav_io, wav_rate, wav_noisy)
                                wav_noisy = subprocess.check_output(
                                    [
                                        "sox",
                                        "-t",
                                        "wav",
                                        "-",
                                        "-t",
                                        "wav",
                                        str(noisy_wav_path),
                                    ]
                                    + shlex.split(effect_params),
                                    input=wav_io.getvalue(),
                                )

                        else:
                            scipy.io.wavfile.write(noisy_wav_path, wav_rate, wav_noisy)

                        print(noisy_wav_path)


# -----------------------------------------------------------------------------


def get_wav(
    text: str,
    voice: str,
    locale: str,
    rate_offset: float = 0,
    pitch_offset: float = 0,
    phonemes: typing.Optional[bool] = None,
) -> bytes:
    if phonemes:
        text = f'<t ph="{phonemes}">{text}</t><t pos=".">.</t>'
    elif not text.endswith("."):
        text += "."

    if rate_offset < 0:
        rate_str = f"{rate_offset}%"
    else:
        rate_str = f"+{rate_offset}%"

    if pitch_offset < 0:
        pitch_str = f"{pitch_offset}%"
    else:
        pitch_str = f"+{pitch_offset}%"

    params = {
        "LOCALE": locale,
        "VOICE": voice,
        "INPUT_TYPE": "RAWMARYXML",
        "INPUT_TEXT": XML_TEMPLATE.format(
            text=text, locale=locale, rate=rate_str, pitch=pitch_str
        ),
        **DEFAULT_PARAMS,
    }

    response = requests.get(URL, params=params)
    response.raise_for_status()

    return response.content


def write_wav(wav_data: bytes, wav_path: typing.Union[str, Path]):
    wav_data = maybe_convert_wav(wav_data)

    with open(wav_path, "wb") as wav_file:
        wav_file.write(wav_data)


# -----------------------------------------------------------------------------


def convert_wav(wav_data: bytes, rate=16000, width=16, channels=1) -> bytes:
    """Converts WAV data to 16-bit, 16Khz mono with sox."""
    return subprocess.run(
        [
            "sox",
            "-t",
            "wav",
            "-",
            "-r",
            str(rate),
            "-e",
            "signed-integer",
            "-b",
            str(width),
            "-c",
            str(channels),
            "-t",
            "wav",
            "-",
        ],
        check=True,
        stdout=subprocess.PIPE,
        input=wav_data,
    ).stdout


def maybe_convert_wav(wav_data: bytes, rate=16000, width=16, channels=1) -> bytes:
    """Converts WAV data to 16-bit, 16Khz mono if necessary."""
    with io.BytesIO(wav_data) as wav_io:
        wav_file: wave.Wave_read = wave.open(wav_io, "rb")
        with wav_file:
            if (
                (wav_file.getframerate() != rate)
                or (wav_file.getsampwidth() != width)
                or (wav_file.getnchannels() != channels)
            ):
                return convert_wav(wav_data, rate=rate, width=width, channels=channels)

            return wav_file.readframes(wav_file.getnframes())


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
