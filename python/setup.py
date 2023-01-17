from setuptools import setup

setup(
    name='multimodalsim',
    version='0.0.1',
    packages=['multimodalsim', 'multimodalsim.config',
              'multimodalsim.config.ini', 'multimodalsim.logger',
              'multimodalsim.optimization', 'multimodalsim.reader',
              'multimodalsim.simulator', 'multimodalsim.observer',
              'multimodalsim.state_machine', 'multimodalsim.statistics'],
    package_data={'multimodalsim': ['config/ini/*',]},
    package_dir={'multimodalsim': 'multimodalsim'},
    url='',
    license='',
    author='',
    author_email='',
    description='',
    install_requires=['pip', 'setuptools', 'networkx', 'numpy', 'pandas']
)
