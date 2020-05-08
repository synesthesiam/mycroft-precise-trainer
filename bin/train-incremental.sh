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
random_dir='/pdsounds'

cp -R "${input_dir}" "${data_dir}"

epochs='1000'
"${trainer}" precise-train -e "${epochs}" "${model_path}" "${data_dir}"
"${trainer}" precise-test "${model_path}" "${data_dir}" > "${output_dir}/test_results.1.txt"
"${trainer}" precise-convert -o "${output_dir}/${model_name}.1.net" "${model_path}"

"${trainer}" precise-train-incremental \
             --random-data-folder "${random_dir}" \
             -e "${epochs}" \
             "${model_path}" "${data_dir}"

"${trainer}" precise-test "${model_path}" "${data_dir}" > "${output_dir}/test_results.txt"
"${trainer}" precise-convert "${model_path}"

echo 'Done'
