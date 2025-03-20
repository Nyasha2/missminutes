from setuptools import setup, find_packages

setup(
    name="missminutes",
    version="0.1",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "minutes_cui=missminutes.cli.main:main",
        ],
    },
    install_requires=[
        "google-auth-oauthlib",
        "google-auth-httplib2",
        "google-api-python-client",
        "click",
        "rich",
        "python-dateutil",
        "tzlocal",
        "pytz",
        "prompt_toolkit",
    ],
)
