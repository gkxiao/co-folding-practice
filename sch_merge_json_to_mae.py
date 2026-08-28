#!/usr/bin/env python

import os
import sys
import json
import argparse

from schrodinger import structure


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


def main():

    parser = argparse.ArgumentParser(
        description="Merge Boltz confidence JSON into MAE/MAEGZ user properties."
    )

    parser.add_argument(
        "-imae",
        required=True,
        help="Input MAE/MAEGZ file"
    )

    parser.add_argument(
        "-ijson",
        required=True,
        help="Input confidence JSON file"
    )

    parser.add_argument(
        "-omae",
        required=True,
        help="Output MAE/MAEGZ file"
    )

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

    with structure.StructureWriter(args.omae) as writer:

        for st in structure.StructureReader(args.imae):

            for prop_name, prop_value in props.items():
                st.property[prop_name] = prop_value

            writer.append(st)
            n_structures += 1

    print(
        f"Successfully wrote {n_structures} structure(s) to "
        f"'{args.omae}'"
    )
    print(f"Added {len(props)} properties.")


if __name__ == "__main__":
    main()
