#!/usr/bin/env bash
set -e

if [[ -z "$2" ]]; then
    echo "Usage: train-from-directory.sh MODEL DIR"
    exit 0
fi

model="$1"
model_dir="$(dirname "${model}")"
model_name="$(basename "${model}" .net)"

wav_dir="$2"
: "${epochs=1000}"
: "${epochs_incremental=600}"

echo "Training (1/3)..."
precise-train \
    --epochs "${epochs}" \
    "${model}" "${wav_dir}"

echo "Testing (1/3)..."
precise-test "${model}" "${wav_dir}" > "${model_dir}/${model_name}.test.1.txt"

echo "Converting (1/3)..."
precise-convert --out "${model_dir}/${model_name}.1.pb" "${model}"

echo "Training (2/3, incremental)..."
precise-train-incremental \
    --random-data-folder /pdsounds \
    --epochs "${epochs}" \
    "${model}" "${wav_dir}"

echo "Testing (2/3)..."
precise-test "${model}" "${wav_dir}" > "${model_dir}/${model_name}.test.2.txt"

echo "Converting (2/3)..."
precise-convert --out "${model_dir}/${model_name}.2.pb" "${model}"

echo "Training (3/3)..."
precise-train \
    --epochs "${epochs}" \
    "${model}" "${wav_dir}"

echo "Testing (3/3)..."
precise-test "${model}" "${wav_dir}" > "${model_dir}/${model_name}.test.3.txt"

echo "Converting (3/3)..."
precise-convert "${model}"

echo "Done"
pb_name="$(basename "${model}" .net).pb"
echo "${pb_name} ${pb_name}.params"
