import os
import subprocess
import time
from timeit import default_timer as timer


def run(repos, folder):

    env = os.environ.copy()

    print(f"Processing {folder}")

    for r in repos:

        print(f"Working with {r}")
        start = timer()

        cmd = [
            "poetry",
            "run",
            "osa-tool",
            "-r",
            r,
            # "--api",
            # "openai",
            # "--base-url",
            # "https://openrouter.ai/api/v1",
            # "--model",
            # "gpt-4.1",
            "--no-fork",
            "--no-pull-request",
            "--output",
            f"/home/ilya/OSA/{folder}__OSA_qwq_32b",
            "-m",
            "basic",
            "--web-mode"
        ]

        process = subprocess.run(
            cmd,
            text=True,
            env=env,
            universal_newlines=True,
            capture_output=True
        )

        with open("logs.txt", "a") as f:
            f.write(f"{folder}\n")
            f.write(f"{r}\n")
            f.write("\n")
            f.write(process.stdout[-25000:])
            f.write("\n")
            f.write("\n")
            f.write("\n")

        end = timer()
        total = (end - start)/60

        print(f"Elapsed time: {total}")
        print(f"{r}\t{total}")

    print("Waiting 5 minutes...")
    time.sleep(60 * 5)
    print()


if __name__ == "__main__":
    repos = [
        # "https://github.com/psf/requests",
        "https://github.com/pallets/flask",
        "https://github.com/mwaskom/seaborn",
        "https://github.com/matplotlib/matplotlib",
        "https://github.com/paul-gauthier/aider",
    ]
    run(repos, "popular_1")

    # repos = [
    #     "https://github.com/sphinx-doc/sphinx",
    #     "https://github.com/pydicom/pydicom",
    #     "https://github.com/marshmallow-code/marshmallow",
    #     "https://github.com/conan-io/conan",
    #     "https://github.com/pylint-dev/pylint",
    # ]
    # run(repos, "popular_2")

    # repos = [
    #     "https://github.com/BMPixel/moffee",
    #     "https://github.com/JuanBindez/pytubefix",
    #     "https://github.com/nasa-jpl/rosa",
    #     "https://github.com/pvlib/pvlib-python",
    # ]
    # run(repos, "popular_3")
