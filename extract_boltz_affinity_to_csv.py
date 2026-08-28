#!/usr/bin/env python

import json
import csv
import argparse
from pathlib import Path


def parse_args():
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        description="Extract Boltz affinity predictions and export CSV summary.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  boltz_affinity_to_csv.py -job HON-0003050R.yaml

  boltz_affinity_to_csv.py \
      -job HON-0003050R.yaml \
      -o affinity_HON-0003050R.csv
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
        help="Output CSV file (default: affinity_<jobid>.csv)"
    )

    return parser.parse_args()


def round_or_none(value, ndigits=2):
    """Round numeric values while preserving None."""

    if value is None:
        return None

    return round(float(value), ndigits)


def main():

    args = parse_args()

    job_id = Path(args.job).stem

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

    print(f"[INFO] Job ID : {job_id}")
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

        pred_ic50_uM = None
        pred_pic50 = None

        #
        # Boltz definition:
        #
        # affinity_pred_value
        # = log10(IC50 [uM])
        #
        # IC50_uM = 10^y
        # pIC50    = 6 - y
        #

        if affinity_pred is not None:

            pred_ic50_uM = round_or_none(
                10 ** affinity_pred
            )

            pred_pic50 = round_or_none(
                6.0 - affinity_pred
            )

        fields = [
            "JobName",

            "Binder_prob",

            "Pred_log10IC50_uM",
            "Pred_IC50_uM",
            "Pred_pIC50",

            "Pred_log10IC50_uM_Model1",
            "Binder_prob_Model1",

            "Pred_log10IC50_uM_Model2",
            "Binder_prob_Model2",
        ]

        row = {

            "JobName":
                job_id,

            "Binder_prob":
                round_or_none(
                    binder_prob
                ),

            "Pred_log10IC50_uM":
                round_or_none(
                    affinity_pred
                ),

            "Pred_IC50_uM":
                pred_ic50_uM,

            "Pred_pIC50":
                pred_pic50,

            "Pred_log10IC50_uM_Model1":
                round_or_none(
                    data.get(
                        "affinity_pred_value1"
                    )
                ),

            "Binder_prob_Model1":
                round_or_none(
                    data.get(
                        "affinity_probability_binary1"
                    )
                ),

            "Pred_log10IC50_uM_Model2":
                round_or_none(
                    data.get(
                        "affinity_pred_value2"
                    )
                ),

            "Binder_prob_Model2":
                round_or_none(
                    data.get(
                        "affinity_probability_binary2"
                    )
                ),
        }

    except json.JSONDecodeError as e:

        print(
            f"[ERROR] JSON parse error:\n{e}"
        )
        return 1

    except Exception as e:

        print(
            f"[ERROR] Failed to process file:\n{e}"
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

    print(f"[DONE] Wrote CSV: {output_csv}")

    print()
    print("=" * 60)
    print("Boltz Affinity Prediction Summary")
    print("=" * 60)

    print(f"Job Name:       {job_id}")

    if row["Binder_prob"] is not None:
        print(
            f"Binder Prob:    "
            f"{row['Binder_prob']:.2f}"
        )

    if row["Pred_log10IC50_uM"] is not None:

        print(
            f"log10(IC50):    "
            f"{row['Pred_log10IC50_uM']:.2f}"
        )

        print(
            f"IC50 (uM):      "
            f"{row['Pred_IC50_uM']:.2f}"
        )

        print(
            f"pIC50:          "
            f"{row['Pred_pIC50']:.2f}"
        )

    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
