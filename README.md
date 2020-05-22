# Mycroft Precise Trainer

Semi-automated scripts for training a custom wake word for [Mycroft Precise](https://github.com/MycroftAI/mycroft-precise) using synthetic data from multiple text to speech systems.

## Text to Speech

Uses an [OpenTTS server](https://github.com/synesthesiam/opentts) for text to speech samples. These samples are manipulated using [sox](http://sox.sourceforge.net) to add noise, change tempo/pitch, etc.

The following text to speech systems are available through [OpenTTS](https://github.com/synesthesiam/opentts):

* [eSpeak](http://espeak.sourceforge.net)
* [flite](http://www.festvox.org/flite)
* [Festival](http://www.cstr.ed.ac.uk/projects/festival/)
* [nanoTTS](https://github.com/gmn/nanotts)
* [MaryTTS](http://mary.dfki.de)
* [Mozilla TTS](https://github.com/mozilla/TTS)

## Training Process

Before training, ensure that you have the Mycroft Precise Trainer Docker image downloaded:

```bash
$ docker pull synesthesiam/mycroft-precise-trainer
```

The scripts in `bin/` will reference this Docker image to run `precise-train`, etc.

### Configuration

Training is controlled by the `config.json` file in the top-level directory of the respository. 

**NOTE:** All `config.json` directories are relative to the repository root directory.

The available settings are:

* `model_directory` - directory to store Precise models and training data (default: `models`)
* `wake_word`
    * `id` - file system friendly identifier for your wake word (used to name files/directories)
    * `text` - actual words that make up your wake word (e.g., "hey mycroft")
    * `not_wake_words` - list of phrases that are close but **not** the wake word (e.g., "hey microsoft")
* `training`
    * `epochs` - number of initial training epochs (default: 1000)
    * `epochs_incremental` - number of incremental training epochs with random data (default: 1000)
* `testing`
    * `wake_words` - directory with real WAV samples of the wake word
    * `not_wake_words` - datasets to download with negative examples
        * `<dataset name>` - name of dataset (used for download directory)
            * `base_url` - URL prefix of files to download
            * `files` - names of files to download (appended to `base_url`)
* `text_to_speech`
    * `server_url` - URL of [OpenTTS server](https://github.com/synesthesiam/opentts)
    * `voices` - list of TTS voices to use prefixed by TTS name (e.g., `marytts:cmu-slt-hsmm`)
        * Overrides other settings!
    * `tts_names` - list of TTS system names to use (empty = all)
    * `langauges` - list of languages to use (empty = all)
    * `locales` - list of locales to use (empty = all)
    * `genders` - list of genders to use (M/F, empty = all)
* `sound_effects`
    * TODO: describe settings (see example `config.json` for now)
* `random_data`
    * TODO: describe settings (see example `config.json` for now)

## Improvements

There is a lot of room for improvement:

* More audio effects to simulate voices in different types of rooms and places in a room
* Other kinds of noise (e.g., TV show)

Research questions:

* How may TTS samples are actually needed (positive, negative, and testing)?
* Can performance be improved by generating negative examples that sound similar (e.g., "okay raspberry")?
* Does selecting specific voices that sound like the intended user help performance?
* What is the best training process and number of epochs? Should incremental training be alternated?
* Could performance be improved by running a keyword spotter at runtime (e.g., Pocketsphinx) and modulating the chunk probability coming out of the Precise engine?
