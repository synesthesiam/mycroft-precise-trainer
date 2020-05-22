#!/usr/bin/env python3
"""doit file"""
import itertools
import json
import logging
import tempfile
from pathlib import Path
from urllib.parse import urlencode, urljoin
from uuid import uuid4

import pydash
from doit import create_after

DOIT_CONFIG = {"action_string_formatting": "new"}

# -----------------------------------------------------------------------------

_DIR = Path(__file__).parent

# Temporary directory
_tempdir_obj = tempfile.TemporaryDirectory()
_TEMPDIR = Path(_tempdir_obj.name)

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger("dodo")

_CONFIG_PATH = _DIR / "config.json"
_LOGGER.debug("Loading config from %s", _CONFIG_PATH)
with open(_CONFIG_PATH, "r") as config_file:
    _CONFIG = json.load(config_file)

_CACHE_DIR = _DIR / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------


def task_random_data():
    """Download and extract random WAV data."""
    wav_dir = _DIR / pydash.get(_CONFIG, "random_data.wav_directory", "data/random")
    wav_dir.mkdir(parents=True, exist_ok=True)

    download_dir = _DIR / pydash.get(
        _CONFIG, "random_data.download_directory", "download"
    )
    download_dir.mkdir(parents=True, exist_ok=True)

    # Download/extract files
    datasets = pydash.get(_CONFIG, "random_data.datasets", {})
    for dataset_key, dataset_info in datasets.items():
        dataset_dir = download_dir / dataset_key
        base_url = dataset_info["base_url"]
        if not base_url.endswith("/"):
            base_url += "/"

        for file_name in dataset_info["files"]:
            file_path = dataset_dir / file_name
            if not file_path.exists():
                # Download
                file_url = urljoin(base_url, file_name)
                yield {
                    "name": f"download_{dataset_key}_{file_name}",
                    "targets": [file_path],
                    "actions": [f"wget -O {{targets}} '{file_url}'"],
                }

            # Extract
            yield {
                "name": f"extract_{dataset_key}_{file_name}",
                "file_dep": [file_path],
                "actions": [f"tar -C '{wav_dir}' -xf {{dependencies}}"],
            }


# -----------------------------------------------------------------------------


def task_not_wake_words():
    """Download and extract negative test examples."""
    wakeword_id = pydash.get(_CONFIG, "wake_word.id")
    assert wakeword_id, "wake_word.id is required"

    model_dir = _DIR / pydash.get(_CONFIG, "model_directory", "models")
    wakeword_dir = model_dir / wakeword_id

    # data/test/not-wake-word
    wav_dir = wakeword_dir / "data" / "test" / "not-wake-word"
    wav_dir.mkdir(parents=True, exist_ok=True)

    download_dir = _DIR / pydash.get(
        _CONFIG, "random_data.download_directory", "download"
    )
    download_dir.mkdir(parents=True, exist_ok=True)

    # Download/extract files
    datasets = pydash.get(_CONFIG, "testing.not_wake_words", {})
    for dataset_key, dataset_info in datasets.items():
        dataset_dir = download_dir / dataset_key
        base_url = dataset_info["base_url"]
        if not base_url.endswith("/"):
            base_url += "/"

        for file_name in dataset_info["files"]:
            file_path = dataset_dir / file_name
            if not file_path.exists():
                # Download
                file_url = urljoin(base_url, file_name)
                yield {
                    "name": f"download_{dataset_key}_{file_name}",
                    "targets": [file_path],
                    "actions": [f"wget -O {{targets}} '{file_url}'"],
                }

            # Extract
            yield {
                "name": f"extract_{dataset_key}_{file_name}",
                "file_dep": [file_path],
                "actions": [f"tar -C '{wav_dir}' -xf {{dependencies}}"],
            }


# -----------------------------------------------------------------------------


def task_test_examples():
    """Copy positive test examples."""
    wakeword_id = pydash.get(_CONFIG, "wake_word.id")
    assert wakeword_id, "wake_word.id is required"

    model_dir = _DIR / pydash.get(_CONFIG, "model_directory", "models")
    wakeword_dir = model_dir / wakeword_id

    src_dir = _DIR / pydash.get(_CONFIG, "testing.wake_words")
    if not src_dir:
        _LOGGER.warning("Not positive test examples provided")
        return

    # data/test/wake-word
    dest_dir = wakeword_dir / "data" / "test" / "wake-word"
    dest_dir.mkdir(parents=True, exist_ok=True)

    for wav_path in src_dir.glob("*.wav"):
        yield {
            "name": f"copy_{wav_path.name}",
            "file_dep": [wav_path],
            "targets": [dest_dir / wav_path.name],
            "actions": ["cp {dependencies} {targets}"],
        }


# -----------------------------------------------------------------------------


def task_voices():
    """Gets list of TTS voices to use."""
    # OpenTTS URL (https://github.com/synesthesiam/opentts)
    server_url = pydash.get(
        _CONFIG, "text_to_speech.server_url", "http://localhost:5500"
    )

    if not server_url.endswith("/"):
        server_url += "/"

    # Explicit list of voices
    voices = pydash.get(_CONFIG, "text_to_speech.voices", [])
    voices_path = _CACHE_DIR / "voices.txt"

    if voices:
        # Explicitly write voices
        def write_voices(voices, targets):
            with open(targets[0], "w") as target_file:
                for voice in sorted(voices):
                    voice = voice.strip()
                    if voice:
                        print(voice, file=target_file)

        yield {
            "name": "voices",
            "file_dep": [_CONFIG_PATH],
            "targets": [voices_path],
            "actions": [(write_voices, voices)],
        }
    else:
        # Determine voices based on other constraints
        languages = pydash.get(_CONFIG, "text_to_speech.languages", [])
        locales = pydash.get(_CONFIG, "text_to_speech.locales", [])
        genders = pydash.get(_CONFIG, "text_to_speech.genders", [])
        tts_names = pydash.get(_CONFIG, "text_to_speech.tts_names", [])

        query = urlencode(
            [("language", language) for language in languages]
            + [("locale", locale) for locale in locales]
            + [("gender", gender) for gender in genders]
            + [("tts_name", tts_name) for tts_name in tts_names]
        )

        voices_url = urljoin(server_url, "api/voices?" + query)

        # Get voice names
        yield {
            "name": "voices",
            "file_dep": [_CONFIG_PATH],
            "targets": [voices_path],
            "actions": [
                f"wget -O - '{voices_url}' | jq --raw-output 'keys[]' | sort | uniq > {{targets}}"
            ],
        }


@create_after(executed="voices")
def task_tts():
    """Creates base WAV files from TTS system(s)."""
    # Load settings
    wakeword_id = pydash.get(_CONFIG, "wake_word.id")
    assert wakeword_id, "wake_word.id is required"

    wakeword_text = pydash.get(_CONFIG, "wake_word.text")
    assert wakeword_text, "wake_word.text is required"

    not_wake_words = pydash.get(_CONFIG, "wake_word.not_wake_words")

    # OpenTTS URL (https://github.com/synesthesiam/opentts)
    server_url = pydash.get(
        _CONFIG, "text_to_speech.server_url", "http://localhost:5500"
    )

    if not server_url.endswith("/"):
        server_url += "/"

    model_dir = _DIR / pydash.get(_CONFIG, "model_directory", "models")
    wakeword_dir = model_dir / wakeword_id
    wakeword_dir.mkdir(parents=True, exist_ok=True)

    # data/wake-word
    positive_examples_dir = wakeword_dir / "data" / "wake-word"
    positive_examples_dir.mkdir(parents=True, exist_ok=True)

    # data/not-wake-word
    negative_examples_dir = wakeword_dir / "data" / "not-wake-word"
    negative_examples_dir.mkdir(parents=True, exist_ok=True)

    # Audio effects
    rates = set(pydash.get(_CONFIG, "sound_effects.rates", []) + [0.0])
    pitches = set(pydash.get(_CONFIG, "sound_effects.pitches", []) + [0.0])
    noises = set(pydash.get(_CONFIG, "sound_effects.noises", []) + [0.0])
    volumes = set(pydash.get(_CONFIG, "sound_effects.volumes", []) + [1.0])
    reverbs = set([pydash.get(_CONFIG, "sound_effects.reverb", False)] + [False])

    # Load voices to use
    voices_path = _CACHE_DIR / "voices.txt"
    voices = set()
    with open(voices_path, "r") as voices_file:
        for line in voices_file:
            line = line.strip()
            if line:
                voices.add(line)

    # Generate WAV file(s)
    dir_texts = [(positive_examples_dir, wakeword_text)] + [
        (negative_examples_dir, w) for w in not_wake_words
    ]

    for voice in voices:
        for output_dir, text in dir_texts:
            query = urlencode({"text": text, "voice": voice})
            tts_url = urljoin(server_url, "api/tts?" + query)

            wav_name = text.replace(" ", "_") + "_" + voice.replace(":", "_")
            wav_path = output_dir / f"{wav_name}.wav"

            yield {
                "name": f"tts_{wav_name}",
                "file_dep": [voices_path],
                "targets": [wav_path],
                "actions": [f"wget -O {{targets}} '{tts_url}'"],
            }

            # Create effects
            for rate, pitch, noise, volume, reverb in itertools.product(
                rates, pitches, noises, volumes, reverbs
            ):
                reverb_str = "_reverb" if reverb else ""
                effect_wav_path = (
                    output_dir
                    / f"{wav_name}_r{rate}_p{pitch}_n{noise}_v{volume}{reverb_str}.wav"
                )
                effects = []

                if rate != 0:
                    effects.extend(["tempo", "-s", str(rate)])

                if pitch != 0:
                    effects.extend(["pitch", str(pitch)])

                if volume != 1:
                    effects.extend(["vol", str(volume)])

                if reverb:
                    effects.extend(
                        ["reverb", "reverb", "-w", "0", "0", "0", "0", "0", "5"]
                    )

                if effects and (noise <= 0):
                    # Single pass with no noise
                    effects_str = " ".join(effects)
                    yield {
                        "name": f"effect_{effect_wav_path.name}",
                        "file_dep": [wav_path],
                        "targets": [effect_wav_path],
                        "actions": [f"sox {{dependencies}} {{targets}} {effects_str}"],
                    }
                elif noise > 0:
                    # Pipe through sox twice to add noise
                    prenoise_wav_path = _TEMPDIR / (str(uuid4()) + ".wav")
                    effects_str = " ".join(effects)
                    yield {
                        "name": f"effect_{effect_wav_path.name}",
                        "file_dep": [wav_path],
                        "targets": [effect_wav_path],
                        "actions": [
                            f"sox {{dependencies}} '{prenoise_wav_path}' {effects_str};"
                            + f"sox '{prenoise_wav_path}' -p synth whitenoise vol {noise} | sox -m '{prenoise_wav_path}' - {{targets}}"
                        ],
                    }


# -----------------------------------------------------------------------------


@create_after(executed="random_data")
@create_after(executed="tts")
def task_wav_lists():
    """Generate lists of WAV files used to train model."""
    random_dir = _DIR / pydash.get(_CONFIG, "random_data.wav_directory", "data/random")

    # Generate list of random data WAV files
    random_data_files = _CACHE_DIR / "random_data_files.txt"
    yield {
        "name": "random_data_files",
        "targets": [random_data_files],
        "actions": [f"ls -1 '{random_dir}' | sort | uniq > {{targets}}"],
    }

    # Generate lists of example WAV files
    wakeword_id = pydash.get(_CONFIG, "wake_word.id")
    model_dir = _DIR / pydash.get(_CONFIG, "model_directory", "models")
    wakeword_dir = model_dir / wakeword_id

    positive_examples_dir = wakeword_dir / "data" / "wake-word"
    positive_wav_files = _CACHE_DIR / "positive_wav_files.txt"

    yield {
        "name": "positive_wav_files",
        "targets": [positive_wav_files],
        "actions": [f"ls -1 '{positive_examples_dir}' | sort | uniq > {{targets}}"],
    }

    negative_examples_dir = wakeword_dir / "data" / "not-wake-word"
    negative_wav_files = _CACHE_DIR / "negative_wav_files.txt"

    yield {
        "name": "negative_wav_files",
        "targets": [negative_wav_files],
        "actions": [f"ls -1 '{negative_examples_dir}' | sort | uniq > {{targets}}"],
    }


# -----------------------------------------------------------------------------


@create_after(executed="test_examples")
def task_train():
    """Initial training."""
    # Load settings
    wakeword_id = pydash.get(_CONFIG, "wake_word.id")
    assert wakeword_id, "wake_word.id is required"

    model_dir = _DIR / pydash.get(_CONFIG, "model_directory", "models")
    wakeword_dir = model_dir / wakeword_id
    model_path = wakeword_dir / f"{wakeword_id}.net"
    data_dir = wakeword_dir / "data"

    epochs = pydash.get(_CONFIG, "training.epochs", 1000)

    test_path = wakeword_dir / "test.1.txt"
    positive_wav_files = _CACHE_DIR / "positive_wav_files.txt"
    negative_wav_files = _CACHE_DIR / "negative_wav_files.txt"

    yield {
        "name": "train",
        "file_dep": [positive_wav_files, negative_wav_files],
        "targets": [test_path],
        "actions": [
            f"precise-train --epochs {epochs} '{model_path}' '{data_dir}'"
            + f"&& precise-test '{model_path}' '{data_dir}' > {{targets}}"
        ],
    }


# -----------------------------------------------------------------------------


@create_after(executed="random_data")
@create_after(executed="train")
def task_train_incremental():
    """Incremental training with random data."""
    # Load settings
    wakeword_id = pydash.get(_CONFIG, "wake_word.id")
    assert wakeword_id, "wake_word.id is required"

    model_dir = _DIR / pydash.get(_CONFIG, "model_directory", "models")
    wakeword_dir = model_dir / wakeword_id
    model_path = wakeword_dir / f"{wakeword_id}.net"
    data_dir = wakeword_dir / "data"

    random_dir = _DIR / pydash.get(_CONFIG, "random_data.wav_directory", "data/random")

    epochs = pydash.get(_CONFIG, "training.epochs_incremental", 1000)

    test_path = wakeword_dir / "test.2.txt"
    positive_wav_files = _CACHE_DIR / "positive_wav_files.txt"
    negative_wav_files = _CACHE_DIR / "negative_wav_files.txt"

    yield {
        "name": "train",
        "file_dep": [positive_wav_files, negative_wav_files],
        "targets": [test_path, model_path],
        "actions": [
            f"precise-train-incremental --epochs {epochs} --random-data-folder '{random_dir}' '{model_path}' '{data_dir}'"
            + f"&& precise-test '{model_path}' '{data_dir}' > {{targets}}"
        ],
    }


# -----------------------------------------------------------------------------


def task_convert():
    """Convert model to .pb"""
    # Load settings
    wakeword_id = pydash.get(_CONFIG, "wake_word.id")
    assert wakeword_id, "wake_word.id is required"

    model_dir = _DIR / pydash.get(_CONFIG, "model_directory", "models")
    model_path = model_dir / wakeword_id / f"{wakeword_id}.net"
    converted_path = model_path.with_suffix(".pb")

    yield {
        "name": "convert",
        "file_dep": [model_path],
        "targets": [converted_path],
        "actions": ["precise-convert {dependencies}"],
    }
