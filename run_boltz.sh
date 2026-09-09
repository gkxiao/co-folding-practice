#!/bin/bash
# 用法: run_boltz.sh [-m|--use-msa] [-h] <input.yaml>

show_help() {
    cat << EOF
Usage: $0 [OPTIONS] <input.yaml>

Options:
  -m, --use-msa    Add --use_msa_server flag (use external MSA server).
                   Omit this if your YAML file already contains MSA information.
  -h, --help       Show this help message.

Fixed prediction parameters:
  --use_potentials
  --diffusion_samples 10
  --sampling_steps 1500
  --step_scale 1.5      (moderately increases conformational diversity)

Example:
  $0 -m my_input.yaml   # uses MSA server
  $0 my_input.yaml      # skips --use_msa_server (assumes MSA is in YAML)
EOF
}

USE_MSA=""
INPUT=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--use-msa)
            USE_MSA="--use_msa_server"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            echo "Error: Unknown option $1" >&2
            show_help
            exit 1
            ;;
        *)
            INPUT="$1"
            shift
            ;;
    esac
done

# 检查是否提供了输入文件
if [[ -z "$INPUT" ]]; then
    echo "Error: Input YAML file is required." >&2
    show_help
    exit 1
fi

# 构建并执行命令
cmd="boltz predict ${INPUT}"
[[ -n "$USE_MSA" ]] && cmd="$cmd $USE_MSA"
cmd="$cmd --use_potentials --diffusion_samples 10 --sampling_steps 1500 --step_scale 1.5"

eval "$cmd"
