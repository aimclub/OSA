from setuptools import setup, find_packages

setup(
    name="readmegen",
    version="0.1.0",
    packages=find_packages(include=["readmegen", "readmegen.*"]),
    package_data={
        "readmegen": ["generators/svg/shieldsio_icons.json",
                      "generators/svg/skill_icons.json",],
    },
    install_requires=[
        "aiohttp==3.11.11",
        "gitdb==4.0.11",
        "gitpython==3.1.43",
        "PyYAML==6.0.2",
        "pydantic-extra-types==2.9.0",
        "pydantic==2.10.5",
        "requests==2.32.3",
        "structlog==24.4.0",
        "tiktoken==0.8.0",
        "tomli==2.2.1",
    ],
    description="README generator",
    python_requires=">=3.9",
)