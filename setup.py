from setuptools import setup
import re
from pathlib import Path

_version_re = re.compile(r"^__version__\s*(?::\s*str)?\s*=\s*['\"]([^'\"]+)['\"]", re.M)


def file_getVersion(rel_path: str) -> str:
    """
    Retrieve the version string from the specified file.
    """
    version_file = Path(rel_path)
    if not version_file.exists():
        raise RuntimeError(f"Version file {rel_path} not found.")

    with open(version_file, 'r') as f:
        content = f.read()
        match = _version_re.search(content)
        if not match:
            raise RuntimeError(f"Could not find __version__ in {rel_path}")
        return match.group(1)


setup(
    name='sclai',
    version=file_getVersion('app/sclai.py'),
    description='A Simple Client for AI Interaction',
    author='FNNDSC',
    author_email='rudolph.pienaar@childrens.harvard.edu',
    url='https://github.com/FNNDSC/pl-sclai',
    py_modules=['app.sclai'],  # Explicitly include app/sclai.py as a module
    install_requires=['chris_plugin'],
    license='MIT',
    entry_points={
        'console_scripts': [
            'sclai = app.sclai:main'  # Matches app/sclai.py
        ]
    },
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Medical Science Apps.'
    ],
    extras_require={
        'none': [],
        'dev': [
            'pytest~=7.1'
        ]
    }
)

