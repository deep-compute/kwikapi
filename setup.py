from setuptools import setup, find_packages
import os

HERE = os.path.abspath(os.path.dirname(__file__))
def get_long_description():
    dirs = [ HERE ]
    if os.getenv("TRAVIS"):
        dirs.append(os.getenv("TRAVIS_BUILD_DIR"))

    long_description = ""

    for d in dirs:
        rst_readme = os.path.join(d, "README.rst")
        if not os.path.exists(rst_readme):
            continue

        with open(rst_readme) as fp:
            long_description = fp.read()
            return long_description

    return long_description

long_description = get_long_description()

# https://docs.djangoproject.com/en/1.11/intro/reusable-apps/
version = '0.0.1'
setup(
    name='kwikapi',
    version=version,
    packages=find_packages(),
    include_package_data=True,
    license='MIT License',  # example license
    description='Quickest way to build powerful HTTP APIs in Python',
    long_description=long_description,
    url='https://github.com/deep-compute/kwikapi',
    download_url="https://github.com/deep-compute/kwikapi/tarball/%s" % version,
    author='Deep Compute, LLC',
    author_email='contact@deepcompute.com',
    install_requires=[
    'django==1.9',
    'msgpack-python',
    'python-rapidjson',
    'structlog',
    'coloredlogs'
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
