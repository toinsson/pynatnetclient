import io, os, re
from os import path
from setuptools import find_packages
from distutils.core import setup

# pip's single-source version method as described here:
# https://python-packaging-user-guide.readthedocs.io/single_source_version/
def read(*names, **kwargs):
    with io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8")
    ) as fp:
        return fp.read()

def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(name='pynatnetclient',
      version=find_version('pynatnetclient', '__init__.py'),

      description='Python client to Optitrack.',
      # long_description=long_description,
      author='Antoine Loriette',
      author_email='antoine.loriette@gmail.com',
      url='https://github.com/toinsson/pynatnetclient',
      license='Apache',

      classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
      ],
      keywords='optitrack',

      packages=find_packages(),
)