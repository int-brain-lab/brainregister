# brainregister
Python package for elastix-based registration of tissues to atlases; with mouse brain registration to the Allen CCFv3 built-in.


# Installation

At the command line:

1. clone the repository to a location on your system.
```
git clone https://github.com/int-brain-lab/brainregister
```

2. create a new conda environment : RECOMMENDED to install into a conda environment

```
conda create --name brainregister python=3.8 
  #  python version specified - all python UTILITIES are installed! including pip setuptools and other dependencies for package management!

 # once created, can activate the environment:
conda activate brainregister

 # can see this is a blank environment:
conda list # shows python version and python utilities installed into this environment

```

3. Install using pip

```
cd brainregister # move to the brainregister directory
  # i.e. where setup.py is
  
 # Install via pip in STANDARD MODE
pip install .


conda list # can see that brainregister & its key dependency simpleitk-elastix is also installed

```

There may be issues with the simpleitk-elastix dependency install on systems other than Ubuntu - please let me know if you run into any trouble.


# Usage

## Mouse Atlas

The Allen mouse CCFv3 is built into the brainregister package, and is the default target dataset.  It has been modified by the IBL to annotate the atlas with left and right hemisphere structures, and the CCF annotation image has been moved from 32bit to 16bit unsigned (to save space), and all brain regions are now contiguously encoded in this image from pixel value 0 (background).  All the data associated with the Allen CCF built into BrainRegister can be browsed in the package:

```
ls brainregister/brainregister/resources/allen-ccf/
```

In particular, the `ccf_parameters.yaml` file contains useful notes about the atlas organisation.  Using this as a template, one can build further atlases, using their own ccf-template, ccf-annotations, and ccf-structure tree files, and encoding the metadata as appropriate into the `ccf_parameters.yaml` file.


## BrainRegister Parameter File

BrainRegister uses a parameter file to identify all the data required to register one dataset to another.  The user can build the default YAML parameters file with the `--yaml` command line option:

```
brainregister --yaml path/to/source-template-image.tif
```

The parameter file is built using as much information as can be automatically extracted from the `source-template-image.tif` image file, including the source-template-path, any annotations and structure-trees linked to it (to support a chain of registrations), other source images acquired in the same space as the source-template (typically microscopical channels containing other histological data that needs transforming), source template image resolution and size.  Default values are then given for source template tissue structure and orientation, target template information - including path (to a brainregister `ccf_parameters.yaml` or `target_parameters.yaml` file), downsampling, and source-to-target & target-to-source registrations/transformations.

Detailed explanations of all parameters is provided in the brainregister_parameters.yaml file produced via this command, please refer to this documentation when setting parameters.


## BrainRegister Registration & Transformation

Once a suitable parameter file has been created and edited, the brainregister registration and transformation can be executed as follows:

```
brainregister path/to/brainregister_parameters.yaml
```

This will perform all registrations and transformations as specified in the parameters file.  A detailed log of all steps will be presented in the command line.


For further help with usage use the `-h` command line flag:

```
brainregister -h

usage: brainregister [-h] [-y] [-d DIRPATH] [-t TEMPLATE] [-n NAME] file_path                                                                                                          
                                                                                                                                                                                       
Welcome to Brain Register!                                                                                                                                                             
--------------------------------                                                                                                                                                       
    Brain Register will register mouse brain auto-fluorescence data to the Allen Common Coordinate Framework, version 3.                                                               
                                                                                                                                                                                       
    Here's how to use it:                                                                                                                                                              
                                                                                                                                                                                       
positional arguments:                                                                                                                                                                  
  file_path             Specify a file path: if --yaml arg is passed, this file path should point to the sample-template image (the image on which the registration is to be           
                        optimised); if no --yaml arg, this file path should point to a brainregister-parameters.yaml file.                                                             
                        
OUTPUT:
optional arguments:
  -h, --help            show this help message and exit
  -y, --yaml            Create new template brainregister-parameter YAML file.
  -d DIRPATH, --dirpath DIRPATH
                        Specify the relative directory path where the brainregister parameters file is to be stored. Setting this parameter only affects the location of the
                        brainregister_parameters.yaml file. The default is ./brainregister/
  -t TEMPLATE, --template TEMPLATE
                        Specify the relative path where a template brainregister parameters exists. Use this to utilise a custom brainregister_parameters.yaml file with custom
                        default values.
  -n NAME, --name NAME  Specify the name of the output brainregister parameters file. Use this to spaecify a custom name for this file. The default is brainregister_parameters.yaml.

Typical Usage
--------------------------------

    # first create a brainregister-parameters.yaml file

    brainregister --yaml path/to/sample-template.tif

     This generates a template brainregister-parameters file: a
     YAML file containing all the parameters to perform brain registration.
     Modify this for registration of the input sample-template and associated
     images.

     This can be customised as follows:
    brainregister --yaml path/to/sample-template.nrrd -d ./br-output -t ./custom-br-template.yaml -n br_params.yaml

     Here, the custom template 'custom-br-template.yaml' from working DIR is used, and
     this is saved to ./br-output/br_params.yaml.

    # then perform brainregister registration

    brainregister path/to/brainregister-parameters.yaml

      This performs the complete brain registration. All parameters for registration are specified
      in the YAML parameters file.

```


Any issues or further questions can be addressed to Steven West (primary author).



---



# CHANGE LOG



0.9.0 : 


0.9.1 :

* Corrected bugs with no downsampling registration and transformation.



