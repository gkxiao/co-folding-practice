#!/usr/bin/env python

import os
import json
import csv
import argparse
from pathlib import Path


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="从Boltz预测结果中提取affinity指标并汇总为CSV文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s -job HON-0003050R.yaml -o affinity_HON-0003050R.csv
  %(prog)s -job my_protein.yaml
  %(prog)s -job path/to/job.yaml -o results/affinity_summary.csv
        """
    )

    parser.add_argument(
        "-job",
        "--job",
        required=True,
        help="Boltz作业文件 (例如: HON-0003050R.yaml)"
    )

    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="输出CSV文件名 (默认: affinity_<job_id>.csv)"
    )

    return parser.parse_args()


def extract_job_id(yaml_file: str) -> str:
    """从YAML文件名提取job ID"""
    basename = os.path.basename(yaml_file)
    return basename.replace(".yaml", "")


def main():
    args = parse_args()

    job_id = extract_job_id(args.job)

    output_csv = (
        args.output
        if args.output
        else f"affinity_{job_id}.csv"
    )

    fields = [
        "JobName",

        "affinity_probability_binary",

        "affinity_pred_value",

        "Predicted_IC50_uM",
        "Predicted_pIC50",
        "Predicted_dG_kcal_mol",

        "affinity_pred_value1",
        "affinity_probability_binary1",

        "affinity_pred_value2",
        "affinity_probability_binary2"
    ]

    pred_dir = Path(
        f"boltz_results_{job_id}/predictions/{job_id}"
    )

    if not pred_dir.exists():
        print(f"[ERROR] 预测结果目录不存在: {pred_dir}")
        return 1

    print(f"[INFO] Job ID: {job_id}")
    print(f"[INFO] 读取目录: {pred_dir}")

    affinity_file = pred_dir / f"affinity_{job_id}.json"

    if not affinity_file.exists():
        print(f"[ERROR] 亲和力文件不存在: {affinity_file}")
        print("[INFO] 可能该作业未启用亲和力预测")
        return 1

    print(f"[INFO] 读取文件: {affinity_file}")

    try:
        with open(affinity_file) as fp:
            data = json.load(fp)

        affinity_pred_value = data.get(
            "affinity_pred_value"
        )

        predicted_ic50_uM = None
        predicted_pic50 = None
        predicted_dg = None

        if affinity_pred_value is not None:

            # Boltz:
            # y = log10(IC50 [uM])

            predicted_ic50_uM = (
                10 ** affinity_pred_value
            )

            predicted_pic50 = (
                6.0 - affinity_pred_value
            )

            predicted_dg = (
                predicted_pic50 * 1.364
            )

        row = {
            "JobName":
                job_id,

            "affinity_probability_binary":
                data.get(
                    "affinity_probability_binary"
                ),

            "affinity_pred_value":
                affinity_pred_value,

            "Predicted_IC50_uM":
                predicted_ic50_uM,

            "Predicted_pIC50":
                predicted_pic50,

            "Predicted_dG_kcal_mol":
                predicted_dg,

            "affinity_pred_value1":
                data.get(
                    "affinity_pred_value1"
                ),

            "affinity_probability_binary1":
                data.get(
                    "affinity_probability_binary1"
                ),

            "affinity_pred_value2":
                data.get(
                    "affinity_pred_value2"
                ),

            "affinity_probability_binary2":
                data.get(
                    "affinity_probability_binary2"
                )
        }

        print(
            f"[OK  ] 已处理: {affinity_file.name}"
        )

    except json.JSONDecodeError as e:
        print(
            f"[ERROR] JSON解析失败 "
            f"{affinity_file}: {e}"
        )
        return 1

    except Exception as e:
        print(
            f"[ERROR] 处理失败 "
            f"{affinity_file}: {e}"
        )
        return 1

    with open(
        output_csv,
        "w",
        newline=""
    ) as fout:

        writer = csv.DictWriter(
            fout,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerow(row)

    print(f"[DONE] 已写入到 {output_csv}")

    print("\n" + "=" * 60)
    print("Affinity Prediction Summary")
    print("=" * 60)

    print(f"Job Name:             {job_id}")

    if affinity_pred_value is not None:
        print(
            f"Affinity Pred Value:  "
            f"{affinity_pred_value:.4f}"
        )

    if predicted_ic50_uM is not None:
        print(
            f"Predicted IC50 (uM):  "
            f"{predicted_ic50_uM:.4f}"
        )

    if predicted_pic50 is not None:
        print(
            f"Predicted pIC50:      "
            f"{predicted_pic50:.4f}"
        )

    if predicted_dg is not None:
        print(
            f"Predicted dG:         "
            f"{predicted_dg:.4f} kcal/mol"
        )

    prob = data.get(
        "affinity_probability_binary"
    )

    if prob is not None:
        print(
            f"Binder Probability:   "
            f"{prob:.4f}"
        )

    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
