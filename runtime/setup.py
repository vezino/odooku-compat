from setuptools import setup, find_packages
from odooku import __version__

setup(
    name='odooku',
    version=__version__,
    url='https://github.com/adaptivdesign/odooku-compat',
    author='Raymond Reggers - Adaptiv Design',
    author_email='raymond@adaptiv.nl',
    description=('Odooku runtime'),
    license='Apache Software License',
    packages=find_packages(),
    zip_safe=False,
    install_requires=[
        'click',
        'gunicorn'
    ],
    entry_points='''
        [console_scripts]
        odooku=odooku.cli:entrypoint
    ''',
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'License :: OSI Approved :: Apache Software License',
    ],
)
