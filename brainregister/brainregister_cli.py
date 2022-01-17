#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Created on Thu Oct  8 16:40:46 2020

Brainregister CLI module.

This includes code for passing command line arguments, and running the two
key functions from the brainregister main module.

Command Line Interface:

* main() : main entry point from command line

    + process() : select between yaml params creation or register functions


One of the two functions are called from the main brainregister module:


* create_brainregister_parameters_file(sample_template_path) : 
    create new template yaml params file


* register(brainregister_parameters_path) : 
    perform elastix-based registration according to yaml params file
    This is located in the BrainRegister class defined in the main module.



@author: stevenwest
'''

import argparse
import textwrap
from pathlib import Path


def main():
    '''Main :

    Call argparse and either generate YAML template or begin
    brainregister registration.

    Returns
    -------
    None.

    '''
    # create argparse object
    parser = argparse.ArgumentParser(
        
        formatter_class=argparse.RawDescriptionHelpFormatter,
        
        description=textwrap.dedent('''\
        Welcome to Brain Register!
        --------------------------------
            Brain Register will register mouse brain auto-fluorescence data to the Allen Common Coordinate Framework, version 3.
            
            Here's how to use it:
        '''),
        
        epilog=textwrap.dedent('''\
        Typical Usage
        --------------------------------
            
            # first create a brainregister-parameters.yaml file
            
            brainregister --yaml path/to/sample-template.nrrd
             
             This generates a template brainregister-parameters file: a
             YAML file containing all the parameters to perform brain registration.
             Modify this for registration of the input sample-template and associated
             images.
            
            # then perform brainregister registration
            
            brainregister path/to/brainregister-parameters.yaml
            
              This performs the complete brain registration.
        ''') 
        
        )
    
    parser.add_argument('-y', '--yaml', action='store_true',
                        help='Create new template brainregister-parameter YAML file.')
    
    parser.add_argument('file_path', type = str, 
                        help=textwrap.dedent('''\
            Specify a file path: if --yaml arg is passed, this file path should 
            point to the sample-template image (the image on which the 
            registration is to be optimised); if no --yaml arg, this file path 
            should point to a brainregister-parameters.yaml file.
            ''') )
    
    parser.add_argument('-d', '--dirpath', type = str, 
                        help=textwrap.dedent('''\
            Specify the relative directory path where the brainregister parameters 
            file is to be stored.  Setting this parameter only affects the location of
            the brainregister_parameters.yaml file.  The default is ./brainregister/
            '''))
    
    
    args = parser.parse_args()
    
    # process data according to yaml and filepath args
    if args.dirpath:
        process(args.yaml, Path(args.file_path), args.dirpath )
    else:
        process(args.yaml, Path(args.file_path), 'brainregister' )



def process(yaml, file_path, brainregister_dir):
    '''Process : admin function to call create_parameters_file() of register()

    If yaml is true create a brainregister_parameters file, otherwise 
    attempt to begin a brainregister registration with the passed file_path.

    Parameters
    ----------
    yaml : bool
        Boolean to indicate whether a new brainregister_parameters file should 
        be generated, or a brainregister registration should be attempted.

    file_path : str OR PosixPath
        A path.  If yaml is true, this should point to the image 
        file that will serve as the sample-template (the image upon which the 
        registration will be optimised).  Else if yaml is false, this should 
        point to a brainregister-parameters.yaml file. Converted to PosixPath 
        object if only a string.

    Returns
    -------
    None.

    '''
    import brainregister
    from brainregister import BrainRegister
    
    if yaml:
        brainregister.create_parameters_file( Path(file_path), 
                                             output_dir = Path(brainregister_dir) )
    else:
        br = BrainRegister(Path(file_path))
        br.register()
    


if __name__ == '__main__':
    main()

