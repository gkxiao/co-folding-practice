#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize all Boltz confidence JSON files for one input into a single CSV,
with a printed confidence summary (model count, system type, recommendation).

Usage:
    python boltz_confidence_summary.py -i ${input}.yaml -o ${input}_boltz_confidence.csv

Given a Boltz input file (e.g. 190-amyr3.yaml), the script locates the standard
Boltz result directory

    boltz_results_<input>/predictions/<input>/

and reads every confidence file inside it:

    confidence_<input>_model_<i>.json      (i = 0, 1, 2, ...)

Each JSON is expanded into one CSV row. The first column is `model`, named
model_0, model_1, ... (matching the file suffix). All scalar metrics
(confidence_score, ptm, iptm, ligand_iptm, protein_iptm, complex_plddt,
complex_iplddt, complex_pde, complex_ipde, ...) become one column each.
Nested objects such as chains_ptm and pair_chains_iptm are flattened into
columns like chains_ptm_0, pair_chains_iptm_0_1, etc. Column names are the
union over all models, so metrics missing from a particular model are left
blank.

Printed summary (after the CSV is written):
  [1] how many models were read;
  [2] system type: monomer vs complex, and protein-ligand vs protein-protein,
      so the right ranking metric is used (Boltz official rule: for single-chain
      inputs pTM drives the confidence ranking; for complexes ipTM / ligand_ipTM
      reflect interface quality);
  [3] per-model key metrics, recommendation of the most trustworthy model(s),
      or a warning when every model is below basic confidence.

Confidence interpretation is based on:
  - Boltz official docs (api.boltz.bio "Core Concepts"): pTM = global fold
    quality, ipTM = interface positioning confidence, protein_iptm / ligand_iptm
    restrict to protein-protein / protein-ligand interfaces, pLDDT = local
    confidence, PDE = predicted distance error in Angstrom (lower is better);
    confidence_score is a composite used to order the samples (model_0 is the
    default top-ranked sample).
  - Community-convention bands (AF2/AF3/Boltz usage, NOT hard Boltz cutoffs):
    pLDDT >= 0.9 very high / 0.7-0.9 high / 0.5-0.7 moderate / <0.5 low;
    pTM >= 0.7 high; ipTM & ligand_ipTM >= 0.8 high-confidence interface.

Chain-type detection order (only used for the summary, never for the CSV):
    1. input YAML "sequences" block (explicit protein/ligand/rna/dna/cc entries,
       parsed with a minimal dependency-free scanner);
    2. <result>/../processed/records/<input>.json "chains"[].mol_type
       (0=protein, 1=rna, 2=dna, 3=ligand; 0/3 verified against real data);
    3. number of chains from the confidence JSON (chains_ptm keys) only.

Result directory lookup order:
    1. --result-dir, if given
    2. <cwd>/boltz_results_<input>/predictions/<input>/
    3. <same dir as the yaml>/boltz_results_<input>/predictions/<input>/
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------
# Community-convention confidence bands (see module docstring for provenance).
# --------------------------------------------------------------------------
MOL_TYPE_NAMES = {0: "protein", 1: "rna", 2: "dna", 3: "ligand"}


def find_confidence_files(result_dir: Path, input_name: str) -> List[Tuple[int, Path]]:
    """Find confidence_<input>_model_<i>.json files, sorted by model index i."""
    pattern = re.compile(rf"^confidence_{re.escape(input_name)}_model_(\d+)\.json$")
    hits: List[Tuple[int, Path]] = []
    for path in result_dir.iterdir():
        if path.is_file():
            m = pattern.match(path.name)
            if m:
                hits.append((int(m.group(1)), path))
    hits.sort(key=lambda item: item[0])
    return hits


def flatten(obj, prefix: str = "", sep: str = "_") -> dict:
    """Recursively flatten a nested dict into flat keys.

    Example: {"chains_ptm": {"0": 0.8}} -> {"chains_ptm_0": 0.8}
    """
    flat = {}
    for key, value in obj.items():
        full_key = f"{prefix}{sep}{key}" if prefix else str(key)
        if isinstance(value, dict):
            flat.update(flatten(value, full_key, sep))
        else:
            flat[full_key] = value
    return flat


def locate_result_dir(input_yaml: Path, input_name: str,
                      explicit: Optional[Path]) -> Optional[Path]:
    if explicit is not None:
        return explicit if explicit.is_dir() else None
    rel = Path("boltz_results_" + input_name) / "predictions" / input_name
    for base in (Path.cwd(), input_yaml.resolve().parent):
        cand = base / rel
        if cand.is_dir():
            return cand
    return None


# --------------------------------------------------------------------------
# Summary helpers: chain-type detection, band labels, recommendation.
# --------------------------------------------------------------------------
def read_input_sequences(input_yaml: Path) -> Optional[Dict[str, int]]:
    """Minimal dependency-free scan of the Boltz input YAML 'sequences' block.

    Boltz input files use a fixed structure::

        sequences:
          - protein:
              id: A
              sequence: ...
          - ligand:
              id: B
              smiles: ...

    Only the entry markers are detected, so no full YAML parser is needed.
    Returns None if the file cannot be read or no 'sequences' entry is found.
    """
    kind_keys = ("protein", "ligand", "rna", "dna", "cc")
    counts = {k: 0 for k in kind_keys}
    try:
        with open(input_yaml, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return None
    in_sequences = False
    found = False
    for line in lines:
        stripped = line.strip()
        if stripped == "sequences:":
            in_sequences = True
            continue
        if in_sequences:
            # A top-level (unindented, non-comment) line closes the block.
            if stripped and not stripped.startswith("#") and not line[:1].isspace():
                break
            for kind in kind_keys:
                if stripped.startswith(f"- {kind}:") or stripped.startswith(f"- {kind} :"):
                    counts[kind] += 1
                    found = True
                    break
    return counts if found else None


def read_records_types(result_dir: Path, input_name: str) -> Optional[Dict[str, int]]:
    """Fallback: read chain molecule types from processed/records/<input>.json."""
    records_path = result_dir.parent.parent / "processed" / "records" / f"{input_name}.json"
    try:
        with open(records_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    counts: Dict[str, int] = {v: 0 for v in MOL_TYPE_NAMES.values()}
    counts["unknown"] = 0
    for chain in data.get("chains", []):
        name = MOL_TYPE_NAMES.get(chain.get("mol_type"), "unknown")
        counts[name] += 1
    return counts


def classify_system(input_yaml: Path, result_dir: Path, input_name: str,
                    n_chains: int) -> Dict[str, object]:
    """Decide monomer vs complex and whether a ligand is present.

    Returns a dict with 'label', 'counts', 'source' and boolean flags.
    """
    counts = read_input_sequences(input_yaml)
    source = "input yaml (sequences)"
    if counts is None:
        counts = read_records_types(result_dir, input_name)
        source = "boltz processed/records (mol_type)"
    if counts is None:
        counts = {"protein": 0, "ligand": 0, "rna": 0, "dna": 0, "cc": 0, "unknown": n_chains}
        source = "confidence JSON chain count only"

    n_protein = counts.get("protein", 0)
    n_ligand = counts.get("ligand", 0)
    n_rna = counts.get("rna", 0)
    n_dna = counts.get("dna", 0)
    n_unknown = counts.get("unknown", 0)

    if n_chains == 1:
        label = "单体 (monomer)"
    elif n_ligand > 0 and n_protein > 0:
        label = "蛋白-配体复合物 (protein-ligand complex)"
    elif n_ligand > 0:
        label = "含配体的多链复合物 (complex with ligand)"
    elif n_protein > 1 or (n_protein + n_rna + n_dna) > 1:
        label = "蛋白(或核酸)复合物 (multi-chain complex)"
    elif n_unknown >= 2:
        label = "多链复合物 (multi-chain complex)"
    else:
        label = "单体 (monomer)"

    detail = f"{n_chains} 条链"
    if n_protein:
        detail += f"，蛋白 {n_protein}"
    if n_ligand:
        detail += f"，配体 {n_ligand}"
    if n_rna:
        detail += f"，RNA {n_rna}"
    if n_dna:
        detail += f"，DNA {n_dna}"
    if n_unknown:
        detail += f"，未知类型 {n_unknown}"

    return {
        "label": label,
        "detail": detail,
        "source": source,
        "is_monomer": n_chains == 1,
        "has_ligand": n_ligand > 0,
    }


def metric_band(metric: str, value: float) -> str:
    """Community-convention band label for one Boltz confidence metric."""
    if metric == "complex_plddt":
        if value >= 0.9:
            return "非常高"
        if value >= 0.7:
            return "高"
        if value >= 0.5:
            return "中等"
        return "低"
    if metric == "ptm":
        if value >= 0.7:
            return "高"
        if value >= 0.5:
            return "中等"
        return "低"
    if metric in ("iptm", "ligand_iptm", "protein_iptm"):
        if value >= 0.8:
            return "高"
        if value >= 0.5:
            return "中等"
        return "低"
    return ""


def print_summary(input_yaml: Path, input_name: str, result_dir: Path, out_path: Path,
                  rows: List[Tuple[str, dict]], n_chains: int) -> None:
    """Print the summary: model count, system type, metrics, recommendation."""
    print("\n=== Boltz 置信度总结 ===")
    print(f"输入文件    : {input_yaml}")
    print(f"结果目录    : {result_dir}")
    print(f"输出 CSV    : {out_path}")

    # [1] model count
    first_idx, last_idx = rows[0][0].rsplit("_", 1)[1], rows[-1][0].rsplit("_", 1)[1]
    print(f"\n[1] 读取模型数 : {len(rows)} 个 (model_{first_idx} ~ model_{last_idx})")

    # [2] system type
    sysinfo = classify_system(input_yaml, result_dir, input_name, n_chains)
    print(f"\n[2] 系统类型   : {sysinfo['label']}")
    print(f"    链组成     : {sysinfo['detail']}")
    print(f"    判定依据   : {sysinfo['source']}")

    # [3] key metrics table
    primary_key = "ptm" if sysinfo["is_monomer"] else ("ligand_iptm" if sysinfo["has_ligand"] else "iptm")
    primary_desc = {
        "ptm": "全局折叠质量 (pTM)",
        "ligand_iptm": "蛋白-配体界面质量 (ligand_iptm)",
        "iptm": "界面质量 (iptm)",
    }[primary_key]
    by_conf = max(rows, key=lambda t: t[1].get("confidence_score", 0.0))
    by_primary = max(rows, key=lambda t: t[1].get(primary_key, 0.0))
    rec_labels = {by_conf[0]: "综合最高", by_primary[0]: primary_desc}

    show_cols = ["model", "confidence_score", "ptm", "iptm", "ligand_iptm", "complex_plddt"]
    widths = {"model": 10, "confidence_score": 17, "ptm": 9, "iptm": 9,
              "ligand_iptm": 13, "complex_plddt": 14}
    print("\n[3] 关键指标概览（Boltz 官方规则：复合物看界面指标 iptm/ligand_iptm，"
          "pTM 仅对单体主导排序；* 为推荐候选）:")
    header = "".join(c.ljust(widths[c]) for c in show_cols) + "  备注"
    print(header)
    for label, flat in rows:
        vals = []
        for c in show_cols[1:]:
            v = flat.get(c)
            vals.append(f"{v:.3f}".ljust(widths[c]) if isinstance(v, (int, float)) else "—".ljust(widths[c]))
        note = rec_labels.get(label, "")
        star = " *" if note else ""
        print(f"{label:<10}" + "".join(vals) + f"  {note}{star}")

    # [4] interpretation and recommendation
    print("\n[4] 置信度解读与推荐")
    if sysinfo["is_monomer"]:
        print("    · 判定规则：单链输入时 Boltz 以 pTM（而非 ipTM）主导置信度排序；"
              "confidence_score 为综合排序键。")
    else:
        print("    · 判定规则：复合物重点看界面指标 iptm/ligand_iptm"
              + ("（蛋白-配体复合物尤以 ligand_iptm 反映结合模式质量）。" if sysinfo["has_ligand"] else "（蛋白复合物界面）。")
              + " pTM 反映全局折叠，pLDDT 反映局部置信度，pDE/ipDE（Å）越低越好。")

    # trust verdict
    prim_vals = [flat.get(primary_key) for _, flat in rows]
    prim_vals = [v for v in prim_vals if isinstance(v, (int, float))]
    plddt_vals = [flat.get("complex_plddt") for _, flat in rows]
    plddt_vals = [v for v in plddt_vals if isinstance(v, (int, float))]
    all_low_prim = bool(prim_vals) and all(v < 0.5 for v in prim_vals)
    all_low_plddt = bool(plddt_vals) and all(v < 0.5 for v in plddt_vals)
    if all_low_prim or all_low_plddt:
        print(f"    · ⚠ 警告：所有模型的 {primary_desc} 均低于 0.5"
              + ("，且 complex_plddt 均低于 0.5" if all_low_plddt else "")
              + "，整体置信度不足，建议仅作为假设性结果，谨慎用于下游分析。")
    else:
        if prim_vals:
            lo, hi = min(prim_vals), max(prim_vals)
            print(f"    · 关键指标分带（社区惯例阈值，非 Boltz 官方硬性截断）："
                  f"{primary_desc} {lo:.3f}–{hi:.3f}"
                  f"（{'高' if hi >= (0.8 if primary_key != 'ptm' else 0.7) else '中等'}置信区间）")
        if plddt_vals:
            lo, hi = min(plddt_vals), max(plddt_vals)
            print(f"      complex_plddt {lo:.3f}–{hi:.3f}，处于"
                  f"{'高/非常高' if hi >= 0.7 else ('中等' if hi >= 0.5 else '低')}分带。")
        print(f"    · 综合置信度最高 : {by_conf[0]} (confidence_score {by_conf[1].get('confidence_score', 0):.3f})"
              f"  <- Boltz 默认排序第 1")
        print(f"    · 关键指标最高   : {by_primary[0]} ({primary_key} {by_primary[1].get(primary_key, 0):.3f})"
              f"  <- 按{primary_desc}优先")
        if by_conf[0] == by_primary[0]:
            print(f"    · 结论 : 推荐模型 {by_conf[0]}（综合与关键指标一致），整体可信。")
        else:
            print(f"    · 结论 : 整体可信。若需全局最优，推荐 {by_conf[0]}；"
                  f"若更关注{primary_desc}，推荐 {by_primary[0]}。")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize Boltz confidence JSON files into a CSV table, "
                    "with a printed confidence summary."
    )
    parser.add_argument("-i", "--input", required=True,
                        help="Boltz input YAML file, e.g. 190-amyr3.yaml")
    parser.add_argument("-o", "--output",
                        help="Output CSV path (default: <input>_boltz_confidence.csv)")
    parser.add_argument("--result-dir",
                        help="Boltz result directory to scan (default: auto-detect "
                             "boltz_results_<input>/predictions/<input>/)")
    parser.add_argument("--quiet", action="store_true",
                        help="Skip the printed confidence summary")
    args = parser.parse_args()

    input_yaml = Path(args.input)
    if not input_yaml.is_file():
        print(f"ERROR: input file not found: {input_yaml}", file=sys.stderr)
        return 1

    input_name = input_yaml.stem
    result_dir = locate_result_dir(input_yaml, input_name,
                                   Path(args.result_dir) if args.result_dir else None)
    if result_dir is None:
        print(f"ERROR: result directory not found: "
              f"boltz_results_{input_name}/predictions/{input_name}/", file=sys.stderr)
        print("Run Boltz first, or pass --result-dir explicitly.", file=sys.stderr)
        return 1

    conf_files = find_confidence_files(result_dir, input_name)
    if not conf_files:
        print(f"ERROR: no confidence_{input_name}_model_*.json found in {result_dir}",
              file=sys.stderr)
        return 1

    rows: List[Tuple[str, dict]] = []
    columns: List[str] = []
    seen = set()
    n_chains: Optional[int] = None
    for idx, path in conf_files:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERROR: failed to read {path}: {exc}", file=sys.stderr)
            return 1
        if not isinstance(data, dict):
            print(f"ERROR: {path} does not contain a JSON object", file=sys.stderr)
            return 1
        if n_chains is None:
            chains_ptm = data.get("chains_ptm")
            n_chains = len(chains_ptm) if isinstance(chains_ptm, dict) else 1
        flat = flatten(data)
        for key in flat:
            if key not in seen:
                seen.add(key)
                columns.append(key)
        rows.append((f"model_{idx}", flat))

    out_path = Path(args.output) if args.output else Path(f"{input_name}_boltz_confidence.csv")
    try:
        # utf-8-sig so Excel opens the file without mojibake; newline="" avoids
        # stray blank lines from csv.writer on Windows.
        with open(out_path, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["model"] + columns)
            for label, flat in rows:
                writer.writerow([label] + [flat.get(col, "") for col in columns])
    except OSError as exc:
        print(f"ERROR: failed to write {out_path}: {exc}", file=sys.stderr)
        return 1

    print(f"OK: {len(rows)} models x {len(columns)} metrics -> {out_path}")
    if not args.quiet:
        print_summary(input_yaml, input_name, result_dir, out_path, rows, n_chains or 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
