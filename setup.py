from setuptools import setup, find_packages

setup(
    name="ai_friend_biographer",
    version="0.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
) 