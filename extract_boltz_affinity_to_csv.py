#!/usr/bin/env python

import os
import json
import csv
import argparse
from pathlib import Path


def parse_args():
    """解析命令行参数"""

    parser = argparse.ArgumentParser(
        description="从Boltz预测结果中提取Affinity指标并汇总为CSV文件",
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
    """从YAML文件名提取Job ID"""

    basename = os.path.basename(yaml_file)
    return basename.replace(".yaml", "")


def round_or_none(value, ndigits=2):
    """保留指定小数位"""

    if value is None:
        return None

    return round(value, ndigits)


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
        "affinity_probability_binary2",
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

        with open(affinity_file, "r") as fp:
            data = json.load(fp)

        affinity_pred_value = data.get(
            "affinity_pred_value"
        )

        predicted_ic50_uM = None
        predicted_pic50 = None
        predicted_dg = None

        if affinity_pred_value is not None:

            #
            # Boltz定义：
            # affinity_pred_value = log10(IC50 [uM])
            #

            predicted_ic50_uM = round_or_none(
                10 ** affinity_pred_value
            )

            predicted_pic50 = round_or_none(
                6.0 - affinity_pred_value
            )

            predicted_dg = round_or_none(
                (6.0 - affinity_pred_value) * 1.364
            )

        row = {
            "JobName":
                job_id,

            "affinity_probability_binary":
                round_or_none(
                    data.get("affinity_probability_binary")
                ),

            "affinity_pred_value":
                round_or_none(
                    data.get("affinity_pred_value")
                ),

            "Predicted_IC50_uM":
                predicted_ic50_uM,

            "Predicted_pIC50":
                predicted_pic50,

            "Predicted_dG_kcal_mol":
                predicted_dg,

            "affinity_pred_value1":
                round_or_none(
                    data.get("affinity_pred_value1")
                ),

            "affinity_probability_binary1":
                round_or_none(
                    data.get("affinity_probability_binary1")
                ),

            "affinity_pred_value2":
                round_or_none(
                    data.get("affinity_pred_value2")
                ),

            "affinity_probability_binary2":
                round_or_none(
                    data.get("affinity_probability_binary2")
                ),
        }

        print(
            f"[OK] 已处理: {affinity_file.name}"
        )

    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON解析失败: {e}")
        return 1

    except Exception as e:
        print(f"[ERROR] 处理失败: {e}")
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

    print()
    print("=" * 60)
    print("Affinity Prediction Summary")
    print("=" * 60)

    print(f"Job Name:             {job_id}")

    if row["affinity_pred_value"] is not None:
        print(
            f"Affinity Pred Value:  "
            f"{row['affinity_pred_value']:.2f}"
        )

    if row["Predicted_IC50_uM"] is not None:
        print(
            f"Predicted IC50 (uM):  "
            f"{row['Predicted_IC50_uM']:.2f}"
        )

    if row["Predicted_pIC50"] is not None:
        print(
            f"Predicted pIC50:      "
            f"{row['Predicted_pIC50']:.2f}"
        )

    if row["Predicted_dG_kcal_mol"] is not None:
        print(
            f"Predicted dG:         "
            f"{row['Predicted_dG_kcal_mol']:.2f} kcal/mol"
        )

    if row["affinity_probability_binary"] is not None:
        print(
            f"Binder Probability:   "
            f"{row['affinity_probability_binary']:.2f}"
        )

    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
