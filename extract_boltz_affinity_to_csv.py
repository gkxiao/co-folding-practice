#!/usr/bin/env python

import os
import json
import csv
import argparse
from pathlib import Path


def parse_args():
    """解析命令行参数"""

    parser = argparse.ArgumentParser(
        description="Extract Boltz affinity predictions and export CSV summary.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -job HON-0003050R.yaml
  %(prog)s -job HON-0003050R.yaml -o affinity.csv
"""
    )

    parser.add_argument(
        "-job",
        "--job",
        required=True,
        help="Boltz job YAML file"
    )

    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output CSV file"
    )

    return parser.parse_args()


def extract_job_id(yaml_file):
    """从yaml文件名提取job id"""

    return Path(yaml_file).stem


def round_or_none(value, ndigits=2):
    """保留小数位"""

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

    pred_dir = Path(
        f"boltz_results_{job_id}/predictions/{job_id}"
    )

    if not pred_dir.exists():
        print(
            f"[ERROR] Prediction directory not found:\n"
            f"        {pred_dir}"
        )
        return 1

    affinity_file = pred_dir / f"affinity_{job_id}.json"

    if not affinity_file.exists():
        print(
            f"[ERROR] Affinity file not found:\n"
            f"        {affinity_file}"
        )
        print(
            "[INFO] Affinity prediction may not have been enabled."
        )
        return 1

    print(f"[INFO] Job ID: {job_id}")
    print(f"[INFO] Reading: {affinity_file}")

    try:

        with open(affinity_file, "r") as fp:
            data = json.load(fp)

        affinity_pred = data.get(
            "affinity_pred_value"
        )

        binder_prob = data.get(
            "affinity_probability_binary"
        )

        predicted_ic50_uM = None
        predicted_pic50 = None

        if affinity_pred is not None:

            #
            # Boltz definition:
            #
            # affinity_pred_value
            # = log10(IC50 [uM])
            #

            predicted_ic50_uM = round_or_none(
                10 ** affinity_pred
            )

            predicted_pic50 = round_or_none(
                6.0 - affinity_pred
            )

        fields = [
            "JobName",

            "Binder_Probability",

            "Predicted_log10IC50_uM",
            "Predicted_IC50_uM",
            "Predicted_pIC50",

            "affinity_pred_value1",
            "affinity_probability_binary1",

            "affinity_pred_value2",
            "affinity_probability_binary2",
        ]

        row = {

            "JobName":
                job_id,

            "Binder_Probability":
                round_or_none(binder_prob),

            "Predicted_log10IC50_uM":
                round_or_none(affinity_pred),

            "Predicted_IC50_uM":
                predicted_ic50_uM,

            "Predicted_pIC50":
                predicted_pic50,

            "affinity_pred_value1":
                round_or_none(
                    data.get("affinity_pred_value1")
                ),

            "affinity_probability_binary1":
                round_or_none(
                    data.get(
                        "affinity_probability_binary1"
                    )
                ),

            "affinity_pred_value2":
                round_or_none(
                    data.get("affinity_pred_value2")
                ),

            "affinity_probability_binary2":
                round_or_none(
                    data.get(
                        "affinity_probability_binary2"
                    )
                )
        }

    except json.JSONDecodeError as e:

        print(f"[ERROR] JSON parse error: {e}")
        return 1

    except Exception as e:

        print(f"[ERROR] Failed to process file: {e}")
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

    print(f"[DONE] Wrote CSV: {output_csv}")

    print()
    print("=" * 60)
    print("Boltz Affinity Prediction Summary")
    print("=" * 60)

    print(f"Job Name:                {job_id}")

    if binder_prob is not None:
        print(
            f"Binder Probability:      "
            f"{row['Binder_Probability']:.2f}"
        )

    if affinity_pred is not None:
        print(
            f"Predicted log10(IC50):   "
            f"{row['Predicted_log10IC50_uM']:.2f}"
        )

        print(
            f"Predicted IC50 (uM):     "
            f"{row['Predicted_IC50_uM']:.2f}"
        )

        print(
            f"Predicted pIC50:         "
            f"{row['Predicted_pIC50']:.2f}"
        )

    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
