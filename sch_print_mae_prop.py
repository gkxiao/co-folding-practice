#/usr/bin/env python
import sys
from schrodinger import structure


def is_builtin_property(prop_name):
    """
    Filter Maestro built-in properties.
    """
    return prop_name.startswith((
        "s_m_", "i_m_", "r_m_", "b_m_",
        "s_sd_", "i_sd_", "r_sd_", "b_sd_"
    ))


def main():
    if len(sys.argv) != 2:
        sys.stderr.write(
            f"Usage: {sys.argv[0]} <input.maegz>\n"
        )
        sys.exit(1)

    infile = sys.argv[1]

    try:
        with structure.StructureReader(infile) as reader:
            st = next(reader)
    except StopIteration:
        sys.stderr.write(f"ERROR: no structures found in {infile}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)

    title = st.title or ""

    print(f"title={title}")

    for key in sorted(st.property.keys()):
        if is_builtin_property(key):
            continue

        value = st.property[key]
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
