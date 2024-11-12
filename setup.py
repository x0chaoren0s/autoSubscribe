from setuptools import setup, find_packages

setup(
    name="autoSubscribe",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'pyyaml',
        'pytest',
        'pytest-asyncio'
    ]
) 