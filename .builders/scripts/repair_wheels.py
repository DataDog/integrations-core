import argparse
import glob
import os
import os.path
import shutil
import sys


def repair_linux(source_dir, output_dir, exclude):
    from auditwheel.patcher import Patchelf
    from auditwheel.policy import get_policy_by_name
    from auditwheel.repair import repair_wheel
    from auditwheel.wheel_abi import NonPlatformWheel

    # Hardcoded policy to the minimum we need to currently support
    policy = get_policy_by_name("manylinux2010_x86_64")
    abis = [policy["name"]] + policy["aliases"]

    os.makedirs(output_dir, exist_ok=True)
    for whl in glob.glob(os.path.join(source_dir, '*.whl')):
        try:
            out_wheel = repair_wheel(
                whl,
                abis=abis,
                lib_sdir=".libs",
                out_dir=output_dir,
                update_tags=True,
                patcher=Patchelf(),
                exclude=exclude,
            )
        except NonPlatformWheel:
            out_wheel = shutil.copy(whl, output_dir)
            print("Non-platform wheel copied without repair to", out_wheel)
            continue

        if out_wheel is not None:
            print("Fixed-up wheel written to", out_wheel)


REPAIR_FUNCTIONS = {
    'linux': repair_linux,
}


def main():
    if sys.platform in REPAIR_FUNCTIONS:
        argparser = argparse.ArgumentParser(
            description="Repair wheels found in a directory with the platform-specific tool"
        )
        argparser.add_argument("--source-dir", required=True)
        argparser.add_argument("--output-dir", required=True)
        argparser.add_argument("--exclude", action="append", default=[])
        args = argparser.parse_args()
        REPAIR_FUNCTIONS[sys.platform](args.source_dir, args.output_dir, args.exclude)
    else:
        print(f"Repair not implemented for platform '{sys.platform}'")
        sys.exit(1)


if __name__ == '__main__':
    main()
