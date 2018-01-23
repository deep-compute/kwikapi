from setuptools import setup, find_packages

version = '0.0.5'
setup(
    name="kwikapi",
    version=version,
    packages=find_packages("."),
    package_dir={'kwikapi': 'kwikapi'},
    include_package_data=True,
    license='MIT License',  # example license
    description='Quickest way to build powerful HTTP APIs in Python',
    url='https://github.com/deep-compute/kwikapi',
    download_url="https://github.com/deep-compute/kwikapi/tarball/%s" % version,
    author='Deep Compute, LLC',
    author_email='contact@deepcompute.com',
    install_requires=[
    'msgpack-python',
    ],
    extras_require={
        'django': ['kwikapi_django'],
        'tornado': ['kwikapi_tornado'],
        'all': ['kwikapi_django', 'kwikapi_tornado']
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
