FROM ubuntu:eoan

COPY pdsounds /pdsounds

RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
        python3 python3-pip python3-venv python3-dev \
        python3-scipy python3-h5py cython \
        libopenblas-dev libatlas-base-dev portaudio19-dev git \
        build-essential

RUN cd / && \
    git clone https://github.com/mycroftai/mycroft-precise

COPY fake-sudo /usr/bin/sudo

RUN cd /mycroft-precise && \
    ./setup.sh

COPY entry.sh train-from-directory.sh /

ENTRYPOINT ["/entry.sh"]