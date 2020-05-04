import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pysdtoken",
    version="0.0.1",
    author="Johnny Birchett",
    description="Pythonic wrapper for the RSA sdauto32.dll soft token service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/XanaDublaKublaConch/pysdtoken/",
    packages=setuptools.find_packages(),
    install_requires="pywin32-ctypes",
    calssifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)

