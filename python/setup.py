from setuptools import setup

setup(
    name='multimodalsim',
    version='',
    packages=['multimodalsim.logger', 'multimodalsim.optimization', 'multimodalsim.reader', 'multimodalsim.simulator'],
    package_dir={'multimodalsim': 'multimodalsim'},
    url='',
    license='',
    author='',
    author_email='',
    description='',
    install_requires=['pip', 'lxml', 'Pillow', 'six', 'python-dateutil', 'setuptools', 'packaging', 'pyparsing',
                      'networkx']
)
