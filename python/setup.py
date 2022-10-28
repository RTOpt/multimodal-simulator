from setuptools import setup

setup(
    name='multimodalsim',
    version='0.0.1',
    packages=['multimodalsim', 'multimodalsim.logger', 'multimodalsim'
              '.optimization', 'multimodalsim.reader',
              'multimodalsim.simulator', 'multimodalsim.observer'],
    package_dir={'multimodalsim': 'multimodalsim'},
    url='',
    license='',
    author='',
    author_email='',
    description='',
    install_requires=['pip', 'setuptools', 'networkx']
)
