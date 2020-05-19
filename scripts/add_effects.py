#!/usr/bin/env python3
import argparse
import itertools
import logging
import shlex
import tempfile
from pathlib import Path
from uuid import uuid4


_LOGGER = logging.getLogger("add_effects")

# -----------------------------------------------------------------------------


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(prog="add_effects.py")
    parser.add_argument("wav_file", help="WAV file to add effects to")
    parser.add_argument("output_dir", help="Output directory")
    parser.add_argument(
        "--rate",
        type=float,
        action="append",
        default=[],
        help="Adjust rate by factor (e.g., 1.5)",
    )
    parser.add_argument(
        "--pitch",
        type=float,
        action="append",
        default=[],
        help="Adjust pitch by cents (e.g., -50)",
    )
    parser.add_argument(
        "--noise",
        type=float,
        action="append",
        default=[],
        help="Add amount of white noise (e.g., 0.5)",
    )
    parser.add_argument(
        "--volume",
        type=float,
        action="append",
        default=[],
        help="Adjust volume by fraction (e.g., 0.3)",
    )
    parser.add_argument("--reverb", action="store_true", help="Add reverb effect")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    wav_file = Path(args.wav_file)
    temp_dir = Path(tempfile.gettempdir())

    # Add default settings
    args.rate = set(args.rate + [0.0])
    args.pitch = set(args.pitch + [0.0])
    args.noise = set(args.noise + [0.0])
    args.volume = set(args.volume + [1.0])
    args.reverb = set([args.reverb + False])

    for rate, pitch, noise, volume, reverb in itertools.product(
        args.rate, args.pitch, args.noise, args.volume, args.reverb
    ):
        output_path = output_dir / get_wav_name(
            wav_file.stem, rate, pitch, noise, volume, reverb
        )

        effects = []

        if rate != 0:
            effects.extend(["tempo", "-s", str(rate)])

        if pitch != 0:
            effects.extend(["pitch", str(pitch)])

        if volume != 1:
            effects.extend(["vol", str(volume)])

        if reverb:
            effects.extend(["reverb", "reverb", "-w", "0", "0", "0", "0", "0", "5"])

        if effects and (noise <= 0):
            # Single pass with no noise
            sox_cmd = [
                "sox",
                shlex.quote(str(wav_file)),
                shlex.quote(str(output_path)),
            ] + effects
            print(" ".join(sox_cmd))
        elif noise > 0:
            # Pipe through sox twice to add noise
            temp_path = temp_dir / (str(uuid4()) + ".wav")

            sox_cmd_1 = [
                "sox",
                shlex.quote(str(wav_file)),
                shlex.quote(str(temp_path)),
            ] + effects

            sox_cmd_2 = [
                "sox",
                shlex.quote(str(temp_path)),
                "-p",
                "synth",
                "whitenoise",
                "vol",
                str(noise),
                "|",
                "sox",
                "-m",
                shlex.quote(str(temp_path)),
                "-",
                shlex.quote(str(output_path)),
            ]

            sox_cmd_1_str = " ".join(sox_cmd_1)
            sox_cmd_2_str = " ".join(sox_cmd_2)

            print(f"({sox_cmd_1_str}) && ({sox_cmd_2_str})")


# -----------------------------------------------------------------------------


def get_wav_name(base_name, rate, pitch, noise, volume, reverb):
    wav_name = f"{base_name}_r{rate}_p{pitch}_n{noise}_v{volume}"
    if reverb:
        wav_name += "_reverb"

    return wav_name + ".wav"


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
