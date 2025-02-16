from setuptools import setup, find_packages

setup(
    name="missminutes",
    version="0.1",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "minutes_cui=missminutes.minutes_cui:main",
        ],
    },
    install_requires=[
        # Add your dependencies here
    ],
)
