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
            "--api",
            "openai",
            "--base-url",
            # "https://openrouter.ai/api/v1",
            "https://foundation-models.api.cloud.ru/v1",
            "--model",
            # "gpt-4.1",
            "meta-llama/Llama-3.3-70B-Instruct",
            "--no-fork",
            "--no-pull-request",
            "--output",
            f"/home/ilya/OSA/{folder}__OSA_Llama_3.3_70B_Instruct",
            "-m",
            "basic",
            "--web-mode",
        ]

        with open("logs.txt", "a") as f:
            f.write(f"{folder}\n")
            f.write(f"{r}\n")
            f.write("\n")

        process = subprocess.run(
            cmd,
            text=True,
            env=env,
            # capture_output=True,
            stdout=open("logs.txt", "a"),
            stderr=subprocess.STDOUT,
        )

        with open("logs.txt", "a") as f:
            f.write("\n")
            f.write("\n")
            f.write("\n")

        end = timer()
        total = (end - start)/60

        print(f"Elapsed time: {total}")
        print(f"{r}\t{total}")

    # print("Waiting 5 minutes...")
    # time.sleep(60 * 5)
    print()


if __name__ == "__main__":

    # repos = [
    #     "https://github.com/Jarvis-Yu/Dottore-Genius-Invokation-TCG-Simulator",
    #     "https://github.com/Josh-XT/pytube2",
    #     "https://github.com/sedrew/petpptx",
    #     "https://github.com/8451/labrea",
    #     "https://github.com/Psychevus/cryptography-suite",
    # ]
    # run(repos, "random_1_new")

    # repos = [
    #     "https://github.com/exdatic/vectorspace",
    #     "https://github.com/ryan95f/yamlator",
    #     "https://github.com/Mongorunway/mongorunway",
    #     "https://github.com/atomic6-org/ghg",
    #     "https://github.com/lestex/pygithubactions",
    # ]
    # run(repos, "random_1_old")

    # repos = [
    #     "https://github.com/Universite-Gustave-Eiffel/acoustic-toolbox",
    #     "https://github.com/NVIDIA/cloudai",
    #     "https://github.com/hellosign/dropbox-sign-python",
    #     "https://github.com/medkit-lib/medkit",
    #     "https://github.com/sieve-community/pytube",
    # ]
    # run(repos, "random_2_new")

    # repos = [
    #     "https://github.com/foozzi/Dali",
    #     "https://github.com/aerleon/aerleon",
    #     "https://github.com/GPLgithub/sg-otio",
    #     "https://github.com/MaxAtkinson/tilted",
    #     "https://github.com/scottbarnes/reconcile",
    # ]
    # run(repos, "random_2_old")

    # repos = [
    #     "https://github.com/mrlooi/latex2json",
    #     "https://github.com/DLR-KI/scan",
    #     "https://github.com/Onix-Systems/python-pin-payments",
    #     "https://github.com/WildDIC/pytube",
    #     "https://github.com/loonghao/transx",
    # ]
    # run(repos, "random_3_new")

    # repos = [
    #     "https://github.com/hanjinliu/acryo",
    #     "https://github.com/front-matter/commonmeta-py",
    #     "https://github.com/OpenVoiceOS/ovos-lingua-franca",
    #     "https://github.com/BSpendlove/pykeadhcp",
    #     "https://github.com/ImperialCollegeLondon/wsi",
    # ]
    # run(repos, "random_3_old")

    # repos = [
    #     "https://github.com/zabbix/python-zabbix-utils",
    #     "https://github.com/weareprestatech/hotpdf",
    #     "https://github.com/awslabs/agent-evaluation",
    #     "https://github.com/dreadnode/rigging",
    #     "https://github.com/pgorecki/lato",
    # ]
    # run(repos, "random_4_new")

    # repos = [
    #     "https://github.com/citrusvanilla/tinyflux",
    #     "https://github.com/dylanljones/pyrekordbox",
    #     "https://github.com/alexmon1989/russia_ddos",
    #     "https://github.com/flakeheaven/flakeheaven",
    #     "https://github.com/haiiliin/abqpy",
    # ]
    # run(repos, "random_4_old")

    # repos = [
    #     "https://github.com/serengil/LightPHE",
    #     "https://github.com/the-siesta-group/edfio",
    #     "https://github.com/xvnpw/ai-security-analyzer",
    #     "https://github.com/capitec/dsp-decision-engine",
    #     "https://github.com/Citi/pargraph",
    # ]
    # run(repos, "random_5_new")

    # repos = [
    #     "https://github.com/saltstack/relenv",
    #     "https://github.com/proroklab/popgym",
    #     "https://github.com/probabilists/zuko",
    #     "https://github.com/znstrider/plottable",
    #     "https://github.com/fox-it/dissect.cstruct",
    # ]
    # run(repos, "random_5_old")

    repos = [
        # "https://github.com/psf/requests",
        "https://github.com/pallets/flask",
        "https://github.com/mwaskom/seaborn",
        # "https://github.com/matplotlib/matplotlib",
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
