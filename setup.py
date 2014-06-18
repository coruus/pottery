from setuptools import setup

setup(
    name='pottery',
    version='0.1',
    description='cffi-based interface to the ottery random number'
                'generator package',
    author='David Leon Gil',
    author_email='coruus@gmail.com',
    package_dir = {'': '.'},
    packages = ['pottery'],
    use_2to3 = True,
)
