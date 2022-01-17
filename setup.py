
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    # package metadata
    name='brainregister',
    version='0.9.0',
    description='Python package for elasitx-based registration of mouse brain images to the Allen CCFv3.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords='mouse brain registration elastix ibl',
    
    # source metadata:
    url="https://github.com/stevenjwest/brainregister",
    author="Steven J. West",
    author_email="stevenjwest@gmail.com",
    packages=setuptools.find_packages(),
    
    # declare dependencies here:
    install_requires=[
          #'SimpleITK>=2.0.0', - will use new ITK+elastix package
          'SimpleITK-Elastix>=2.0.0rc2',
          'numpy>=1.19.2',
          'pyyaml>=6.0',
          'pynrrd>=0.4.2',
          'matplotlib>=3.5.1',
      ],
      
    # test suite
    test_suite='nose.collector',
    tests_require=['nose'],
    
    # entry points for CLI commands:
        entry_points = {
        'console_scripts': ['brainregister=brainregister.brainregister_cli:main'],
    },
    
    # add this to include all resources declared in MANIFEST.in file
    include_package_data=True,
      
    # specify a specific version here - ~= means all subversions in this version
    python_requires='~=3.8',
)

