#!/usr/bin/env python
"""打印 .mae/.maegz 文件的 title 与非内置属性（独立 RDKit 实现，无需 Schrödinger）。

用法:
    python rdkit_print_mae_prop.py <input.mae|input.maegz>

说明:
    - Maestro 的 s_m_title 在 RDKit 中映射为分子属性 "_Name"
    - .maegz/.mae.gz 为 gzip 压缩，必须用 gzip.open() 传给 MaeMolSupplier
    - 属性值一律为字符串
"""
import gzip
import sys

from rdkit.Chem import rdmolfiles


def is_builtin_property(prop_name):
    """Filter Maestro built-in properties."""
    return prop_name.startswith((
        "s_m_", "i_m_", "r_m_", "b_m_",
        "s_sd_", "i_sd_", "r_sd_", "b_sd_"
    ))


def open_mae_stream(path):
    """按扩展名打开输入文件，.maegz/.mae.gz 自动解压，返回二进制流。"""
    if path.endswith((".maegz", ".mae.gz")):
        return gzip.open(path, "rb")
    return open(path, "rb")


def main():
    if len(sys.argv) != 2:
        sys.stderr.write(
            f"Usage: {sys.argv[0]} <input.mae|input.maegz>\n"
        )
        sys.exit(1)

    infile = sys.argv[1]
    try:
        with open_mae_stream(infile) as stream:
            suppl = rdmolfiles.MaeMolSupplier(stream)
            st = next(suppl)  # 第一个结构（与原 Schrödinger 脚本一致）
    except StopIteration:
        sys.stderr.write(f"ERROR: no structures found in {infile}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)

    # Maestro 的 s_m_title 在 RDKit 中映射为 "_Name"
    title = st.GetProp("_Name") if st.HasProp("_Name") else ""
    print(f"title={title}")

    for key in sorted(st.GetPropNames()):
        if key == "_Name":
            continue  # 已在 title= 中打印
        if is_builtin_property(key):
            continue
        print(f"{key}={st.GetProp(key)}")


if __name__ == "__main__":
    main()
