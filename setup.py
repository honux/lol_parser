from setuptools import setup


setup(
    name = "lol_parser",
    version = "1.0.18",
    author = "Adriano Martins",
    author_email = "atoahp@hotmail.com",
    description = ("Parsers for several different files formats of League of Legends"),
    license = "MIT",
    keywords = "league_of_legends",
    url = "https://github.com/honux/lol_parser",
    install_requires=[
        "requests",
        "xxhash",
        "zstd",
    ],
    packages=['lol_parser'],
)
