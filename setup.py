from setuptools import setup, find_packages

setup(
    name="autosubscribe",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pyyaml",
        "pytest",
        "asyncssh",
        "tqdm",
    ],
    python_requires=">=3.7",
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool for auto-subscribing and managing proxy servers",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/autosubscribe",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    package_data={
        'autosubscribe': [
            'config/*.yaml',
            'config/*.json',
        ],
    },
) 