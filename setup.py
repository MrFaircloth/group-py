from setuptools import setup, find_packages

setup(
    name='group-py',
    version='0.2.0',
    author='mrfaircloth',
    description='GroupMe API wrapper module.',
    packages=find_packages(),
    install_requires=[
        'requests',  # List your dependencies here
    ],
)
