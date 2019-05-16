from setuptools import setup, find_packages

version = '0.5.8'
setup(
    name="kwikapi",
    version=version,
    packages=find_packages("."),
    package_dir={'kwikapi': 'kwikapi'},
    include_package_data=True,
    license='MIT License',
    description='Quickly build API services to expose functionality in Python.',
    url='https://github.com/deep-compute/kwikapi',
    download_url="https://github.com/deep-compute/kwikapi/tarball/%s" % version,
    author='Deep Compute, LLC',
    author_email='contact@deepcompute.com',
    install_requires=[
    'msgpack-python==0.5.1',
    'deeputil==0.2.7',
    'numpy==1.15.1',
    'future==0.16.0',
    'requests>=2.18.4',
    ],
    extras_require={
        'django': ['kwikapi-django==0.2.6'],
        'tornado': ['kwikapi-tornado==0.3.7'],
        'all': ['kwikapi-django==0.2.6', 'kwikapi-tornado==0.3.7']
    },
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
