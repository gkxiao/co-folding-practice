#!/bin/bash

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <input.yaml>"
    exit 1
fi

yaml_file="$1"

if [ ! -f "$yaml_file" ]; then
    echo "ERROR: YAML file not found: $yaml_file"
    exit 1
fi

input=$(basename "$yaml_file" .yaml)

pred_dir="boltz_results_${input}/predictions/${input}"

if [ ! -d "$pred_dir" ]; then
    echo "ERROR: Prediction directory not found:"
    echo "  $pred_dir"
    exit 1
fi

for mae in "${pred_dir}"/model_*.maegz
do
    [ -e "$mae" ] || continue

    model_id=$(basename "$mae" .maegz)
    model_id=${model_id#model_}

    json="${pred_dir}/confidence_${input}_model_${model_id}.json"
    out_mae="${pred_dir}/model_${model_id}_with_confidence.maegz"

    if [ ! -f "$json" ]; then
        echo "WARNING: Missing JSON file:"
        echo "  $json"
        continue
    fi

    echo "Processing model_${model_id} ..."

    $boltz_tools/merge_json_to_mae.py \
        -imae "$mae" \
        -ijson "$json" \
        -omae "$out_mae"

done

echo "Done."
