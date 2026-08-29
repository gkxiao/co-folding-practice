#!/usr/bin/env python
"""
纯 RDKit 版本：将 Boltzmann confidence JSON 合并到 MAE/MAEGZ 的用户属性中。
功能等价于 sch_merge_json_to_mae.py，但不依赖 Schrödinger Python API。

用法:
    python RDKit_merge_json_to_mae.py -imae input.mae   -ijson conf.json -omae output.mae
    python RDKit_merge_json_to_mae.py -imae input.maegz -ijson conf.json -omae output.maegz

RDKit 版关键差异:
  - 读入 .maegz 需用 gzip.open(..., "rb")；写出 .maegz 需用 gzip.open(..., "wt")
  - 分子属性按类型用 SetIntProp / SetDoubleProp / SetProp 设置
  - MaeMolSupplier 可能返回 None（解析失败的结构），需跳过
"""
import os
import sys
import json
import gzip
import argparse

from rdkit import Chem
from rdkit.Chem import rdmolfiles


def flatten_dict(d, prefix=""):
    """
    Recursively flatten a nested dictionary.
    Example:
        {"a": {"b": 1}}
    ->
        {"a_b": 1}
    """
    items = {}
    for k, v in d.items():
        key = f"{prefix}_{k}" if prefix else str(k)
        if isinstance(v, dict):
            items.update(flatten_dict(v, key))
        else:
            items[key] = v
    return items


def json_to_maestro_props(json_data):
    """
    Convert JSON fields to Maestro property names.
    """
    flat = flatten_dict(json_data)
    props = {}
    for key, value in flat.items():
        safe_key = (
            str(key)
            .replace(".", "_")
            .replace("-", "_")
        )
        if isinstance(value, bool):
            props[f"i_user_{safe_key}"] = int(value)
        elif isinstance(value, int):
            props[f"i_user_{safe_key}"] = value
        elif isinstance(value, float):
            props[f"r_user_{safe_key}"] = value
        else:
            props[f"s_user_{safe_key}"] = str(value)
    return props


def is_maegz(path):
    return path.endswith((".maegz", ".mae.gz"))


def open_mae_input(path):
    """打开 MAE/MAEGZ 输入，返回二进制流（MaeMolSupplier 需要二进制流）。"""
    if is_maegz(path):
        return gzip.open(path, "rb")
    return open(path, "rb")


def open_mae_output(path):
    """打开 MAE/MAEGZ 输出，返回文本流（MaeWriter 接受 file-like object）。"""
    if is_maegz(path):
        return gzip.open(path, "wt")
    return open(path, "w")


def set_mol_property(mol, name, value):
    """按值类型用正确的 RDKit 方法设置分子属性。"""
    if isinstance(value, bool):
        mol.SetIntProp(name, int(value))
    elif isinstance(value, int):
        mol.SetIntProp(name, value)
    elif isinstance(value, float):
        mol.SetDoubleProp(name, value)
    else:
        mol.SetProp(name, str(value))


def main():
    parser = argparse.ArgumentParser(
        description="Merge Boltzmann confidence JSON into MAE/MAEGZ user properties (RDKit version)."
    )
    parser.add_argument("-imae", required=True, help="Input MAE/MAEGZ file")
    parser.add_argument("-ijson", required=True, help="Input confidence JSON file")
    parser.add_argument("-omae", required=True, help="Output MAE/MAEGZ file")
    args = parser.parse_args()

    # Prevent accidental overwrite
    if os.path.exists(args.omae):
        sys.stderr.write(
            f"ERROR: Output file already exists: {args.omae}\n"
            "Refusing to overwrite existing file.\n"
        )
        sys.exit(1)

    # Read JSON
    with open(args.ijson, "r") as fh:
        json_data = json.load(fh)
    props = json_to_maestro_props(json_data)

    n_structures = 0
    with open_mae_output(args.omae) as out_stream:
        writer = rdmolfiles.MaeWriter(out_stream)
        with open_mae_input(args.imae) as in_stream:
            for st in rdmolfiles.MaeMolSupplier(in_stream):
                if st is None:
                    continue
                for prop_name, prop_value in props.items():
                    set_mol_property(st, prop_name, prop_value)
                writer.write(st)
                n_structures += 1
        writer.close()

    print(f"Successfully wrote {n_structures} structure(s) to '{args.omae}'")
    print(f"Added {len(props)} properties.")


if __name__ == "__main__":
    main()
