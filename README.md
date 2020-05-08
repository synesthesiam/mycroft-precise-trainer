# Mycroft Precise Trainer

Rough set of scripts and Dockerfile for building a text-to-speech based training system for [Mycroft Precise](https://github.com/MycroftAI/mycroft-precise).

Used to train a sample model for the phrase "okay rhasspy" using **only** synthesized text to speech samples. About 20 real world samples were used for testing.

## Text to Speech

Uses [MaryTTS](http://mary.dfki.de/) for text to speech (`bin/marytts_generate.py`) with the following voices:

* cmu-slt-hsmm (female)
* dfki-prudence-hsmm (female)
* dfki-poppy-hsmm (female)
* dfki-spike-hsmm (male)
* dfki-obadiah-hsmm (male)
* cmu-rms-hsmm (male)
* cmu-bdl-hsmm (male)

Generates wake word samples with the following parameters:

* With 3 levels of white noise 
* Tempo adjustments from -30% to +30% (increments of 15%)
* Pitch adjustments from -30% to +30% (increments of 10%)
* Reverb effect to make voice sound far away (using [sox](http://sox.sourceforge.net))
* Volume reduction effect

## Training Process

Only one model has been trained so far as a test (`sample/okay-rhasspy.pb`). The process was:

1. Generate ~2k TTS samples for "okay raspy" (positive examples and tests)
2. Generate ~2k TTS samples for "hey mycroft" (negative examples)
3. Randomly sample 2k WAV files from the [Google Speech Commands Dataset](http://download.tensorflow.org/data/speech_commands_v0.01.tar.gz), with half being negative examples and half being (negative) tests
4. Record 20 actual samples for **testing only**
5. Train model with `bin/train-incremental`, which runs `precise-train` for 1000 epochs, followed by `precise-train-incremental` with [pdsounds](http://pdsounds.tuxfamily.org/) for another 1000 epochs

Training took approximately 15 minutes on an Intel Core i7-8750H with 64GB of RAM.

Final model has a 99.46% summary score and performed quite well in a small live test.

## Improvements

There is a lot of room for improvement:

* More TTS systems, like picoTTS, Festival, Google TTS, etc.
* More voices
* More audio effects to simulate voices in different types of rooms and places in a room
* Other kinds of noise (e.g., TV show)

Research questions:

* How may TTS samples are actually needed (positive, negative, and testing)?
* Can performance be improved by generating negative examples that sound similar (e.g., "okay raspberry")?
* Does selecting specific voices that sound like the intended user help performance?
* What is the best training process and number of epochs? Should incremental training be alternated?
* Could performance be improved by running a keyword spotter at runtime (e.g., Pocketsphinx) and modulating the chunk probability coming out of the Precise engine?

## Dependencies

Assumes you've downloaded the [Public Domain Sounds Backup](http://pdsounds.tuxfamily.org/) and converted them to WAV files as described in [the Mycroft training tutorial](https://github.com/MycroftAI/mycroft-precise/wiki/Training-your-own-wake-word#method-2). They should be in a `pdsounds` directory at the root of the cloned repo.

Docker image should be built as:

```bash
$ docker build . -t synesthesiam/mycroft-precise-trainer
```

The `bin/mycroft-precise-trainer` script will let you execute a command inside the training environment, e.g.:

```bash
$ bin/mycroft-precise-trainer precise-train ...
```

The command is run as your user with your home directory automatically mounted and the working directory set to `$PWD`.
