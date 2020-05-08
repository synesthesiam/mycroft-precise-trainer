#!/usr/bin/env bash
set -e

if [[ -z "$2" ]]; then
    echo "Usage: train-simple input_dir/ output_dir/"
    exit 1
fi

input_dir="$1"
output_dir="$2"

this_dir="$( cd "$( dirname "$0" )" && pwd )"
src_dir="$(realpath "${this_dir}/..")"
trainer="${src_dir}/bin/mycroft-precise-trainer.sh"

# -----------------------------------------------------------------------------

rm -rf "${output_dir}"
mkdir -p "${output_dir}"

model_name='model'
model_path="${output_dir}/${model_name}.net"
data_dir="${output_dir}/data"

cp -R "${input_dir}" "${data_dir}"

epochs='1000'
"${trainer}" precise-train -e "${epochs}" "${model_path}" "${data_dir}"
"${trainer}" precise-test "${model_path}" "${data_dir}" > "${output_dir}/test_results.txt"
"${trainer}" precise-convert "${model_path}"

echo 'Done'
