from setuptools import setup, find_packages

setup(
    name="hellogpt",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        f"GDAL=={subprocess.check_output(['gdal-config', '--version']).decode('utf-8').strip()}",
    ],
)