from setuptools import setup

setup(
    name='multimodalsim',
    version='0.0.1',
    packages=['multimodalsim', 'multimodalsim.config',
              'multimodalsim.config.ini', 'multimodalsim.coordinates',
              'multimodalsim.logger', 'multimodalsim.observer',
              'multimodalsim.optimization',
              'multimodalsim.optimization.fixed_line',
              'multimodalsim.optimization.shuttle',
              'multimodalsim.reader', 'multimodalsim.simulator',
              'multimodalsim.state_machine', 'multimodalsim.statistics'],
    package_data={'multimodalsim': ['config/ini/*',]},
    package_dir={'multimodalsim': 'multimodalsim'},
    url='',
    license='',
    author='',
    author_email='',
    description='',
    install_requires=['pip', 'setuptools', 'networkx', 'numpy', 'pandas',
                      'requests', 'polyline', 'pyproj', 'matplotlib']
)

