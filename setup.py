from setuptools import setup, find_packages
from os import path

__version__ = 20211130.0
here = path.abspath(path.dirname(__file__))

# get the dependencies and installs
with open(path.join(here, "requirements.txt"), encoding="utf-8") as f:
    all_reqs = f.read().split("\n")

install_requires = [x.strip() for x in all_reqs if "git+" not in x]

setup(
    name="canopy",
    version=__version__,
    description="Helper for Instructure Canvas API",
    url="https://github.com/tylerclair/canopy",
    author="Tyler Clair",
    author_email="tyler.clair@gmail.com",
    license="MIT",
    packages=find_packages(exclude=["docs", "tests*"]),
    include_package_data=True,
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "canvas_api_builder = canopy.scripts.canvas_api_builder:cli",
        ],
    },
)
