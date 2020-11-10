import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pysdtoken",
    version="1.0.1",
    author="XanaDublaKublaConch",
    author_email="XanaDublaKublaConch@styrophobia.org",
    description="Pythonic wrapper for the RSA sdauto32.dll soft token service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/XanaDublaKublaConch/pysdtoken/",
    # packages=setuptools.find_packages(),
    packages=['pysdtoken'],
    install_requires="pywin32-ctypes",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
    ],
    python_requires='>=3.7',
)

