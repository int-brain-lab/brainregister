"""
brainregister

A Package that defines a 3D image registeration framework, including optimised
registration parameters and the Allen CCFv3 mouse brian atlas.

"""

# package metadata
__version__ = '0.9.0'
__author__ = 'Steven J. West'

# package imports
import os
import glob
import sys
import gc
import yaml # pyyaml library
from pathlib import Path
import SimpleITK as sitk #SimpleITK-elastix package

 # get the module directory - to point to resources/ and other package artifacts
BRAINREGISTER_MODULE_DIR = os.path.abspath( os.path.dirname(__file__) )


# example function for testing
def version():
    print("BrainRegister : version "+__version__)
    print("  Author : "+__author__)


def create_parameters_file(sample_template_path, 
            output_dir = Path('brainregister'),
            brainregister_params_template_path = 'brainregister_params', 
            brainregister_params_filename = 'brainregister_parameters.yaml'):
    '''Create Brainregister Parameters File

    Generates a new brainregister_parameters.yaml file based on the
    sample_template_path: this should be a RELATIVE PATH to an existing VALID
    IMAGE which will be used for elastix registration.
    
    The brainregister_parameters.yaml file will also be filled with any other
    Sample Images (files with the same extension as the Sample Template Image)
    for transformation.
    
    The brainregister_parameters.yaml file will be written to disk to output_dir
    which defines a DIR tree from the CURRENT WORKING DIRECTORY that will be
    created for holding registration data.
    
    Prior to registration, the user should review the 
    brainregister_parameters.yaml file and modify as appropriate.
    
    To execute the registration use 
    brainregister.register(brainregister_parameters.yaml)
    
    Parameters
    ----------
    sample_template_path : pathlib Path
        This should point to the image file that will serve as the sample-
        template (the image upon which the registration will be optimised).
    
    output_dir : pathlib Path
        This points to the output dir where all brainregister registration and
        transformation data will be stored.  set to 'brainregister' by default
        and written to the current working directory.
    
    brainregister_params_template_path : str
        String representing the path to the template brainregister parameters 
        yaml file.  Set to 'brainregister_params' by default, so will use the 
        built-in brainregister allen ccf data.  This can be set to an 
        external template by the user.  NOTE: This function assumes any 
        user-defined yaml template  contains the SAME FIELDS, but has modified 
        default values to suit the users needs.  Any comments in an external 
        yaml parameters file will be REMOVED after parsing through this method,
        therefore it is best to create/copy a user-defined template manually.
    
    brainregister_params_filename : str
        String representing the file name the brainregister parameters yaml file
        will be written to.  Set to 'brainregister_parameters.yaml' by default 
        - RECOMMENDED TO KEEP THIS NAMING CONVENTION!
    
    Returns
    -------
    brp : dict
        BrainRegister Parameters dict.

    '''
    
    print('')
    print('')
    print('================================')
    print('CREATE BRAINREGISTER PARAMS FILE')
    print('================================')
    print('')
    
    
    # RESOLVE the path- remove any .. references and convert to absolute path
    sample_template_path_res = sample_template_path.resolve()
    
    # Make the path into an absolute path - remove ~ and ensure absolute
    # AND convert to STRING
    stp = str(sample_template_path.expanduser().absolute() )
    
    print('  reading source template image information..')
    print('')
    # try to read image header with sitk
    reader = sitk.ImageFileReader()
    reader.SetFileName( stp )
    reader.LoadPrivateTagsOn()
    try:
        reader.ReadImageInformation()
    except:
        print('\033[1;31m ERROR : The input file is not a valid image: '
                + stp + ' \033[0;0m')
        sys.exit('input file not valid')
    
    # if image is valid to sitk.reader this will pass
    
    print('  creating brainregister output directory : ' + str(output_dir) )
    print('')
    # next - resolve and create output_dir
    output_dir.resolve().mkdir(parents=True, exist_ok=True)
    # this is where the brainregister_parameters.yaml file will be written
    brainregister_params_path = Path( 
        str(output_dir.resolve().expanduser().absolute() ) 
        + os.path.sep
        + brainregister_params_filename)
    
    print('  building brainregister parameters file..')
    # next - build the yaml file
    if brainregister_params_template_path == 'brainregister_params':
        # open the brainregister template from resources/ dir in brainregister package
        # read yaml to dict
        br_params = os.path.join(
                        BRAINREGISTER_MODULE_DIR, 
                        'resources', 'brainregister_parameters.yaml')
        with open(br_params, 'r') as file:
            brp = yaml.safe_load(file)
        
        # read yaml to list - THIS CONTAINS THE COMMENTS
        with open(br_params, 'r') as file:
            brpf = file.readlines()
    else:
        with open(brainregister_params_template_path, 'r') as file:
            brp = yaml.safe_load(file)
    
    brp_keys = list(brp.keys())
    
    # MODIFY PARAMETERS
    
    print('    adding template path : ' + 
                  sample_template_path_res.stem +
                  sample_template_path_res.suffix )
    # set sample-template-path to stp
    brp['source-template-path'] = os.path.relpath(
                sample_template_path_res, 
                output_dir.resolve().expanduser().absolute()  )
    
    brp['source-annotations-path'] = [] # set to blank, user can modify manually as needed
    brp['source-structure-tree'] = [] # set to blank, user can modify manually as needed
    
    print('    adding image paths..')
    # get other files with same suffix as stp in parent dir
    fn, ext = os.path.splitext(sample_template_path_res.name)
    files = glob.glob( 
        str( str(sample_template_path_res.parent.expanduser().absolute() ) 
            + os.path.sep 
            + "*" 
            + ext) )
    # filter to remove the current sample_template_path and extract just the name(s)
    filenames = [Path(f).name for f in files if f != str(
                    sample_template_path_res.expanduser().absolute()) ]
    
    source_path_keys = [b for b in brp_keys if (
                                b.startswith('source-') 
                            and b.endswith('-path') 
                        and not b.startswith('source-template-path')
                        and not b.startswith('source-annotations-path') ) ]
    
    for s in source_path_keys: # add image files to source_images_keys
        brp[s] = filenames
    
    
    print('    adding source template image resolution..')
    
    if any([r == 1.0 for r in reader.GetSpacing()]):
        print('')
        print('\033[1;31m TEMPLATE RESOLUTION NOT FOUND : '+
              'Please add manually to the brainregister params file! \033[0;0m')
        print('')
    else:
        print('      adding x-um : ' + str(reader.GetSpacing()[0]) )
        brp['source-template-resolution']['x-um'] = reader.GetSpacing()[0]
        print('      adding y-um : ' + str(reader.GetSpacing()[1]) )
        brp['source-template-resolution']['y-um'] = reader.GetSpacing()[1]
        print('      adding z-um : ' + str(reader.GetSpacing()[2]) )
        brp['source-template-resolution']['z-um'] = reader.GetSpacing()[2]
    
    
    print('    adding source template image size..')
    
    print('      adding x-um : ' + str(reader.GetSize()[0]) )
    brp['source-template-size']['x'] = reader.GetSize()[0]
    print('      adding y-um : ' + str(reader.GetSize()[1]) )
    brp['source-template-size']['y'] = reader.GetSize()[1]
    print('      adding z-um : ' + str(reader.GetSize()[2]) )
    brp['source-template-size']['z'] = reader.GetSize()[2]
    
    
    print('    saving brainregister parameters file..')
    with open(brainregister_params_path, 'w') as file:
        yaml.dump(brp, file, sort_keys=False)
    
    # ONLY IF USING brainregister parameters yaml (as know where comments are!)
    if brainregister_params_template_path == 'brainregister_params':
        # add COMMENTS from original file
        with open(brainregister_params_path, 'r') as file:
            brpf2 = file.readlines()
        
        # get index of sample-template-orientation 
         # as sample-images length can VARY!
        sil = [i for i, s in enumerate(brpf2) if 'source-template-orientation' in s]
        
        # get index of downsampled-to-ccf-save-images
         # as downsampled-to-ccf-parameters-files length can VARY!
        pfld = [i for i, s in enumerate(brpf2) if 'source-to-target-save-image-type' in s]
        
        # get index of ccf-to-downsampled-save-annotation
         # as ccf-to-downsampled-parameters-files length can VARY!
        pflc = [i for i, s in enumerate(brpf2) if 'target-to-source-save-image-type' in s]
        
        # concat comments and yaml lines into one list:
        brpf3 = [ brpf[0:53] + # source- image space comments
                  brpf2[ 0:(sil[0]+1) ] + # source- params
                  brpf[71:87] + # target- image space comments
                  brpf2[ (sil[0]+1):(sil[0]+3)] + # target- params
                  brpf[89:117] + # downsampling- general comments
                  brpf2[ (sil[0]+3):(sil[0]+6)] + # downsampling- general params
                  brpf[120:146] + # downsampling- output comments
                  brpf2[ (sil[0]+6):(sil[0]+11)] + # source-to-target downsampling output params
                  brpf[151:152] + # blank line!
                  brpf2[ (sil[0]+11):(sil[0]+16)] + # target-to-source downsampling output params
                  brpf[157:206] + # source-to-target comments
                  brpf2[(sil[0]+16):(pfld[0]+1)] + # source-to-target params
                  brpf[219:268] + # target-to-source comments
                  brpf2[ (pfld[0]+1):(pflc[0]+1)] # target-to-source params
                                                          ]
        brpf3 = brpf3[0] # remove the nesting of this list
        
        # write this OVER the current yaml
        with open(brainregister_params_path, 'w') as file:
            for b in brpf3:
                file.write('%s' % b)
        
        print('      written brainregister_parameters.yaml file : ' +
               os.path.relpath(brainregister_params_path, os.getcwd()  ) )
        
    else:
        print('  written custom brainregister parameters yaml file', brainregister_params_template_path)
    
    # return the yaml file dict
    return brp
    





class BrainRegister(object):
    
    
    def __init__(self, yaml_path):
        
        self.set_brainregister_parameters_filepath(yaml_path)
        self.initialise_brainregister()
        self.create_output_dirs()
    
    
    
    def set_brainregister_parameters_filepath(self, yaml_path):
        self.yaml_path = yaml_path
        
    
    
    def get_brainregister_parameters_Filepath(self):
        return self.yaml_path
    
    
    def register(self):
        
        self.register_transform_highres_to_downsampled()
        
        self.register_source_to_target()
        self.transform_source_to_target()
        
        self.register_target_to_source()
        self.transform_target_to_source()
        
        self.transform_lowres_to_downsampled()
        
        self.save_target_params()
        
    
    
    
    
    def initialise_brainregister(self):
        
        print('')
        print('')
        print('==========================')
        print('INITIALISING BRAINREGISTER')
        print('==========================')
        print('')
        
        print('  loading brainregister parameters file..')
        self.load_params()
        
        
        ### RESOLVE PARAMETERS ###
        ##########################
        
        # paths to output DIRs
        print('  resolving output DIR paths..')
        self.resolve_dirs()
        
        # paths to source template and images
        print('  resolving source template and image paths..')
        self.resolve_source_params()
        
        # paths to ccf params and ccf template + annotation imagess
        print('  resolving target template and image paths..')
        self.resolve_target_params()
        
        print('  resolving elastix & transformix parameter file paths..')
        self.resolve_params()
        
        print('')
        
    
    
    
    
    def load_params(self):
        """
        Load brainregister parameters file
        
        This loads the brainregister_parameters.yaml file pointed to by yaml_file,
        and the brainregister_parameters.yaml directory path. These are set to
        instance variables brp and brp_dir, respectively.
        
        This function must be run before any other processing can take place!
        """
        
        # resolve path to parameters file and get the parent dir
        yaml_path_res = Path(self.yaml_path).resolve()
        self.brp_dir = yaml_path_res.parent
        
        # first check that yaml_path is valid and read file
        if Path(self.yaml_path).exists() == False:
            print('')
            print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
            print('')
            sys.exit('  no brainregister_params file!')
        
        with open(self.yaml_path, 'r') as file:
            self.brp = yaml.safe_load(file)
        
        self.brp_keys = list(self.brp.keys())
        # check the resolutions have been set to something other than 0.0 (which is the default)
        if ( (self.brp['source-template-resolution']['x-um'] == 0.0) | 
            (self.brp['source-template-resolution']['y-um'] == 0.0) | 
            (self.brp['source-template-resolution']['z-um'] == 0.0) ) :
            print('')
            print('\033[1;31m ERROR : ' + 
                  ' image resolution not set in brainregister_params : ' + 
                      self.yaml_path + ' \033[0;0m')
            print('')
            sys.exit( str('ERROR :  image resolution not set in brainregister_params : ' + 
                      self.yaml_path) )
        
        
    
    
    def resolve_dirs(self):
        '''
        Resolve the output directory paths

        Returns
        -------
        None.

        '''
        
        self.src_tar_dir = Path( str(self.brp_dir) 
                       + os.path.sep
                       + self.brp['source-to-target-output'] )
        
        self.tar_src_dir = Path( str(self.brp_dir) 
                       + os.path.sep
                       + self.brp['target-to-source-output'] )
        
        # get downsampling output
        self.src_tar_ds = (self.brp['source-to-target-downsampling-output'] is not False)
        
        self.src_tar_ds_dir = None
        if self.src_tar_ds is True:
            self.src_tar_ds_dir = Path( str(self.brp_dir) 
                       + os.path.sep
                       + self.brp['source-to-target-downsampling-output'] )
        
        
        self.tar_src_ds = (self.brp['target-to-source-downsampling-output'] is not False)
        
        self.tar_src_ds_dir = None
        if self.tar_src_ds is True:
            self.tar_src_ds_dir = Path( str(self.brp_dir) 
                       + os.path.sep
                       + self.brp['target-to-source-downsampling-output'] )
        
        
    
    
    def resolve_source_params(self):
        '''
        Resolve source image paths
        
        Also instantiate object variables for source template image in source,
        downsampled, and target spaces - initially set to None.

        Returns
        -------
        None.

        '''
        
        self.source_template_path = Path( 
            str(self.brp_dir) + 
            os.path.sep + 
            self.brp['source-template-path'] ).resolve()
        
        self.source_template_path_ds = None
        if self.src_tar_ds is True:
            self.source_template_path_ds = Path( 
                str(self.src_tar_ds_dir) + 
                os.path.sep  + 
                self.brp['downsampling-prefix'] + 
                Path(os.path.basename(
                            self.brp['source-template-path'])).stem + 
                '.' + 
                self.brp['downsampling-save-image-type'] )
        
        
        self.source_template_path_target = Path( 
            str(self.src_tar_dir) + 
            os.path.sep  + 
            self.brp['source-to-target-prefix'] + 
            Path(os.path.basename(
                            self.brp['source-template-path'])).stem +
            '.' + 
            self.brp['source-to-target-save-image-type'] )
        
        
        source_path_keys = [b for b in self.brp_keys if (
                                    b.startswith('source-') 
                                and b.endswith('-path') 
                            and not b.startswith('source-template-path') ) ]
        
        
        self.source_anno_path = []
        self.source_anno_path_ds = []
        self.source_anno_path_target = []
        
        if ( ('source-annotations-path' in source_path_keys) and
            (len(self.brp['source-annotations-path']) > 0) ):
            
            for sap in self.brp['source-annotations-path']:
                
                self.source_anno_path.append(  Path( 
                    str(self.brp_dir) + 
                    os.path.sep + sap ).resolve() )
                
                if self.src_tar_ds is True:
                    self.source_anno_path_ds.append( Path( 
                        str(self.src_tar_ds_dir) + 
                        os.path.sep  + 
                        self.brp['downsampling-prefix'] + 
                        Path(os.path.basename(sap)).stem + 
                        '.' + 
                        self.brp['downsampling-save-image-type'] ) )
                    
                self.source_anno_path_target.append( Path( 
                    str(self.src_tar_dir) + 
                    os.path.sep  + 
                    self.brp['source-to-target-prefix'] + 
                    Path(os.path.basename(sap)).stem +
                    '.' + 
                    self.brp['source-to-target-save-image-type'] ) )
        
        
        # and structure trees!
        self.source_tree_path = []
        self.source_tree_path_ds = []
        self.source_tree_path_target = []
        
        if ((len(self.brp['source-structure-tree']) > 0) ):
            
            for sst in self.brp['source-structure-tree']:
                
                self.source_tree_path.append(  Path( 
                    str(self.brp_dir) + 
                    os.path.sep + sst ).resolve() )
                
                if self.src_tar_ds is True:
                    self.source_tree_path_ds.append( Path( 
                        str(self.src_tar_ds_dir) + 
                        os.path.sep  + 
                        self.brp['downsampling-prefix'] + sst ) )
                    
                self.source_tree_path_target.append( Path( 
                    str(self.src_tar_dir) + 
                    os.path.sep  + 
                    self.brp['source-to-target-prefix'] + sst ) )
        
        
        
        # gen without template or annotation
        source_path_keys = [b for b in self.brp_keys if (
                                    b.startswith('source-') 
                                and b.endswith('-path') 
                            and not b.startswith('source-template-path')
                            and not b.startswith('source-annotations-path') ) ]
        
        self.source_image_path = []
        for s in source_path_keys:
            if self.brp[s]: # only add if not blank
            
                self.source_image_path.append(
                    [Path( 
                str(self.source_template_path.parent) 
                + os.path.sep 
                + str(sr)) for sr in self.brp[s] ]
                     )
                
        
        self.source_image_path_ds = []
        self.source_image_path_target = []
        if self.source_image_path: # only flatten list if not empty!
            
            self.source_image_path = [item for sublist in self.source_image_path for item in sublist]
            
            for s in self.source_image_path:
                if self.src_tar_ds is True:
                    self.source_image_path_ds.append( Path( 
                        str(self.src_tar_ds_dir) + 
                        os.path.sep  + 
                        self.brp['downsampling-prefix'] + 
                        Path(os.path.basename(s)).stem +
                        '.' + 
                        self.brp['downsampling-save-image-type'] ) )
                    
                
                self.source_image_path_target.append( Path(
                    str(self.src_tar_dir) + 
                    os.path.sep  + 
                    self.brp['source-to-target-prefix'] + 
                    Path(os.path.basename(s)).stem +
                    '.' + 
                    self.brp['source-to-target-save-image-type'] ) )
        
        
        # ALSO set all image instance variables to None
        self.source_template_img = None
        self.source_template_img_filt = None # post-filtering
        self.source_template_img_ds = None
        self.source_template_img_ds_filt = None # post-filtering
        self.source_template_img_target = None
        self.source_template_img_target_filt = None # post-filtering
        
        
        # create image lists, and fill with None
        self.source_anno_img = []
        for i in self.source_anno_path:
            self.source_anno_img.append(None)
            
        self.source_anno_img_ds = []
        for i in self.source_anno_path_ds:
            self.source_anno_img_ds.append(None)
        
        self.source_anno_img_target = []
        for i in self.source_anno_path_target:
            self.source_anno_img_target.append(None)
        
        
        self.source_image_img = []
        for i in self.source_image_path:
            self.source_image_img.append(None)
        
        self.source_image_img_ds = []
        for i in self.source_image_path_ds:
            self.source_image_img_ds.append(None)
        
        self.source_image_img_target = []
        for i in self.source_image_path_target:
            self.source_image_img_target.append(None)
        
    
    
    
    def resolve_target_params(self):
        '''
        Resolve target image paths
        
        Also instantiate object variables for target template image in target,
        downsampled, and source spaces - initially set to None.

        Returns
        -------
        None.

        '''
        
        if (self.brp['target-template-path'] == 
            'brainregister:resource/allen-ccf/ccf_parameters.yaml'):
            # open the ccf params file for brainregister allen ccf
            ccf_params = os.path.join(BRAINREGISTER_MODULE_DIR, 'resources',
                                      'allen-ccf', 'ccf_parameters.yaml')
            with open(ccf_params, 'r') as file:
                self.ccfp = yaml.safe_load(file)
        else: # use user-defined path
            ccf_params = str( Path( os.path.join(
                            self.brp['target-template-path'])
                        ).resolve() )
            with open( ccf_params, 'r') as file:
                self.ccfp = yaml.safe_load( file )
        
        
        self.ccfp_keys = list(self.ccfp.keys())
        
        if self.ccfp_keys[0].startswith('ccf-'):
            self.target_string = 'ccf'
        elif self.ccfp_keys[0].startswith('target-'):
            self.target_string = 'target'
        else:
            sys.exit('  ERROR - target-template-path : does not point to a valid'+
                 ' target parameters file.  All parameters must begin with either'+
                 '"ccf" or "target"!')
        
        
        self.target_template_path = Path( 
            os.path.dirname(ccf_params) + 
            os.path.sep + 
            self.ccfp[str(self.target_string+'-template-path')] ).resolve()
        
        
        self.target_template_path_ds = None
        if self.tar_src_ds is True:
            self.target_template_path_ds = Path( 
                str(self.tar_src_ds_dir) + 
                os.path.sep  + 
                self.brp['downsampling-prefix'] + 
                Path(os.path.basename(
                    self.ccfp[str(self.target_string+'-template-path')])).stem + 
                '.' + 
                self.brp['downsampling-save-image-type'] )
        
        
        self.target_template_path_source = Path( 
            str(self.tar_src_dir) + 
            os.path.sep  + 
            self.brp['target-to-source-prefix'] + 
            Path(os.path.basename(
                self.ccfp[str(self.target_string+'-template-path')])).stem +
            '.' + 
            self.brp['target-to-source-save-image-type'] )
        
        
        target_path_keys = [b for b in self.ccfp_keys if (
                            b.endswith('-path') 
                    and not b.startswith(str(self.target_string+'-template-path')) 
                                 ) ]
        
        
        self.target_anno_path = []
        self.target_anno_path_ds = []
        self.target_anno_path_source = []
        
        if ((str(self.target_string+'-annotations-path') in target_path_keys) and
            (len(self.ccfp[str(self.target_string+'-annotations-path')]) > 0) ):
            
            for tap in self.ccfp[str(self.target_string+'-annotations-path')]:
                
                self.target_anno_path.append(Path( 
                    os.path.dirname(ccf_params) + 
                    os.path.sep + tap ).resolve() )
                
                if self.tar_src_ds is True:
                    self.target_anno_path_ds.append( Path( 
                        str(self.tar_src_ds_dir) + 
                        os.path.sep  + 
                        self.brp['downsampling-prefix'] + 
                        Path(os.path.basename(tap)).stem + 
                        '.' + self.brp['downsampling-save-image-type'] ) )
                
                self.target_anno_path_source.append( Path( 
                    str(self.tar_src_dir) + 
                    os.path.sep  + 
                    self.brp['target-to-source-prefix'] + 
                    Path(os.path.basename(tap)).stem +
                    '.' + self.brp['target-to-source-save-image-type'] ) )
        
        
        # and structure trees!
        self.target_tree_path = []
        self.target_tree_path_ds = []
        self.target_tree_path_source = []
        
        if ((len(self.ccfp[str(self.target_string+'-structure-tree')]) > 0) ):
            
            for tap in self.ccfp[str(self.target_string+'-structure-tree')]:
                    
                    self.target_tree_path.append(Path( 
                        os.path.dirname(ccf_params) + 
                        os.path.sep + tap ).resolve() )
                    
                    if self.tar_src_ds is True:
                        self.target_tree_path_ds.append( Path( 
                            str(self.tar_src_ds_dir) + 
                            os.path.sep  + 
                            self.brp['downsampling-prefix'] + tap ) )
                    
                    self.target_tree_path_source.append( Path( 
                        str(self.tar_src_dir) + 
                        os.path.sep  + 
                        self.brp['target-to-source-prefix'] + tap ) )
        
        
        
        
        target_path_keys = [b for b in self.ccfp_keys if (
                            b.endswith('-path') 
                    and not b.startswith(str(self.target_string+'-template-path'))
                    and not b.startswith(str(self.target_string+'-annotations-path')) 
                                  ) ]
        
        self.target_image_paths = []
        for s in target_path_keys:
            if self.ccfp[s]: # only add if not blank
            
                self.target_image_paths.append(
                    [Path( 
                str(self.target_template_path.parent) 
                + os.path.sep 
                + str(s)) for s in self.ccfp[s] ]
                     )
                
        
        self.target_image_paths_ds = []
        self.target_image_paths_source = []
        if self.target_image_paths: # only flatten list if not empty!
            self.target_image_paths = [item for sublist in self.target_image_paths for item in sublist]
            
            for s in self.target_image_paths:
                
                if self.tar_src_ds is True:
                    
                    self.target_image_paths_ds.append( Path( 
                        str(self.tar_src_ds_dir) + 
                        os.path.sep  + 
                        self.brp['downsampling-prefix'] + 
                        Path(os.path.basename(s)).stem +
                        '.' + 
                        self.brp['downsampling-save-image-type'] ) )
                
                self.target_image_paths_source.append( Path(
                    str(self.tar_src_dir) + 
                    os.path.sep  + 
                    self.brp['target-to-source-prefix'] + 
                    Path(os.path.basename(s)).stem +
                    '.' + 
                    self.brp['target-to-source-save-image-type'] ) )
        
        # ALSO set all image instance variables to None
        self.target_template_img = None
        self.target_template_img_filt = None # post-filtering
        self.target_template_img_ds = None
        self.target_template_img_ds_filt = None # post-filtering
        self.target_template_img_source = None
        
        
        # create image lists, and fill with None
        self.target_anno_img = []
        for i in self.target_anno_path:
            self.target_anno_img.append(None)
            
        self.target_anno_img_ds = []
        for i in self.target_anno_path_ds:
            self.target_anno_img_ds.append(None)
        
        self.target_anno_img_source = []
        for i in self.target_anno_path_source:
            self.target_anno_img_source.append(None)
        
        
        self.target_image_imgs = []
        for i in self.target_image_paths:
            self.target_image_imgs.append(None)
        
        self.target_image_imgs_ds = []
        for i in self.target_image_paths_ds:
            self.target_image_imgs_ds.append(None)
        
        self.target_image_imgs_source = []
        for i in self.target_image_paths_source:
            self.target_image_imgs_source.append(None)
        
        
    
    
    
    
    
    def resolve_params(self):
        '''
        Resolve elastix and transformix parameters files paths
        
        Also instantiate object variables : booleans for src/tar prefiltering 
        status, and parameter maps for highres <-> downsampled, and 
        downsampled <-> lowres.

        Returns
        -------
        None.

        '''
        
        self.wd = Path(os.getcwd()).resolve() # store current working directory
        
        # paths to transformix parameter map files
        
        # source-to-target downsampled transformix params
        if self.src_tar_ds == True: # save to ds_dir
            self.src_tar_ds_pm_path = [ Path(os.path.join( 
             self.src_tar_ds_dir, 
             self.brp['source-to-target-downsampling-transform-parameter-file'] ) ) ]
            
        else: # save to src to target dir
            self.src_tar_ds_pm_path = [ Path(os.path.join( 
             self.src_tar_dir, 
             self.brp['source-to-target-downsampling-transform-parameter-file'] ) ) ]
        
        # source-to-target transformix params
        # applied to the source and target AFTER downsampling
        self.src_tar_pm_paths = []
        for pm in self.brp['source-to-target-transform-parameter-files']:
            self.src_tar_pm_paths.append( 
                    Path( os.path.join(self.src_tar_dir, pm ) ) )
        
        # target-to-source downsampled transformix params
        if self.tar_src_ds == True: # save to ds_dir
            # source-to-downsampled
            self.tar_src_ds_pm_path = [ Path(os.path.join( 
             self.tar_src_ds_dir, 
             self.brp['target-to-source-downsampling-transform-parameter-file'] ) ) ]
        else: # save to target to src dir
            self.tar_src_ds_pm_path = [ Path(os.path.join( 
             self.tar_src_dir, 
             self.brp['target-to-source-downsampling-transform-parameter-file'] ) ) ]
        
        # target-to-source transformix params
        # applied to the source and target AFTER downsampling
        self.tar_src_pm_paths = []
        for pm in self.brp['target-to-source-transform-parameter-files']:
            self.tar_src_pm_paths.append( 
                    Path( os.path.join(self.tar_src_dir, pm ) ) )
        
        
        # check params-filenames and files are of the same number
        if (len(self.brp['target-to-source-transform-parameter-files']) != 
            len(self.brp['target-to-source-elastix-parameter-files'])):
            sys.exit('  ERROR - target-to-source : transform-params-filenames'+
                 ' and parameters-files are not equal in length')
        
        if (len(self.brp['source-to-target-transform-parameter-files']) != 
            len(self.brp['source-to-target-elastix-parameter-files'])):
            sys.exit('  ERROR - source-to-target : transform-params-filenames'+
                 ' and parameters-files are not equal in length')
        
        
        self.tar_src_ep = self.get_elastix_params(self.brp['target-to-source-elastix-parameter-files'])
        self.src_tar_ep = self.get_elastix_params(self.brp['source-to-target-elastix-parameter-files'])
        
        
        # load the parameter map lists if they exist, or set to None
        self.src_tar_ds_pm = self.load_pm_files(self.src_tar_ds_pm_path) 
        self.tar_src_ds_pm = self.load_pm_files(self.tar_src_ds_pm_path) 
        
        self.src_tar_pm = self.load_pm_files(self.src_tar_pm_paths)
        self.tar_src_pm = self.load_pm_files(self.tar_src_pm_paths)
        
        # create the nearest neighbour transform for any images labelled as ANNOTATION
        # eg. source-annotations-path or target-annotation-path
        self.src_tar_ds_pm_anno = None
        self.src_tar_pm_anno = None
        self.tar_src_ds_pm_anno = None
        self.tar_src_pm_anno = None
        
        if self.source_anno_path != []:
            self.src_tar_ds_pm_anno = self.edit_pms_nearest_neighbour(self.src_tar_ds_pm)
            self.src_tar_pm_anno = self.edit_pms_nearest_neighbour(self.src_tar_pm)
        
        if self.target_anno_path != []:
            self.tar_src_ds_pm_anno = self.edit_pms_nearest_neighbour(self.tar_src_ds_pm)
            self.tar_src_pm_anno = self.edit_pms_nearest_neighbour(self.tar_src_pm)
        
        
        # can load the src to tar and tar to src scale factors now
        # to compute the downsampling
        self.s2t, self.t2s = self.get_source_target_scale_factors()
        
        # and therefore work out which image should undergo downsampling
        # source or target, depending on which has the HIGHER resolution
        s2t_ratio = (self.s2t['x-um']*self.s2t['y-um']*self.s2t['z-um'])
        t2s_ratio = (self.t2s['x-um']*self.t2s['y-um']*self.t2s['z-um'])
        
        if s2t_ratio < t2s_ratio:
            self.downsampling_img = 'source'
        elif t2s_ratio < s2t_ratio:
            self.downsampling_img = 'target'
        else: # source and target are same size!
            self.downsampling_img = 'none' # so do NO DOWNSAMPLING!
        
        # initialise bools for prefiltering
        # use to determine whether the src->tar or tar->src prefiltering has been applied
        self.src_tar_prefiltered = False
        self.tar_src_prefiltered = False
    
    
    
    
    
    def create_output_dirs(self):
        '''
        Create output directories
        
        For storing output files!

        Returns
        -------
        None.

        '''
        
        print('  create output dirs..')
        
                
        if self.src_tar_ds is True:
            print('    making source-to-target downsampling dir : '+ 
                      self.get_relative_path(self.src_tar_ds_dir) )
            if self.src_tar_ds_dir.exists() == False:
                self.src_tar_ds_dir.mkdir(parents = True, exist_ok=True)
            
        
        if self.tar_src_ds is True:
            print('    making source-to-target downsampling dir : '+ 
                      self.get_relative_path(self.tar_src_ds_dir) )
            if self.tar_src_ds_dir.exists() == False:
                self.tar_src_ds_dir.mkdir(parents = True, exist_ok=True)
            
        
        
        print('    making source-to-target dir  : '+ 
              self.get_relative_path(self.src_tar_dir) )
        if self.src_tar_dir.exists() == False:
            self.src_tar_dir.mkdir(parents = True, exist_ok=True)
        
        print('    making target-to-source dir : '+ 
              self.get_relative_path(self.tar_src_dir) )
        if self.tar_src_dir.exists() == False:
            self.tar_src_dir.mkdir(parents = True, exist_ok=True)
        
        print('')
        
    
    
    
    def save_target_params(self):
        
        # load template target_parameters.yaml from package
        target_params_output_path = Path( 
            str(self.brp_dir ) 
            + os.path.sep
            + self.brp['target-template-output'])
        
        print('  building output target parameters file..')
        
        # next - build the yaml file
        tar_params_path = os.path.join(
                        BRAINREGISTER_MODULE_DIR, 
                        'resources', 'target_parameters.yaml')
        
        # read yaml to dict
        with open(tar_params_path, 'r') as file:
            tp = yaml.safe_load(file)
        
        # read yaml to list - THIS CONTAINS THE COMMENTS
        with open(tar_params_path, 'r') as file:
            tpf = file.readlines()
        
        # write variables to param list
        tp['target-template-path'] = self.brp['source-template-path']
        
        # annotations are annotations from the current target params
        # PLUS any annotations from current source params
        target_anno_paths = []
        for ta in self.target_anno_path_source:
            target_anno_paths.append(
                os.path.relpath(ta, start=self.brp_dir))
        for sa in self.source_anno_path:
            target_anno_paths.append(
                os.path.relpath(sa, start=self.brp_dir))
        tp['target-annotations-path'] = target_anno_paths
        
        # annotations are annotations from the current target params
        # PLUS any annotations from current source params
        target_tree_paths = []
        for ta in self.target_tree_path_source:
            target_tree_paths.append(
                os.path.relpath(ta, start=self.brp_dir))
        for sa in self.source_tree_path:
            target_tree_paths.append(
                os.path.relpath(sa, start=self.brp_dir))
        tp['target-structure-tree'] = target_tree_paths
        
        tp['target-template-resolution']['x-um'] = self.brp['source-template-resolution']['x-um']
        tp['target-template-resolution']['y-um'] = self.brp['source-template-resolution']['y-um']
        tp['target-template-resolution']['z-um'] = self.brp['source-template-resolution']['z-um']
        
        tp['target-template-size']['x'] = self.brp['source-template-size']['x']
        tp['target-template-size']['y'] = self.brp['source-template-size']['y']
        tp['target-template-size']['z'] = self.brp['source-template-size']['z']
        
        tp['target-template-structure'] = self.brp['source-template-structure']
        tp['target-template-orientation'] = self.brp['source-template-orientation']
        
        # write param list to brainregister output DIR
        print('    saving target parameters file..')
        with open(target_params_output_path, 'w') as file:
            yaml.dump(tp, file, sort_keys=False)
        
        # add COMMENTS from original file
        with open(target_params_output_path, 'r') as file:
            tpf2 = file.readlines()
        
        # get index of sample-template-orientation 
         # as sample-images length can VARY!
        til = [i for i, s in enumerate(tpf2) if 'target-template-resolution' in s]
        
        
        # concat comments and yaml lines into one list:
        tpf3 = [ tpf[0:24] + # target paths
                  tpf2[ 0:(til[0]) ] + # source- params
                  tpf[29:44] + # target params
                  tpf2[ (til[0]):(til[0]+10)] # target- params
                                                          ]
        tpf3 = tpf3[0] # remove the nesting of this list
        
        # write this OVER the current yaml
        with open(target_params_output_path, 'w') as file:
            for t in tpf3:
                file.write('%s' % t)
        
        print('      written target_parameters.yaml file : ' +
               os.path.relpath(target_params_output_path, os.getcwd()  ) )
        
    
    
    
    
    def get_relative_path(self, path):
        """
        Returns the relative path from current working directory to path.

        Parameters
        ----------
        path : str or Path
            Path to compute relative path to.

        Returns
        -------
        str
            The relative path as a string.

        """
        path = path.resolve()
        return os.path.relpath(path, start=self.wd)
        
    
    
    def register_transform_highres_to_downsampled(self):
        """
        Register & Transform the high-res image to downsampled image space
        
        Generates the affine scaling transform from img -> ds, and its reverse to
        move the higher-res image between soruce and target into downsampled space, 
        and vice versa.  
        
        The downsampled resolution matches that of the lower-res image between
        the source and target.  The default target in brainregister is the 
        built-in Allen Mouse Brain CCF, which has a resolution of 25µm XYZ.
        
        The downsampled image is filtered, scaled, and saved as dictated by the 
        brainregister parameters yaml, and a reference to this image is stored
        to the instance variable, `source_template_img_ds` for source downsampling
        or 'target_template_img_ds' for target downsampling.
        
        Annotation and other images at the higher-resolution are transformed into
        the downsampled image space as dictated by the  brainregister parameters yaml 
        file.

        Returns
        -------
        None.

        """
        
        
        if (self.downsampling_img == 'source'):
            # ds source
            print('')
            print('source template higher resolution than target - downsampling source..')
            print('')
            print('')
            print('=====================')
            print('SOURCE TO DOWNSAMPLED')
            print('=====================')
            print('')
            
            # generate scaling param files as needed
            self.generate_ds_scaling_param_files()
            
            # transform and save source template ds image as needed
            self.transform_save_high_ds_template()
            
            # also transform and save source annotation images - if requested in the params file
            self.transform_save_high_ds_anno()
            
            # also transform and save other source images - if requested in the params file
            self.transform_save_high_ds_images()
            
            
        elif (self.downsampling_img == 'target'):
            
            print('')
            print('target template higher resolution than source - downsampling target..')
            print('')
            print('')
            print('=====================')
            print('TARGET TO DOWNSAMPLED')
            print('=====================')
            print('')
            
            # generate scaling param files as needed
            self.generate_ds_scaling_param_files()
            
            # transform and save template ds image as needed
            self.transform_save_high_ds_template()
            
            # also transform and save source annotation images - if requested in the params file
            self.transform_save_high_ds_anno()
            
            # also transform and save other source images - if requested in the params file
            self.transform_save_high_ds_images()
            
        else:
            # no downsampling!
            print('source and target template same resolution - no downsampling performed.')
        
    
    
    
    def src_tar_ds_pm_path_exists(self):
        return self.src_tar_ds_pm_path[0].exists()
    
    
    
    def tar_src_ds_pm_path_exists(self):
        return self.tar_src_ds_pm_path[0].exists()
    
    
    
    def save_template_ds(self):
        
        if (self.downsampling_img == 'source'):
            # save the source -> target downsampling template - if requested in params file!
            if self.brp['source-to-target-downsampling-save-template'] == True:
                if self.source_template_img_ds != None:
                    print('  saving source downsampled template image : ' +
                      self.get_relative_path(self.source_template_path_ds ) )
                    self.save_image(self.source_template_img_ds, 
                                    self.source_template_path_ds)
                else:
                    print('  source template image in ds space does not exist - run get_template_ds()')
                
            
        elif (self.downsampling_img == 'target'):
            # save the target -> source downsampling template - if requested in params file!
            if self.brp['target-to-source-downsampling-save-template'] == True:
                if self.template_ds_img != None:
                    print('  saving target downsampled template image : ' +
                      self.get_relative_path(self.target_template_path_ds ) )
                    self.save_image(self.target_template_img_ds, self.target_template_path_ds)
                else:
                    print('  target template image in ds space does not exist - run get_template_ds()')
                
            
        
    
    
    
    def move_image_img_ds(self, img):
        '''
        Move from raw space to downsampled image space
        
        This depends which image has been downsampled (source or target).  If no 
        downsampling, this method returns None.
        
        Downsampling images are first filtered according to the 
        downsampling-filter parameter in the brainregister parameters file.

        Parameters
        ----------
        img : SITK Image
            Assumed this image is in the raw image space.

        Returns
        -------
        None : if no downsampling, otherwise it transforms the img into the 
        appropriate downsampled image space.

        '''
        
        
        if (self.downsampling_img == 'source'):
            # img -> ds is source to ds source image space
            
            # apply img to ds filter first
            if self.brp['downsampling-filter'] != 'false':
                print('    running downsampling filter..')
                self.img_ds_filter_pipeline = self.compute_adaptive_filter_img_ds()
                img_filt = self.apply_adaptive_filter(
                                    img, self.img_ds_filter_pipeline)
            else:
                img_filt = img
            
            # to move FROM SOURCE TO DS, need the src -> tar ds pm files
            if self.src_tar_ds_pm == None:
                print('  loading source-to-downsampled transform parameters file : ' +
                      self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
                self.src_tar_ds_pm = self.load_pm_files(self.src_tar_ds_pm_path)
                if self.src_tar_ds_pm == None:
                    print("ERROR : src_tar_ds_pm files do not exist - run register() first")
            
            # transform all input images with transformix
            print('  transforming image..')
            print('    source-to-downsampled elastix pm file : ' + 
                    self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
            print('')
            print('========================================================================')
            print('')
            print('')
            img_t = self.transform_image(img_filt, self.src_tar_ds_pm)
            return img_t
            
            
        elif (self.downsampling_img == 'target'):
            # img -> ds is target ti ds target image space
            
            # apply img to ds filter first
            if self.brp['downsampling-filter'] != 'false':
                print('    running downsampling filter..')
                self.img_ds_filter_pipeline = self.compute_adaptive_filter_img_ds()
                img_filt = self.apply_adaptive_filter(
                                    img, self.img_ds_filter_pipeline)
            else:
                img_filt = img
            
            # to move FROM TARGET TO DS, need the tar -> src ds pm files
            if self.tar_src_ds_pm == None:
                print('  loading target-to-downsampled transform parameters file : ' +
                      self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
                self.tar_src_ds_pm = self.load_pm_files(self.tar_src_ds_pm_path)
                if self.tar_src_ds_pm == None:
                    print("ERROR : tar_src_ds_pm files do not exist - run register() first")
            
            # transform all input images with transformix
            print('  transforming image..')
            print('    target-to-downsampled elastix pm file : ' + 
                    self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
            print('')
            print('========================================================================')
            print('')
            print('')
            img_t = self.transform_image(img_filt, self.tar_src_ds_pm)
            return img_t
            
            
        elif (self.downsampling_img == 'none'):
            return None # cannot move as no downsampling defined!
        
        
    
    
    
    def move_anno_img_ds(self, img):
        '''
        Move annotation from raw space to downsampled image space
        
        This depends which image has been downsampled (source or target).  If no 
        downsampling, this method returns None.
        
        Downsampling images are first filtered according to the 
        downsampling-filter parameter in the brainregister parameters file.

        Parameters
        ----------
        img : SITK Image
            Assumed this image is in the raw image space.

        Returns
        -------
        None : if no downsampling, otherwise it transforms the img into the 
        appropriate downsampled image space.

        '''
        
        
        if (self.downsampling_img == 'source'):
            # img -> ds is source to ds source image space
            
            # apply img to ds filter first
            #if self.brp['downsampling-filter'] != 'false':
            #    print('    running downsampling filter..')
            #    self.img_ds_filter_pipeline = self.compute_adaptive_filter_img_ds()
            #    img_filt = self.apply_adaptive_filter(
            #                        img, self.img_ds_filter_pipeline)
            #else:
            #    img_filt = img
            
            # to move FROM SOURCE TO DS, need the src -> tar ds pm files
            if self.src_tar_ds_pm_anno == None:
                print('  loading source-to-downsampled transform parameters file : ' +
                      self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
                self.src_tar_ds_pm = self.load_pm_files(self.src_tar_ds_pm_path)
                if self.src_tar_ds_pm == None:
                    print("ERROR : src_tar_ds_pm files do not exist - run register() first")
                self.src_tar_ds_pm_anno = self.edit_pms_nearest_neighbour(self.src_tar_ds_pm)
            
            # transform all input images with transformix
            print('  transforming annotation image..')
            print('    source-to-downsampled elastix pm file : ' + 
                    self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
            print('')
            print('========================================================================')
            print('')
            print('')
            anno_t = self.transform_image(img, self.src_tar_ds_pm_anno)
            return anno_t
            
            
        elif (self.downsampling_img == 'target'):
            # img -> ds is target ti ds target image space
            
            # apply img to ds filter first
            #if self.brp['downsampling-filter'] != 'false':
            #    print('    running downsampling filter..')
            #    self.img_ds_filter_pipeline = self.compute_adaptive_filter_img_ds()
            #    img_filt = self.apply_adaptive_filter(
            #                        img, self.img_ds_filter_pipeline)
            #else:
            #    img_filt = img
            
            # to move FROM TARGET TO DS, need the tar -> src ds pm files
            if self.tar_src_ds_pm_anno == None:
                print('  loading target-to-downsampled transform parameters file : ' +
                      self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
                self.tar_src_ds_pm = self.load_pm_files(self.tar_src_ds_pm_path)
                if self.tar_src_ds_pm == None:
                    print("ERROR : tar_src_ds_pm files do not exist - run register() first")
                self.tar_src_ds_pm_anno = self.edit_pms_nearest_neighbour(self.tar_src_ds_pm)
            
            # transform all input images with transformix
            print('  transforming annotation image..')
            print('    target-to-downsampled elastix pm file : ' + 
                    self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
            print('')
            print('========================================================================')
            print('')
            print('')
            anno_t = self.transform_image(img, self.tar_src_ds_pm_anno)
            return anno_t
            
            
        elif (self.downsampling_img == 'none'):
            return None # cannot move as no downsampling defined!
        
        
    
    
    def move_image_ds_img(self, img):
        '''
        Move from downsampled space to the raw image space
        
        This depends which image has been downsampled (source or target).  If no 
        downsampling, this method returns None.

        Parameters
        ----------
        img : SITK Image
            Assumed this image is in the downsampled image space.

        Returns
        -------
        None : if no downsampling, otherwise it transforms the img into the 
        appropriate rawimage space.

        '''
        
        
        if (self.downsampling_img == 'source'):
            # ds -> img is ds to source image space
            
            # to move FROM DS TO SOURCE, need the tar -> src ds pm files
            if self.tar_src_ds_pm == None:
                print('  loading downsampled-to-source transform parameters file : ' +
                      self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
                self.tar_src_ds_pm = self.load_pm_files(self.tar_src_ds_pm_path)
                if self.tar_src_ds_pm == None:
                    print("ERROR : tar_src_ds_pm files do not exist - run register() first")
            
            # transform all input images with transformix
            print('  transforming image..')
            print('    downsampled-to-source elastix pm file : ' + 
                    self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
            print('')
            print('========================================================================')
            print('')
            print('')
            img_t = self.transform_image(img, self.tar_src_ds_pm)
            return img_t
            
            
        elif (self.downsampling_img == 'target'):
            # ds -> ims is ds to target image space
            
            # to move FROM DS TO TARGET, need the src -> tar ds pm files
            if self.src_tar_ds_pm == None:
                print('  loading downsampled-to-target transform parameters file : ' +
                      self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
                self.src_tar_ds_pm = self.load_pm_files(self.src_tar_ds_pm_path)
                if self.src_tar_ds_pm == None:
                    print("ERROR : src_tar_ds_pm files do not exist - run register() first")
            
            # transform all input images with transformix
            print('  transforming image..')
            print('    downsampled-to-target elastix pm file : ' + 
                    self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
            print('')
            print('========================================================================')
            print('')
            print('')
            img_t = self.transform_image(img, self.src_tar_ds_pm)
            return img_t
            
        
        elif (self.downsampling_img == 'none'):
            return None # cannot move as no downsampling defined!
        
        
    
    
    
    def move_anno_ds_img(self, img):
        '''
        Move annotation from downsampled space to the raw image space
        
        This depends which image has been downsampled (source or target).  If no 
        downsampling, this method returns None.

        Parameters
        ----------
        img : SITK Image
            Assumed this image is in the downsampled image space.

        Returns
        -------
        None : if no downsampling, otherwise it transforms the img into the 
        appropriate rawimage space.

        '''
        
        
        if (self.downsampling_img == 'source'):
            # ds -> img is ds to source image space
            
            # to move FROM DS TO SOURCE, need the tar -> src ds pm files
            if self.tar_src_ds_pm_anno == None:
                print('  loading target-to-downsampled transform parameters file : ' +
                      self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
                self.tar_src_ds_pm = self.load_pm_files(self.tar_src_ds_pm_path)
                if self.tar_src_ds_pm == None:
                    print("ERROR : tar_src_ds_pm files do not exist - run register() first")
                self.tar_src_ds_pm_anno = self.edit_pms_nearest_neighbour(self.tar_src_ds_pm)
            
            # transform all input images with transformix
            print('  transforming image..')
            print('    downsampled-to-source elastix pm file : ' + 
                    self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
            print('')
            print('========================================================================')
            print('')
            print('')
            anno_t = self.transform_image(img, self.tar_src_ds_pm_anno)
            return anno_t
            
            
        elif (self.downsampling_img == 'target'):
            # ds -> ims is ds to target image space
            
            # to move FROM DS TO TARGET, need the src -> tar ds pm files
            if self.src_tar_ds_pm_anno == None:
                print('  loading source-to-downsampled transform parameters file : ' +
                      self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
                self.src_tar_ds_pm = self.load_pm_files(self.src_tar_ds_pm_path)
                if self.src_tar_ds_pm == None:
                    print("ERROR : src_tar_ds_pm files do not exist - run register() first")
                self.src_tar_ds_pm_anno = self.edit_pms_nearest_neighbour(self.src_tar_ds_pm)
            
            # transform all input images with transformix
            print('  transforming image..')
            print('    downsampled-to-target elastix pm file : ' + 
                    self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
            print('')
            print('========================================================================')
            print('')
            print('')
            anno_t = self.transform_image(img, self.src_tar_ds_pm)
            return anno_t
            
        
        elif (self.downsampling_img == 'none'):
            return None # cannot move as no downsampling defined!
        
        
    
    
    
    def get_template_ds(self):
        
        if (self.downsampling_img == 'source'):
            # template_ds is source_template_ds!
            
            if self.source_template_path_ds.exists() == False: # only transform if the output does not exist
                
                if self.source_template_img_ds == None: # and if the output image is not already loaded!
                    # TRANSFORM : will transform sample template to ds space
                    
                    if self.source_template_img == None:
                        print('  loading source template image : ' + 
                          self.get_relative_path(self.source_template_path) )
                        self.source_template_img = self.load_image(self.source_template_path)
                    
                    
                    if self.src_tar_ds_pm == None:
                        print('  loading source-to-downsampled transform parameters file : ' +
                              self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
                        self.src_tar_ds_pm = self.load_pm_files(self.src_tar_ds_pm_path)
                        if self.src_tar_ds_pm == None:
                            print("ERROR : src_tar_ds_pm files do not exist - run register() first")
                    
                    
                    # apply downsampling filter - if requested in brp
                    if self.brp['downsampling-filter'] != 'false':
                        print('  running source to downsampled filter..')
                        self.img_ds_filter_pipeline = self.compute_adaptive_filter_img_ds()
                        self.source_template_img = self.apply_adaptive_filter(
                                                    self.source_template_img, 
                                                    self.img_ds_filter_pipeline)
                    
                    # transform all input images with transformix
                    print('  transforming source template image..')
                    print('    image : ' + 
                            self.get_relative_path(self.source_template_path) )
                    print('    source-to-downsampled elastix pm file : ' + 
                            self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.source_template_img_ds = self.transform_image(
                                                    self.source_template_img, 
                                                    self.src_tar_ds_pm)
                    return self.source_template_img_ds
                    
                else:
                    print('  downsampled source template image exists : returning image' )
                    return self.source_template_img_ds
            
            else:
                print('  downsampled source template image exists - loading image..')
                self.source_template_img_ds = self.load_image(self.source_template_path_ds)
                return self.source_template_img_ds
            
            
        if (self.downsampling_img == 'target'):
            # template_ds is target_template_ds!
            
            if self.target_template_path_ds.exists() == False: # only transform if the output does not exist
                
                if self.target_template_img_ds == None: # and if the output image is not already loaded!
                    # TRANSFORM : will transform sample template to ds space
                    
                    if self.target_template_img == None:
                        print('  loading target template image : ' + 
                          self.get_relative_path(self.target_template_path) )
                        self.target_template_img = self.load_image(self.target_template_path)
                    
                    
                    if self.tar_src_ds_pm == None:
                        print('  loading target-to-downsampled transform parameters file : ' +
                              self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
                        self.tar_src_ds_pm = self.load_pm_files(self.tar_src_ds_pm_path)
                        if self.tar_src_ds_pm == None:
                            print("ERROR : tar_src_ds_pm files do not exist - run register() first")
                    
                    
                    # apply downsampling filter - if requested in brp
                    if self.brp['downsampling-filter'] != 'false':
                        print('  running target to downsampled filter..')
                        self.img_ds_filter_pipeline = self.compute_adaptive_filter_img_ds()
                        self.target_template_img = self.apply_adaptive_filter(
                                                    self.target_template_img, 
                                                    self.img_ds_filter_pipeline)
                    
                    # transform all input images with transformix
                    print('  transforming target template image..')
                    print('    image : ' + 
                            self.get_relative_path(self.target_template_path) )
                    print('    target-to-downsampled elastix pm file : ' + 
                            self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.target_template_img_ds = self.transform_image(
                                                    self.target_template_img, 
                                                    self.tar_src_ds_pm)
                    return self.target_template_img_ds
                    
                else:
                    print('  downsampled target template image exists : returning image' )
                    return self.target_template_img_ds
            
            else:
                print('  downsampled target template image exists - loading image..')
                self.target_template_img_ds = self.load_image(self.target_template_path_ds)
                return self.target_template_img_ds
            
        
    
    
    
    
    def generate_ds_scaling_param_files(self):
        
        if self.downsampling_img =='source':
            # downsampling from SOURCE TO TARGET : compute source <-> downsampled spaces
            
            if self.src_tar_ds_pm_path_exists() == False:
                
                print('  defining source to downsampled scaling parameters..')
                self.src_tar_ds_pm = self.get_img_ds_scaling()
                
                print('  saving source-to-downsampled transform parameters file : ')
                print('    '+self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
                self.save_img_ds_pm_file()
                
            else:
                
                print('  loading source-to-downsampled transform parameters file : ')
                print('    '+self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
                self.src_tar_ds_pm = self.load_pm_files(self.src_tar_ds_pm_path)
            
            
            if self.tar_src_ds_pm_path_exists() == False:
                
                print('  defining downsampled to source scaling parameters..')
                self.tar_src_ds_pm = self.get_ds_img_scaling()
                
                print('  saving downsampled-to-source transform parameters file : ')
                print('    '+self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
                self.save_ds_img_pm_file()
                
            else:
                
                print('  loading downsampled-to-source transform parameters file : ')
                print('    '+self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
                self.tar_src_ds_pm = self.load_pm_files(self.tar_src_ds_pm_path)
            
            print('')
            
            
            
        elif self.downsampling_img =='target':
            # downsampling from TARGET TO SOURCE : compute target <-> downsampled spaces
            
            if self.tar_src_ds_pm_path_exists() == False:
                
                print('  defining target to downsampled scaling parameters..')
                self.tar_src_ds_pm = self.get_img_ds_scaling()
                
                print('  saving target-to-downsampled transform parameters file : ' +
                          self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
                self.save_img_ds_pm_file()
                
            else:
                
                print('  loading target-to-downsampled transform parameters file : ' +
                          self.get_relative_path(self.tar_src_ds_pm_path[0] ) )
                self.tar_src_ds_pm = self.load_pm_files(self.tar_src_ds_pm_path)
            
            
            if self.src_tar_ds_pm_path_exists() == False:
                
                print('  defining downsampled to target scaling parameters..')
                self.src_tar_ds_pm = self.get_ds_img_scaling()
                
                print('  saving downsampled-to-target transform parameters file : ' +
                          self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
                self.save_ds_img_pm_file()
                
            else:
                
                print('  loading downsampled-to-target transform parameters file : ' +
                          self.get_relative_path(self.src_tar_ds_pm_path[0] ) )
                self.src_tar_ds_pm = self.load_pm_files(self.src_tar_ds_pm_path)
            
            print('')
            
    
    
    
    def  get_source_target_scale_factors(self):
        
        #str(self.target_string+'-template-resolution')
        # round to 6 dp - used by elastix!
        s2c = {key: round( 
            self.brp['source-template-resolution'][key] / 
            self.ccfp[str(self.target_string+'-template-resolution')].get(key, 0), 6 )
                            for key in self.brp['source-template-resolution'].keys()}
        
        # scale-factors in XYZ ccf -> sample
          # round to 6 dp - used by elastix!
        c2s = {key: round(
            self.ccfp[str(self.target_string+'-template-resolution')][key] / 
            self.brp['source-template-resolution'].get(key, 0), 6 )
                            for key in self.ccfp[str(self.target_string+
                                                '-template-resolution')].keys()}
        
        #scale_matrix = np.zeros((4, 4))
        #scale_matrix[0,0] = s2c['x-um']
        #scale_matrix[1,1] = s2c['y-um']
        #scale_matrix[2,2] = s2c['z-um']
        #scale_matrix[3,3] = 1 # to set the homogenous coordinate!
        
        #at = sitk.AffineTransform(3)
         # this works because translation is (0,0,0) - so can use the LAST ROW!
        #at.SetParameters( tuple( np.reshape(scale_matrix[0:4,0:3], (1,12))[0] ) )
        
        return s2c, c2s
        
    
    
    def compute_adaptive_filter_img_ds(self):
        
        if (self.downsampling_img == 'source'):
            # target-to-source resolution diff. used to compute filter radius
            # Median of res. diff for smoothed downsampling
            return ImageFilterPipeline(
                    str("M,"+
                    str(round( (self.t2s['x-um'] ) / 2)) + ',' +
                    str(round( (self.t2s['y-um'] ) / 2)) + ',' +
                    str(round( (self.t2s['z-um'] ) / 2)) ) )
        
        if (self.downsampling_img == 'target'):
            # source-to-target resolution diff. used to comptue filter radius
            return ImageFilterPipeline(
                str("M,"+
                str(round( (self.s2t['x-um']) / 2)) + ',' +
                str(round( (self.s2t['y-um']) / 2)) + ',' +
                str(round( (self.s2t['z-um']) / 2)) )  )
        
    
    
    
    
    
    
    def get_img_ds_scaling(self):
        
        if self.downsampling_img =='source':
            # downsampling the source image : source -> downsampled (target res.)
            
            img_ds_pm = sitk.ReadParameterFile(
                        os.path.join(BRAINREGISTER_MODULE_DIR, 'resources',
                                          'transformix-parameter-files', 
                                          '00_scaling.txt') )
            # see keys with list(img_ds_pm)
            # see contents of keys with img_ds_pm['key']
            
            # edit TransformParameters to correct tuple
             # use t2s - as the registration is FROM fixed TO moving!!!
            img_ds_pm['TransformParameters'] = tuple( 
                [str("{:.6f}".format(self.t2s['x-um'])), 
                 '0.000000', '0.000000','0.000000', 
                 str("{:.6f}".format(self.t2s['y-um'])), 
                 '0.000000','0.000000','0.000000', 
                 str("{:.6f}".format(self.t2s['z-um'])), 
                 '0.000000','0.000000','0.000000'] )
            
            # AND edit the Size to correct tuple
             # here want to use s2t - as this defines the size of the final FIXED image!
            img_ds_pm['Size'] = tuple( 
                [str("{:.6f}".format( round(
                     self.brp['source-template-size']['x'] * self.s2t['x-um']) ) ), 
                 str("{:.6f}".format( round(
                     self.brp['source-template-size']['y'] * self.s2t['y-um']) ) ),
                 str("{:.6f}".format( round(
                     self.brp['source-template-size']['z'] * self.s2t['z-um']))) ] )
            
            # set the output format
            img_ds_pm['ResultImageFormat'] = tuple( [ self.brp['downsampling-save-image-type'] ] )
            
            img_ds_pm = [img_ds_pm]
            # wrap in list so this works with transform_image like any other set pof parameter maps!
            
            return img_ds_pm
            
            
        elif self.downsampling_img =='target':
            # downsampling the target image : target -> downsampled (source res.)
            
            img_ds_pm = sitk.ReadParameterFile(
                        os.path.join(BRAINREGISTER_MODULE_DIR, 'resources',
                                          'transformix-parameter-files', 
                                          '00_scaling.txt') )
            # see keys with list(img_ds_pm)
            # see contents of keys with img_ds_pm['key']
            
            # edit TransformParameters to correct tuple
             # use s2t - as the registration is FROM fixed TO moving!!!
            img_ds_pm['TransformParameters'] = tuple( 
                [str("{:.6f}".format(self.s2t['x-um'])), 
                 '0.000000', '0.000000','0.000000', 
                 str("{:.6f}".format(self.s2t['y-um'])), 
                 '0.000000','0.000000','0.000000', 
                 str("{:.6f}".format(self.s2t['z-um'])), 
                 '0.000000','0.000000','0.000000'] )
            
            # AND edit the Size to correct tuple
             # here want to use t2s - as this defines the size of the final FIXED image!
            img_ds_pm['Size'] = tuple( 
                [str("{:.6f}".format( round(
                    self.ccfp[str(self.target_string+'-template-size')]['x'] 
                      * self.t2s['x-um']) ) ), 
                 str("{:.6f}".format( round(
                     self.ccfp[str(self.target_string+'-template-size')]['y'] 
                       * self.t2s['y-um']) ) ),
                 str("{:.6f}".format( round(
                     self.ccfp[str(self.target_string+'-template-size')]['z'] 
                       * self.t2s['z-um']))) ] )
            
            # set the output format
            img_ds_pm['ResultImageFormat'] = tuple( [ self.brp['downsampling-save-image-type'] ] )
            
            img_ds_pm = [img_ds_pm]
            # wrap in list so this works with transform_image like any other set pof parameter maps!
            
            return img_ds_pm
        else:
            return None
    
    
    
    def get_ds_img_scaling(self):
        
        if self.downsampling_img =='source':
            # downsampling the source image : downsampled (target res.) -> source
            ds_img_pm = sitk.ReadParameterFile(
                        os.path.join(BRAINREGISTER_MODULE_DIR, 'resources',
                                          'transformix-parameter-files', 
                                          '00_scaling.txt') )
            # see keys with list(ds_img_pm)
            # see contents of keys with ds_img_pm['key']
            
            # edit TransformParameters to correct tuple
             # use s2c - as the registration is FROM fixed TO moving!!!
            ds_img_pm['TransformParameters'] = tuple( 
                [str("{:.6f}".format(self.s2t['x-um'])), 
                 '0.000000', '0.000000','0.000000', 
                 str("{:.6f}".format(self.s2t['y-um'])), 
                 '0.000000','0.000000','0.000000', 
                 str("{:.6f}".format(self.s2t['z-um'])), 
                 '0.000000','0.000000','0.000000'] )
            
            # AND edit the Size to correct tuple
             # here want to use source template size - as this defines the size of the final FIXED image!
            ds_img_pm['Size'] = tuple( 
                [str("{:.6f}".format( round( self.brp['source-template-size']['x'] ))), 
                 str("{:.6f}".format( round( self.brp['source-template-size']['y'] ))),
                 str("{:.6f}".format( round( self.brp['source-template-size']['z'] ))) ] )
            
            # set the output format
            ds_img_pm['ResultImageFormat'] = tuple( [ self.brp['downsampling-save-image-type'] ] )
            
            ds_img_pm = [ds_img_pm]
            # wrap in list so this works with transform_image like any other set pof parameter maps!
            
            return ds_img_pm
        
    
    
    
    def save_image(self, image, path):
        
        # save with simpleITK - much FASTER even for nrrd images!
        sitk.WriteImage(
            image,   # sitk image
            str(path), # dir plus file name
            True # useCompression set to TRUE
            )
        
        
    
    
    def load_image(self, path):
        img = sitk.ReadImage(str(path))
        img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
        return img
    
    
    
    def load_transform_anno_img_ds(self, anno_path):
        
        img = self.load_image(anno_path)
        return self.move_anno_img_ds(img)
    

    
    def load_transform_image_img_ds(self, image_path):
        
        img = self.load_image(image_path)
        return self.move_image_img_ds(img)
        
    
    
    
    
    def transform_image(self, template_img, pm_list):
        
        transformixImageFilter = sitk.TransformixImageFilter()
        
        # add the first PM with Set
        transformixImageFilter.SetTransformParameterMap(pm_list[0])
        if len(pm_list) > 1: # then any subsequent ones with Add
            for i in range(1,len(pm_list)):
                transformixImageFilter.AddTransformParameterMap(pm_list[i])
        
        transformixImageFilter.SetMovingImage(template_img)
        
        transformixImageFilter.Execute()
        
        img = transformixImageFilter.GetResultImage()
        img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
        
        
        print('')
        print('========================================================================')
        print('')
        print('')
        
        # cast to the original image bitdepth
        # output is 32-bit float - convert this to the ORIGINAL image type!
        img = self.cast_image(template_img, img)
        
        
        return img
        
    
    
    def cast_image(self, sample_template_img, sample_template_ds):

        # get the minimum and maximum values in sample_template_img
        minMax = sitk.MinimumMaximumImageFilter()
        minMax.Execute(sample_template_img)
        
        # cast with numpy - as sitk casting has weird rounding errors..?
        sample_template_ds_np = sitk.GetArrayFromImage(sample_template_ds)
        
        # first rescale the pixel values to those in the original matrix
        # THIS IS NEEDED as sometimes the rescaling produces values above or below
        # the ORIGINAL IMAGE - clearly this is an error, so just crop the pixel values
        # check the number of pixels below the Minimum for example:
        #np.count_nonzero(sample_template_ds_np < minMax.GetMinimum())
        
        sample_template_ds_np[ 
            sample_template_ds_np < 
            minMax.GetMinimum() ] = minMax.GetMinimum()
        
        sample_template_ds_np[ 
            sample_template_ds_np > 
            minMax.GetMaximum() ] = minMax.GetMaximum()
        
        # NO NEED TO CAST NOW - this can be incorrect as if one pixel is aberrantly set below
        # 0 by a long way by registration quirks, this permeates into this casting, 
        # where the 0 pixels are artifically pushed up
        #sample_template_ds_cast = np.interp(
        #    sample_template_ds_np, 
        #    ( sample_template_ds_np.min(), sample_template_ds_np.max() ), 
        #    ( minMax.GetMinimum(), minMax.GetMaximum() ) 
        #        )
        
        # then CONVERT matrix to correct datatype
        if sample_template_img.GetPixelIDTypeAsString() == '16-bit signed integer':
            sample_template_ds_np = sample_template_ds_np.astype('int16')
            
        elif sample_template_img.GetPixelIDTypeAsString() == '8-bit signed integer':
            sample_template_ds_np = sample_template_ds_np.astype('int8')
            
        elif sample_template_img.GetPixelIDTypeAsString() == '8-bit unsigned integer':
            sample_template_ds_np = sample_template_ds_np.astype('uint8')
            
        elif sample_template_img.GetPixelIDTypeAsString() == '16-bit unsigned integer':
            sample_template_ds_np = sample_template_ds_np.astype('uint16')
            
        else: # default cast to unsigned 16-bit
            sample_template_ds_np = sample_template_ds_np.astype('uint16')
        
        # discard the np array
        #sample_template_ds_np = None
        
        img = sitk.GetImageFromArray( sample_template_ds_np )
        img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
        return img
        

    
    
    def save_img_ds_pm_file(self):
        
        if self.downsampling_img =='source':
            
            if self.src_tar_ds_pm_path_exists() == False:
                
                sitk.WriteParameterFile(self.src_tar_ds_pm[0], 
                                         str(self.src_tar_ds_pm_path[0]) )
                
            
        elif self.downsampling_img =='target':
            
            if self.tar_src_ds_pm_path_exists() == False:
                
                sitk.WriteParameterFile(self.tar_src_ds_pm[0], 
                                         str(self.tar_src_ds_pm_path[0]) )
                
            
        
    
    
    
    
    
    def save_ds_img_pm_file(self):
        
        if self.downsampling_img =='source':
            
            if self.tar_src_ds_pm_path_exists() == False:
                
                sitk.WriteParameterFile(self.tar_src_ds_pm[0], 
                                         str(self.tar_src_ds_pm_path[0]) )
                
            
        elif self.downsampling_img =='target':
            
            if self.src_tar_ds_pm_path_exists() == False:
                
                sitk.WriteParameterFile(self.src_tar_ds_pm[0], 
                                         str(self.src_tar_ds_pm_path[0]) )
        
        
        
    
    
    
    
    
    def transform_save_high_ds_template(self):
        
        if self.downsampling_img == 'source':
            
            if self.brp['source-to-target-downsampling-save-template'] == True:
                
                if self.source_template_path_ds.exists() == False:
                    self.source_template_img_ds = self.get_template_ds()
                    self.save_template_ds()
                    # DISCARD the template_img - as this can be a large file, best to discard!
                    self.source_template_img = None
                    garbage = gc.collect() # run garbage collection to ensure memory is freed
                else:
                    print('')
                    print('  source template in downsampled space exists..')
                    print('')
            else:
                print('')
                print('  transforming and saving source template to ds : not requested')
                print('')
            
            
        elif self.downsampling_img == 'target':
            
            if self.brp['target-to-source-downsampling-save-template'] == True:
                
                if self.target_template_path_ds.exists() == False:
                    self.target_template_img_ds = self.get_template_ds()
                    self.save_template_ds()
                    self.target_template_img = None
                    garbage = gc.collect() # run garbage collection to ensure memory is freed
                else:
                    print('')
                    print('  target template in downsampled space exists..')
                    print('')
            else:
                print('')
                print('  transforming and saving target template to ds : not requested')
                print('')
        
    
    
    
    
    def transform_save_high_ds_anno(self ):
        
        if (self.downsampling_img == 'source'):
            #source-to-target-downsampling-save-annotations
            if self.brp['source-to-target-downsampling-save-annotations'] == True:
                # now transform and save each sample annotation
                if self.source_anno_path != []:
                    print('')
                    print('  transforming and saving source annotations to ds..')
                    
                    for i, s in enumerate(self.source_anno_path):
                        
                        self.process_anno_ds(i)
                    
                else:
                    print('')
                    print('  transforming and saving source annotations to ds : no annotations to process')
                    print('')
            else:
                print('')
                print('  transforming and saving source annotations to ds : not requested')
                print('')
                
            
            
        elif (self.downsampling_img == 'target'):
            #target-to-source-downsampling-save-annotations
            if self.brp['target-to-source-downsampling-save-annotations'] == True:
                # now transform and save each sample annotation
                if self.target_anno_path != []:
                    print('')
                    print('  transforming and saving target annotations to ds..')
                    
                    for i, s in enumerate(self.target_anno_path):
                        
                        self.process_anno_ds(i)
                    
                else:
                    print('')
                    print('  transforming and saving target annotations to ds : no annotations to process')
                    print('')
            else:
                print('')
                print('  transforming and saving target annotations to ds : not requested')
                print('')
                
            
        
    
    
    
    
    def process_anno_ds(self, index):
        
        if (self.downsampling_img == 'source'):
        #source_anno images
            if (self.source_anno_path_ds != []):
                
                if self.source_anno_path_ds[index].exists() == False:
                    print('')
                    print('    loading source annotation image : ' 
                           + self.get_relative_path(
                               self.source_anno_path_ds[index]) )
                    
                    anno_ds = self.load_transform_anno_img_ds(
                                    self.source_anno_path_ds[index] )
                    
                    self.save_anno_ds(index, anno_ds)
                    
                else:
                    print('    downsampled source annotation image exists : ' 
                           + self.get_relative_path( self.source_anno_path_ds[index]) )
                    
                
            else:
                print('    no source annotation images to downsample..' )
                
                
        elif (self.downsampling_img == 'target'):
        #target_anno images
            if (self.target_anno_path_ds != []):
                
                if self.target_anno_path_ds[index].exists() == False:
                    print('')
                    print('    loading target annotation image : ' 
                           + self.get_relative_path(
                               self.target_anno_path_ds[index]) )
                    
                    anno_ds = self.load_transform_anno_img_ds(
                                    self.target_anno_path_ds[index] )
                    
                    self.save_anno_ds(index, anno_ds)
                    
                else:
                    print('    downsampled target annotation image exists : ' 
                           + self.get_relative_path( self.target_anno_path_ds[index]) )
                    
                
            else:
                print('    no target annotation images to downsample..' )
        
        
    
    
    
    
    def transform_save_high_ds_images(self ):
        
        if (self.downsampling_img == 'source'):
            #source-to-target-downsampling-save-images
            if self.brp['source-to-target-downsampling-save-images'] == True:
                # now transform and save each sample image
                
                if self.source_image_path != []:
                    
                    print('')
                    print('  transforming and saving source images to ds..')
                    for i, s in enumerate(self.source_image_path):
                        print('  source image ' + str(i))
                        self.process_image_ds(i)
                    
                else:
                    print('')
                    print('  transforming and saving source images to ds : no images to process')
                    print('')
            else:
                print('')
                print('  transforming and saving source images to ds : not requested')
                print('')
                
            
        elif (self.downsampling_img == 'target'):
            #target-to-source-downsampling-save-images
            if self.brp['target-to-source-downsampling-save-images'] == True:
                # now transform and save each sample image
                
                if self.target_image_paths != []:
                    print('')
                    print('  transforming and saving target images to ds..')
                    for i, s in enumerate(self.target_image_paths):
                        print('  target image ' + str(i))
                        self.process_image_ds(i)
                    
                else:
                    print('')
                    print('  transforming and saving target images to ds : no images to process')
                    print('')
            else:
                print('')
                print('  transforming and saving target images to ds : not requested')
                print('')
                
        
    
    
    
    def process_image_ds(self, index):
        
        if (self.downsampling_img == 'source'):
            # source_images
            if (self.source_image_path_ds is not None):
                
                if self.source_image_path_ds[index].exists() == False:
                    
                    print('')
                    print('    loading source image : ' 
                           + self.get_relative_path(
                               self.source_image_path[index]) )
                    
                    sample_ds = self.load_transform_image_img_ds(
                                 self.source_image_path[index] )
                    
                    self.save_image_ds(index, sample_ds)
                    
                else:
                    print('    downsampled source image exists : ' 
                           + self.get_relative_path( 
                               self.source_image_path_ds[index]) )
                    
                
            else:
                print('    no source images to downsample..' )
                
                
                
        if (self.downsampling_img == 'target'):
            # target_images
            if (self.target_image_paths_ds is not None):
                
                if self.target_image_paths_ds[index].exists() == False:
                    
                    print('')
                    print('    loading target image : ' 
                           + self.get_relative_path(
                               self.target_image_paths[index]) )
                    
                    sample_ds = self.load_transform_image_img_ds(
                                 self.target_image_paths[index] )
                    
                    self.save_image_ds(index, sample_ds)
                    
                else:
                    print('    downsampled target image exists : ' 
                           + self.get_relative_path( 
                               self.target_image_paths_ds[index]) )
                    
            else:
                print('    no target images to downsample..' )
                
            
        
    
    
    
    
    
    def save_anno_ds(self, index, sample_ds):
        
        if (self.downsampling_img == 'source'):
            # save to source anno image path
            if self.source_anno_path_ds[index].exists() == False:
                print('    saving downsampled image : ' 
                   + self.get_relative_path(self.source_anno_path_ds[index]) )
                self.save_image(sample_ds, self.source_anno_path_ds[index])
                
            
        elif (self.downsampling_img == 'target'):
            # save to target anno image path
            if self.target_anno_path_ds[index].exists() == False:
                print('    saving downsampled image : ' 
                   + self.get_relative_path(self.target_anno_path_ds[index]) )
                self.save_image(sample_ds, self.target_anno_path_ds[index])
                
            
        
    
    
    
    def save_image_ds(self, index, sample_ds):
        
        if (self.downsampling_img == 'source'):
            # source_images
            if self.source_image_path_ds[index].exists() == False:
                print('    saving source downsampled image : ' 
                   + self.get_relative_path(
                       self.source_image_path_ds[index]) )
                
                self.save_image(sample_ds, 
                                 self.source_image_path_ds[index] )
                
            
        elif (self.downsampling_img == 'target'):
            # target_images
            if self.target_image_paths_ds[index].exists() == False:
                print('    saving target downsampled image : ' 
                   + self.get_relative_path(
                       self.target_image_paths_ds[index]) )
                
                self.save_image(sample_ds, 
                                 self.target_image_paths_ds[index] )
        
    
    
    
    
    def register_source_to_target(self):
        
        print('')
        print('')
        print('================')
        print('SOURCE TO TARGET')
        print('================')
        print('')
        
        
        if self.src_tar_pm_files_exist() is False:
            # if the param files do not exist, generate them by registering
            # src template to tar template (using the correct downsampled stack!)
            
            
            if (self.downsampling_img == 'source'):
                # source image is downsampled to target img resolution
                # so use this to register to target img
                
                if self.source_template_img_ds == None:
                    
                    if self.source_template_path_ds.exists() == True:
                        
                        print('  loading ds source template image : ', 
                                        self.source_template_path_ds.name)
                        self.source_template_img_ds = self.load_image(self.source_template_path_ds)
                    else:
                        print('  ds source template image does not exist -'+
                                ' generating from source template')
                        self.source_template_img_ds = self.get_template_ds()
                
                
                if self.target_template_img == None:
                    
                    print('  loading target template image : '+ 
                                      self.target_template_path.name)
                    self.target_template_img = self.load_image(self.target_template_path)
                
                
                # apply source-to-target filter - if requested in brp and not performed already
                self.src_tar_prefiltering()
                    
                
                if self.src_tar_prefiltered == False: # if src_tar_filter is set to 'none'
                    # REGISTRATION - use unfiltered images
                    print('  registering source to target..')
                    print('    source : ' + 
                                self.get_relative_path(self.source_template_path_ds) )
                    print('    target : ' + 
                                self.get_relative_path(self.target_template_path) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.source_template_img_target = self.register_image(
                                                        self.source_template_img_ds, 
                                                        self.target_template_img, 
                                                        self.src_tar_ep )
                    
                elif self.src_tar_prefiltered == True:
                    # REGISTRATION - use filt images
                    print('  registering source to target after prefilter..')
                    print('    source : ' + 
                                self.get_relative_path(self.source_template_path_ds) )
                    print('    target : ' + 
                                self.get_relative_path(self.target_template_path) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.source_template_img_target_filt = self.register_image(
                                                        self.source_template_img_ds_filt, 
                                                        self.target_template_img_filt, 
                                                        self.src_tar_ep )
                
                print('  saving source to target parameter map file[s]..')
                self.save_pm_files( self.src_tar_pm_paths )
                
                
                
            if (self.downsampling_img == 'target'):
                # target image is downsampled to source img resolution
                # so use source to register to ds target img
                 
                if self.source_template_img == None:
                     
                     print('  loading source template image : '+ 
                                       self.source_template_path.name)
                     self.source_template_img = sitk.ReadImage( 
                                                 str(self.source_template_path) )
                     self.source_template_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
                
                
                if self.target_template_img_ds == None:
                    
                    if self.target_template_path_ds.exists() == True:
                        
                        print('  loading ds target template image : ', 
                                        self.target_template_path_ds.name)
                        self.target_template_img_ds = sitk.ReadImage( 
                                             str(self.target_template_path_ds) )
                        self.target_template_img_ds.SetSpacing( 
                                                        tuple([1.0, 1.0, 1.0]) )
                    else:
                        print('  ds target template image does not exist -'+
                                ' generating from target template')
                        self.target_template_img_ds = self.get_template_ds()
                
                
                # apply source-to-target filter - if requested in brp and not performed already
                self.src_tar_prefiltering()
                    
                
                if self.src_tar_prefiltered == False: # if src_tar_filter is set to 'none'
                    # REGISTRATION - use unfiltered images
                    print('  registering source to target..')
                    print('    source : ' + 
                                self.get_relative_path(self.source_template_path) )
                    print('    target : ' + 
                                self.get_relative_path(self.target_template_path_ds) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.source_template_img_target = self.register_image(
                                                        self.source_template_img, 
                                                        self.target_template_img_ds, 
                                                        self.src_tar_ep )
                    
                elif self.src_tar_prefiltered == True:
                    # REGISTRATION - use filt images
                    print('  registering source to target after prefilter..')
                    print('    source : ' + 
                                self.get_relative_path(self.source_template_path) )
                    print('    target : ' + 
                                self.get_relative_path(self.target_template_path_ds) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.source_template_img_target_filt = self.register_image(
                                                        self.source_template_img_filt, 
                                                        self.target_template_img_ds_filt, 
                                                        self.src_tar_ep )
                
                print('  saving source to target parameter map file[s]..')
                self.save_pm_files( self.src_tar_pm_paths )
                
                
                
            if (self.downsampling_img == 'none'):
                # target image is source img resolution
                # so use source to register to target img
                
                if self.source_template_img == None:
                    
                    print('  loading source template image : '+ 
                                      self.source_template_path.name)
                    self.source_template_img = sitk.ReadImage( 
                                                str(self.source_template_path) )
                    self.source_template_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
                
                
                if self.target_template_img == None:
                    
                    print('  loading target template image : '+ 
                                      self.target_template_path.name)
                    self.target_template_img = sitk.ReadImage( 
                                                str(self.target_template_path) )
                    self.target_template_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
                
                
                # apply source-to-target filter - if requested in brp and not performed already
                self.src_tar_prefiltering()
                    
                
                if self.src_tar_prefiltered == False: # if src_tar_filter is set to 'none'
                    # REGISTRATION - use unfiltered images
                    print('  registering source to target..')
                    print('    source : ' + 
                                self.get_relative_path(self.source_template_path) )
                    print('    target : ' + 
                                self.get_relative_path(self.target_template_path) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.source_template_img_target = self.register_image(
                                                        self.source_template_img, 
                                                        self.target_template_img, 
                                                        self.src_tar_ep )
                    
                elif self.src_tar_prefiltered == True:
                    # REGISTRATION - use filt images
                    print('  registering source to target after prefilter..')
                    print('    source : ' + 
                                self.get_relative_path(self.source_template_path) )
                    print('    target : ' + 
                                self.get_relative_path(self.target_template_path) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.source_template_img_target_filt = self.register_image(
                                                        self.source_template_img_filt, 
                                                        self.target_template_img_filt, 
                                                        self.src_tar_ep )
                
                print('  saving source to target parameter map file[s]..')
                self.save_pm_files( self.src_tar_pm_paths )
                
                
        else:
            print('  source to target parameter map file[s] already exist : No Registration')
            
            
    
    
    
    
    def register_target_to_source(self):
        
        print('')
        print('')
        print('================')
        print('TARGET TO SOURCE')
        print('================')
        print('')
        
        
        if self.tar_src_pm_files_exist() is False:
            # if the param files do not exist, generate them by registering
            # tar template to src template (using the correct downsampled stack!)
            
            
            if (self.downsampling_img == 'source'):
                # source image is downsampled to target img resolution
                # register target to downsampled source image
                
                if self.source_template_img_ds == None:
                    
                    if self.source_template_path_ds.exists() == True:
                        
                        print('  loading ds source template image : ', 
                                        self.source_template_path_ds.name)
                        self.source_template_img_ds = self.load_image(self.source_template_path_ds)
                    else:
                        print('  ds source template image does not exist -'+
                                ' generating from source template')
                        self.source_template_img_ds = self.get_template_ds()
                
                
                if self.target_template_img == None:
                    
                    print('  loading target template image : '+ 
                                      self.target_template_path.name)
                    self.target_template_img = self.load_image(self.target_template_path)
                
                
                # apply target-to-source filter - if requested in brp and not performed already
                self.tar_src_prefiltering()
                    
                
                if self.tar_src_prefiltered == False: # if src_tar_filter is set to 'none'
                    # REGISTRATION - use unfiltered images
                    print('  registering target to source..')
                    print('    target : ' + 
                                self.get_relative_path(self.target_template_path) )
                    print('    source : ' + 
                                self.get_relative_path(self.source_template_path_ds) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.target_template_img_source = self.register_image( 
                                                        self.target_template_img, 
                                                        self.source_template_img_ds, 
                                                        self.tar_src_ep )
                    
                elif self.tar_src_prefiltered == True:
                    # REGISTRATION - use filt images
                    print('  registering target to source after prefilter..')
                    print('    target : ' + 
                                self.get_relative_path(self.target_template_path) )
                    print('    source : ' + 
                                self.get_relative_path(self.source_template_path_ds) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.target_template_img_source_filt = self.register_image(
                                                        self.target_template_img_filt, 
                                                        self.source_template_img_ds_filt, 
                                                        self.tar_src_ep )
                
                print('  saving target to source parameter map file[s]..')
                self.save_pm_files( self.tar_src_pm_paths )
                
                
                
            if (self.downsampling_img == 'target'):
                # target image is downsampled to source img resolution
                # so use source to register to ds target img
                 
                if self.source_template_img == None:
                     
                     print('  loading source template image : '+ 
                                       self.source_template_path.name)
                     self.source_template_img = self.load_image(self.source_template_path)
                
                
                if self.target_template_img_ds == None:
                    
                    if self.target_template_path_ds.exists() == True:
                        
                        print('  loading ds target template image : ', 
                                        self.target_template_path_ds.name)
                        self.target_template_img_ds = self.load_image(self.target_template_path_ds)
                    else:
                        print('  ds target template image does not exist -'+
                                ' generating from target template')
                        self.target_template_img_ds = self.get_template_ds()
                
                
                # apply target-to-source filter - if requested in brp and not performed already
                self.tar_src_prefiltering()
                    
                
                if self.tar_src_prefiltered == False: # if src_tar_filter is set to 'none'
                    # REGISTRATION - use unfiltered images
                    print('  registering target to source..')
                    print('    target : ' + 
                                self.get_relative_path(self.target_template_path_ds) )
                    print('    source : ' + 
                                self.get_relative_path(self.source_template_path) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.target_template_img_source = self.register_image(
                                                        self.target_template_img_ds, 
                                                        self.source_template_img, 
                                                        self.tar_src_ep )
                    
                elif self.tar_src_prefiltered == True:
                    # REGISTRATION - use filt images
                    print('  registering target to source after prefilter..')
                    print('    target : ' + 
                                self.get_relative_path(self.target_template_path_ds) )
                    print('    source : ' + 
                                self.get_relative_path(self.source_template_path) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.target_template_img_source_filt = self.register_image(
                                                        self.target_template_img_ds_filt, 
                                                        self.source_template_img_filt, 
                                                        self.tar_src_ep )
                
                print('  saving source to target parameter map file[s]..')
                self.save_pm_files( self.tar_src_pm_paths )
                
                
                
            if (self.downsampling_img == 'none'):
                # target image is source img resolution
                # so use source to register to target img
                
                if self.source_template_img == None:
                    
                    print('  loading source template image : '+ 
                                      self.source_template_path.name)
                    self.source_template_img = self.load_image(self.source_template_path)
                
                
                if self.target_template_img == None:
                    
                    print('  loading target template image : '+ 
                                      self.target_template_path.name)
                    self.target_template_img = self.load_image(self.target_template_path)
                
                
                # apply target-to-source filter - if requested in brp and not performed already
                self.tar_src_prefiltering()
                    
                
                if self.tar_src_prefiltered == False: # if src_tar_filter is set to 'none'
                    # REGISTRATION - use unfiltered images
                    print('  registering target to source..')
                    print('    target : ' + 
                                self.get_relative_path(self.target_template_path) )
                    print('    source : ' + 
                                self.get_relative_path(self.source_template_path) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.target_template_img_source = self.register_image(
                                                        self.target_template_img, 
                                                        self.source_template_img, 
                                                        self.tar_src_ep )
                    
                elif self.tar_src_prefiltered == True:
                    # REGISTRATION - use filt images
                    print('  registering target to source after prefilter..')
                    print('    target : ' + 
                                self.get_relative_path(self.target_template_path) )
                    print('    source : ' + 
                                self.get_relative_path(self.source_template_path) )
                    print('')
                    print('========================================================================')
                    print('')
                    print('')
                    self.target_template_img_source_filt = self.register_image(
                                                        self.target_template_img_filt, 
                                                        self.source_template_img_filt, 
                                                        self.tar_src_ep )
                
                print('  saving source to target parameter map file[s]..')
                self.save_pm_files( self.tar_src_pm_paths )
                
                
        else:
            print('  target to source parameter map file[s] already exist : No Registration')
            
            
        
    
    
    
    
    
    def src_tar_prefiltering(self):
        
        if (self.downsampling_img == 'source'):
            # source image is downsampled to target img resolution
        
            if self.brp['source-to-target-filter'] != "none":
                
                print('  running source to target prefilter..')
                self.src_tar_filter_pipeline = self.compute_adaptive_filter(
                                            self.brp['source-to-target-filter'] )
                
                
                if self.source_template_img_ds_filt != None:
                    if self.src_tar_prefiltered: # already correctly filtered!
                        print('    ds source template')
                    else: # filter correctly
                        print('    ds source template')
                        self.source_template_img_ds_filt = self.apply_adaptive_filter(
                                                    self.source_template_img_ds, 
                                                    self.src_tar_filter_pipeline )
                else: # no filtered image exists!
                    print('    ds source template')
                    self.source_template_img_ds_filt = self.apply_adaptive_filter(
                                                self.source_template_img_ds, 
                                                self.src_tar_filter_pipeline )
                    
                
                if self.target_template_img_filt != None:
                    if self.src_tar_prefiltered: # already correctly filtered!
                        print('    target template')
                    else: # filter correctly
                        print('    target template')
                        self.target_template_img_filt = self.apply_adaptive_filter(
                                                    self.target_template_img, 
                                                    self.src_tar_filter_pipeline )
                else: # no filtered image exists!
                    print('    target template')
                    self.target_template_img_filt = self.apply_adaptive_filter(
                                                self.target_template_img, 
                                                self.src_tar_filter_pipeline )
                
                # set bools to indicate filtering
                self.src_tar_prefiltered = True
                self.tar_src_prefiltered = False
                
            else: # no src-to-tar filtering, log this
                print('  no source to target prefilter..')
                
                
                
        elif (self.downsampling_img == 'target'):
            # target image is downsampled to source img resolution
        
            if self.brp['source-to-target-filter'] != "none":
                
                print('  running source to target prefilter..')
                self.src_tar_filter_pipeline = self.compute_adaptive_filter(
                                            self.brp['source-to-target-filter'] )
                
                
                if self.source_template_img_filt != None:
                    if self.src_tar_prefiltered: # already correctly filtered!
                        print('    source template')
                    else: # filter correctly
                        print('    source template')
                        self.source_template_img_filt = self.apply_adaptive_filter(
                                                    self.source_template_img, 
                                                    self.src_tar_filter_pipeline )
                else: # no filtered image exists!
                    print('    source image')
                    self.source_template_img_filt = self.apply_adaptive_filter(
                                                self.source_template_img, 
                                                self.src_tar_filter_pipeline )
                    
                
                if self.target_template_img_filt != None:
                    if self.src_tar_prefiltered: # already correctly filtered!
                        print('    target template')
                    else: # filter correctly
                        print('    target template')
                        self.target_template_img_filt = self.apply_adaptive_filter(
                                                    self.target_template_img, 
                                                    self.src_tar_filter_pipeline )
                else: # no filtered image exists!
                    print('    target template')
                    self.target_template_img_filt = self.apply_adaptive_filter(
                                                self.target_template_img, 
                                                self.src_tar_filter_pipeline )
                
                # set bools to indicate filtering
                self.src_tar_prefiltered = True
                self.tar_src_prefiltered = False
                
            else: # no src-to-tar filtering, log this
                print('  no source to target prefilter..')
                
                
        elif (self.downsampling_img == 'none'):
            # target image & source img same resolution!
            # so no downsampling to use!
            if self.brp['source-to-target-filter'] != "none":
                
                print('  running source to target prefilter..')
                self.src_tar_filter_pipeline = self.compute_adaptive_filter(
                                            self.brp['source-to-target-filter'] )
                
                if self.source_template_img_filt != None:
                    if self.src_tar_prefiltered: # already correctly filtered!
                        print('    source template')
                    else: # filter correctly
                        print('    source template')
                        self.source_template_img_filt = self.apply_adaptive_filter(
                                                    self.source_template_img, 
                                                    self.src_tar_filter_pipeline )
                else: # no filtered image exists!
                    print('    source image')
                    self.source_template_img_filt = self.apply_adaptive_filter(
                                                self.source_template_img, 
                                                self.src_tar_filter_pipeline )
                    
                
                if self.target_template_img_ds_filt != None:
                    if self.src_tar_prefiltered: # already correctly filtered!
                        print('    ds target template') # just log as if filtering took place
                    else: # filter correctly
                        print('    ds target template')
                        self.target_template_img_ds_filt = self.apply_adaptive_filter(
                                                    self.target_template_img_ds, 
                                                    self.src_tar_filter_pipeline )
                else: # no filtered image exists!
                    print('    ds target template')
                    self.target_template_img_ds_filt = self.apply_adaptive_filter(
                                                self.target_template_img_ds, 
                                                self.src_tar_filter_pipeline )
                
                # set bools to indicate filtering
                self.src_tar_prefiltered = True
                self.tar_src_prefiltered = False
                
            else: # no src-to-tar filtering, log this
                print('  no source to target prefilter..')
                
                
    
    
    
    def tar_src_prefiltering(self):
        
        if self.brp['target-to-source-filter'] != "none":
            
            print('  running target to source prefilter..')
            self.tar_src_filter_pipeline = self.compute_adaptive_filter(
                                        self.brp['target-to-source-filter'] )
            
            # now run on images depending on which were downsampled
            
            if (self.downsampling_img == 'source'):
                # source image is downsampled to target img resolution
                
                
                if self.source_template_img_ds_filt != None:
                    if self.src_tar_prefiltered: # already correctly filtered!
                        print('    ds source template')
                    else: # filter correctly
                        print('    ds source template')
                        self.source_template_img_ds_filt = self.apply_adaptive_filter(
                                                    self.source_template_img_ds, 
                                                    self.tar_src_filter_pipeline )
                else: # no filtered image exists!
                    print('    ds source template')
                    self.source_template_img_ds_filt = self.apply_adaptive_filter(
                                                self.source_template_img_ds, 
                                                self.tar_src_filter_pipeline )
                    
                
                if self.target_template_img_filt != None:
                    if self.src_tar_prefiltered: # already correctly filtered!
                        print('    target template')
                    else: # filter correctly
                        print('    target template')
                        self.target_template_img_filt = self.apply_adaptive_filter(
                                                    self.target_template_img, 
                                                    self.tar_src_filter_pipeline )
                else: # no filtered image exists!
                    print('    target template')
                    self.target_template_img_filt = self.apply_adaptive_filter(
                                                self.target_template_img, 
                                                self.tar_src_filter_pipeline )
                
                # set bools to indicate filtering
                self.src_tar_prefiltered = False
                self.tar_src_prefiltered = True
                
                
                
                
            elif (self.downsampling_img == 'target'):
            # target image is downsampled to source img resolution
                
                
                if self.source_template_img_filt != None:
                    if self.src_tar_prefiltered: # already correctly filtered!
                        print('    source template')
                    else: # filter correctly
                        print('    source template')
                        self.source_template_img_filt = self.apply_adaptive_filter(
                                                    self.source_template_img, 
                                                    self.src_tar_filter_pipeline )
                else: # no filtered image exists!
                    print('    source image')
                    self.source_template_img_filt = self.apply_adaptive_filter(
                                                self.source_template_img, 
                                                self.src_tar_filter_pipeline )
                    
                
                if self.target_template_img_filt != None:
                    if self.src_tar_prefiltered: # already correctly filtered!
                        print('    target template')
                    else: # filter correctly
                        print('    target template')
                        self.target_template_img_filt = self.apply_adaptive_filter(
                                                    self.target_template_img, 
                                                    self.src_tar_filter_pipeline )
                else: # no filtered image exists!
                    print('    target template')
                    self.target_template_img_filt = self.apply_adaptive_filter(
                                                self.target_template_img, 
                                                self.src_tar_filter_pipeline )
                
                # set bools to indicate filtering
                self.src_tar_prefiltered = False
                self.tar_src_prefiltered = True
                
                
            elif (self.downsampling_img == 'none'):
                # target image & source img same resolution!
                # so no downsampling to use!
                
                if self.source_template_img_filt != None:
                    if self.src_tar_prefiltered: # already correctly filtered!
                        print('    source template')
                    else: # filter correctly
                        print('    source template')
                        self.source_template_img_filt = self.apply_adaptive_filter(
                                                    self.source_template_img, 
                                                    self.src_tar_filter_pipeline )
                else: # no filtered image exists!
                    print('    source image')
                    self.source_template_img_filt = self.apply_adaptive_filter(
                                                self.source_template_img, 
                                                self.src_tar_filter_pipeline )
                    
                
                if self.target_template_img_ds_filt != None:
                    if self.src_tar_prefiltered: # already correctly filtered!
                        print('    target template') # just log as if filtering took place
                    else: # filter correctly
                        print('    target template')
                        self.target_template_img_filt = self.apply_adaptive_filter(
                                                    self.target_template_img, 
                                                    self.src_tar_filter_pipeline )
                else: # no filtered image exists!
                    print('    target template')
                    self.target_template_img_filt = self.apply_adaptive_filter(
                                                self.target_template_img, 
                                                self.src_tar_filter_pipeline )
                
                # set bools to indicate filtering
                self.src_tar_prefiltered = False
                self.tar_src_prefiltered = True
                
        else: # no src-to-tar filtering, log this
            print('  no source to target prefilter..')
                
                
    
    
    
    def get_elastix_params(self, param_files):
        """
        Returns the elastix parameter map files as VectorOfParameterMap Object
        
        
        Returns
        -------
        parameterMapVector : VectorOfParameterMap
            Vector of Parameter Map files for use with elastix.

        """
        
        parameterMapVector = sitk.VectorOfParameterMap()
        
        for pf in param_files:
            
            if pf == 'brainregister:affine':
                pm = sitk.ReadParameterFile(
                         os.path.join(BRAINREGISTER_MODULE_DIR, 'resources', 
                                 'elastix-parameter-files', '01_affine.txt') )
                
            elif pf == 'brainregister:bspline':
                pm = sitk.ReadParameterFile(
                         os.path.join(BRAINREGISTER_MODULE_DIR, 'resources', 
                                 'elastix-parameter-files', '02_bspline.txt') )
                
            else: # open relative file specified in pf
                pm = sitk.ReadParameterFile( 
                      str(Path(os.path.join(str(self.brp_dir), pf)).resolve())
                )
            
            parameterMapVector.append(pm)
            
            
        return parameterMapVector
        
    
    
    def register_image(self, moving_img, fixed_img, parameter_map_vector):
        
        # perform elastix registration
        elastixImageFilter = sitk.ElastixImageFilter()
        
        elastixImageFilter.SetMovingImage(moving_img)
        elastixImageFilter.SetFixedImage(fixed_img)
        
        elastixImageFilter.SetParameterMap(parameter_map_vector)
        
        elastixImageFilter.Execute()
        
        # remove the registration logs
        reg_logs = [f for f in os.listdir('.') if 
                    os.path.isfile(f) & 
                    os.path.basename(f).startswith("IterationInfo.")]
        for rl in reg_logs:
            os.remove(rl)
            
        
        print('')
        print('========================================================================')
        print('')
        print('')
        
        # get the registered image
        img = elastixImageFilter.GetResultImage()
        img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
        return img
    
    
    
    def save_pm_files(self, pm_paths):
        
        # move TransformParameters files to pm_paths
        transform_params = [f for f in os.listdir('.') if os.path.isfile(f) & 
                            os.path.basename(f).startswith("TransformParameters.")]
        
        transform_params.sort() # into ASCENDING ORDER
        
        for i, tp in enumerate(transform_params):
            os.rename(tp, str(pm_paths[i]) )
        
        
    
    
    def load_pm_files(self, pm_paths ):
        
        if pm_paths[0].exists() == True: # assume if first pm file exists they all do!
            pms = []
            for pm in pm_paths:
                pms.append(sitk.ReadParameterFile( str(pm) ) )
            
            return pms
        else:
            return None # if doesnt exist return none - mainly for call in resolve_params()
        
    
    
    def src_tar_pm_files_exist(self):
        """
        Returns true only if all src_tar_pm files exist

        Returns
        -------
        None.

        """
        
        exists = True
        for pm in self.src_tar_pm_paths:
            if pm.exists() is False:
                exists = False
        
        return exists
        
    
    
    def tar_src_pm_files_exist(self):
        """
        Returns true only if all tar_src_pm files exist

        Returns
        -------
        None.

        """
        
        exists = True
        for pm in self.tar_src_pm_paths:
            if pm.exists() is False:
                exists = False
        
        return exists
        
    
    
    def compute_adaptive_filter(self, filter_string):
        
        if filter_string == 'brainregister:autofl-filter':
            # autofluorescence default filter is a radius 4 median filter
            return ImageFilterPipeline('M,4,4,4')
            # figure out how to COMPUTE an adaptive filter here?!
            
        elif filter_string == 'none':
            return None
            
        else:
            # syntax for user defining their own filter?
            # Writing in new Class ImageFilterPipeline
            return ImageFilterPipeline(filter_string)
        
    
    
    
    def apply_adaptive_filter(self, img, filter_pipeline):
        
        if filter_pipeline is not None:
            
            filter_pipeline.set_image(img)
            img = filter_pipeline.execute_pipeline()
            filter_pipeline.dereference_image() # remove ref to raw data
            
            return filter_pipeline.get_filtered_image()
        
        else:
            return img
    
    
    
    
    def transform_source_to_target(self):
        
        #if (self.downsampling_img == 'source'): 
        # NOT NEEDED as no refs to ds or raw image data/paths!
        
        if self.brp['source-to-target-save-template'] == True:
            
            if self.source_template_path_target.exists() == False:
                self.source_template_img_target = self.get_src_template_tar()
                self.save_src_template_tar()
            else:
                print('')
                print('  saving source template to target : image exists')
                print('')
            
        else:
            print('')
            print('  saving source template to target : not requested')
            print('')
        
        
        if self.brp['source-to-target-save-annotations'] == True:
            
            
            if self.source_anno_path_target != []: # not a blank list
                print('')
                print('  source annotations to target : ')
                print('')
                for i,im_ds in enumerate(self.source_anno_path_target):
                    # source_anno_path + _ds + _target all are SAME LENGTH!
                    print('  annotation image ' + str(i))
                    anno_img = self.get_src_anno_tar(i)
                    # save to local var, do not hold onto refs with self.source_image_img_target[i].append()
                    # user can use load_src_anno_tar() to do this!s
                    self.save_src_anno_tar(i, anno_img)
            else:
                print('')
                print('  source annotations to target : no annotation images')
                print('')
        
        else:
            print('')
            print('  saving source annotations to target : not requested')
            print('')
        
        
        if self.brp['source-to-target-save-images'] == True:
            
            
            if self.source_image_path_target != []: # not a blank list
                print('')
                print('  source images to target :')
                print('')
                for i,im_ds in enumerate(self.source_image_path_target):
                    # source_image_path + _ds + _target all are SAME LENGTH!
                    print('  source image ' + str(i))
                    img_tar = self.get_src_image_tar(i)
                    # save to local var, do not hold onto refs with self.source_image_img_target[i].append()
                    # user can use load_src_images_tar() to do this!s
                    self.save_src_image_tar(i, img_tar)
            else:
                print('')
                print('  source images to target : no further images')
                print('')
        
        else:
            print('')
            print('  saving source images to target : not requested')
            print('')
            
        
        # discard from memory all images/martices not needed - just point vars to blank list!
        garbage = gc.collect() # run garbage collection to ensure memory is freed
        
        
    
    
    
    
    def transform_target_to_source(self):
        #if (self.downsampling_img == 'source'): 
        # NOT NEEDED as no refs to ds or raw image data/paths!
        
        if self.brp['target-to-source-save-template'] == True:
            
            if self.target_template_path_source.exists() == False:
                self.target_template_img_source = self.get_tar_template_src()
                self.save_tar_template_src()
            else:
                print('')
                print('  saving target template to source : image exists')
                print('')
        else:
            print('')
            print('  saving target template to source : not requested')
            print('')
        
        
        if self.brp['target-to-source-save-annotations'] == True:
            
            
            if self.target_anno_path_source != []: # not a blank list
                print('')
                print('  target annotations to source : ')
                print('')
                for i,im_ds in enumerate(self.target_anno_path_source):
                    # source_anno_path + _ds + _target all are SAME LENGTH!
                    print('  annotation image ' + str(i))
                    anno_img = self.get_tar_anno_src(i)
                    # save to local var, do not hold onto refs with self.source_image_img_target[i].append()
                    # user can use load_src_anno_tar() to do this!s
                    self.save_tar_anno_src(i, anno_img)
            else:
                print('')
                print('  target annotations to source : no annotation images')
                print('')
        
        else:
            print('')
            print('  saving target annotations to source : not requested')
            print('')
        
        
        if self.brp['target-to-source-save-images'] == True:
            
            
            if self.target_image_paths_source != []: # not a blank list
                print('')
                print('  target images to source :')
                print('')
                for i,im_ds in enumerate(self.target_image_paths_source):
                    # source_image_path + _ds + _target all are SAME LENGTH!
                    print('  target image ' + str(i))
                    img_tar = self.get_tar_image_src(i)
                    # save to local var, do not hold onto refs with self.source_image_img_target[i].append()
                    # user can use load_src_images_tar() to do this!s
                    self.save_tar_image_src(i, img_tar)
            else:
                print('')
                print('  target images to source : no further images')
                print('')
        
        else:
            print('')
            print('  saving target images to source : not requested')
            print('')
            
        
        # discard from memory all images/martices not needed - just point vars to blank list!
        garbage = gc.collect() # run garbage collection to ensure memory is freed
        
        
    
    
    
    def get_src_template_tar(self):
        '''
        Get the source template image in target image space

        Returns
        -------
        sitk Image
            Image of the source template in target image space.

        '''
        
        
        if (self.downsampling_img == 'source'):
            # source image is downsampled to target img transformation
            # so get ds source and transform this to target img
            
            if self.source_template_path_target.exists() == False: 
                # only transform if output does not exist
                if self.source_template_img_target == None: 
                    # and if the output image is not already loaded!
                    
                    self.source_template_img_ds = self.get_template_ds()
                    
                    
                    if self.src_tar_pm is None:
                        print('  source to target paramater maps not loaded - loading files..')
                        self.src_tar_pm = self.load_pm_files( self.src_tar_pm_paths )
                    
                    print('  transforming source template downsampled image to target..')
                    print('    image : ' + 
                            self.get_relative_path(self.source_template_path_ds) )
                    
                    for i, pm in enumerate(self.src_tar_pm_paths):
                        print('    source-to-target paramter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    
                    print('========================================================================')
                    print('')
                    print('')
                    return self.transform_image(self.source_template_img_ds, 
                                                  self.src_tar_pm )
                
                else:
                    print('  downsampled source template to target space exists - returning image..')
                    return self.source_template_img_target
            
            else:
                print('  downsampled source template to target space exists - loading image..')
                self.source_template_img_target = self.load_image(self.source_template_path_target)
                return self.source_template_img_target
            
            
        elif (self.downsampling_img == 'target'):
            # source images to ds target img THEN ds to target image space
            
            if self.source_template_path_target.exists() == False: 
                # only transform if output does not exist
                if self.source_template_img_target == None: 
                    # and if the output image is not already loaded!
                    
                    # get source image
                    if self.source_template_img is None: # AND path exists!
                        print('  source template image not loaded - loading image..')
                        self.source_template_img = self.load_image(self.source_template_path)
                    
                    
                    if self.src_tar_pm is None: # this gives source to ds target
                        print('  source to target paramater maps not loaded - loading files..')
                        self.src_tar_pm = self.load_pm_files( self.src_tar_pm_paths )
                    
                    print('  transforming source template image to downsampled target..')
                    print('    image : ' + 
                            self.get_relative_path(self.source_template_path) )
                    
                    for i, pm in enumerate(self.src_tar_pm_paths):
                        print('    source-to-downsampled-target paramter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    
                    print('========================================================================')
                    print('')
                    print('')
                    img = self.transform_image(self.source_template_img, 
                                                  self.src_tar_pm )
                    
                    # and move source to ds target from ds target to raw target
                    return self.move_image_ds_img(img)
                    
                else:
                    print('  source template to target space exists - returning image..')
                    return self.source_template_img_target
            
            else:
                print('  source template to target space exists - loading image..')
                self.source_template_img_target = self.load_image(self.source_template_path_target)
                return self.source_template_img_target
        
        
        elif (self.downsampling_img == 'none'):
            # source image to target image space (no downsampling in this instance!)
            
            if self.source_template_path_target.exists() == False: 
                # only transform if output does not exist
                if self.source_template_img_target == None: 
                    # and if the output image is not already loaded!
                    
                    if self.source_template_img is None: # AND path exists!
                        print('  source template image not loaded - loading image..')
                        self.source_template_img = self.load_image(self.source_template_path)
                    
                    
                    if self.src_tar_pm is None:
                        print('  source to target paramater maps not loaded - loading files..')
                        self.src_tar_pm = self.load_pm_files( self.src_tar_pm_paths )
                    
                    print('  transforming source template image to target..')
                    print('    image : ' + 
                            self.get_relative_path(self.source_template_path) )
                    
                    for i, pm in enumerate(self.src_tar_pm_paths):
                        print('    source-to-target paramter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    
                    print('========================================================================')
                    print('')
                    print('')
                    return self.transform_image(self.source_template_img, 
                                                  self.src_tar_pm )
                
                else:
                    print('  source template to target space exists - returning image..')
                    return self.source_template_img_target
            
            else:
                print('  source template to target space exists - loading image..')
                self.source_template_img_target = self.load_image(self.source_template_path_target)
                return self.source_template_img_target
        
    
    
    
    def save_src_template_tar(self):
        
        if self.source_template_path_target.exists() == False:
            if self.source_template_img_target != None:
                print('  saving source template to target : ' + 
                      self.get_relative_path(self.source_template_path_target))
                self.save_image(self.source_template_img_target, self.source_template_path_target)
            else:
                print('  source template in target space does not exist - run get_src_template_tar()')
                
        else:
            print('  source template in target image space exists')
    
    
    
    
    def get_src_anno_tar(self, index):
        
        if (self.downsampling_img == 'source'):
            # source image is downsampled source to target img transformation
            # so get ds source and transform this to target img
            im_path = self.source_anno_path_ds[index]
            
            if self.source_anno_path_target[index].exists() == False: 
                # only transform if output does not exist
                if self.source_anno_img_target[index] == None: 
                    # and if the output anno is not already loaded!
                    
                    if im_path.exists() == False:
                        print('  transforming downsampled source annotation from source anno..')
                        img_ds = self.load_transform_anno_img_ds(self.source_anno_path[index])
                    
                    else:
                        print('  loading downsampled source annotation..')
                        img_ds = self.load_image(im_path)
                    
                    
                    if self.src_tar_pm_anno is None:
                        print('  source to target annotation paramater maps not loaded - loading files..')
                        self.src_tar_pm = self.load_pm_files( self.src_tar_pm_paths )
                        if self.src_tar_pm == None:
                            print("ERROR : src_tar_ds_pm files do not exist - run register() first")
                        self.src_tar_pm_anno = self.edit_pms_nearest_neighbour(self.src_tar_pm)
                    
                    
                    print('  transforming source downsampled annotation to target..')
                    print('    image : ' + self.get_relative_path(im_path) )
                    
                    for i, pm in enumerate(self.src_tar_pm_paths):
                        print('    source-to-target paramter map file '+
                                str(i) + ' : ' + self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    img_ds_tar = self.transform_image(img_ds, self.src_tar_pm_anno)
                    # not saving to self.source_anno_img_target[index] to minimise memory occupation
                    return img_ds_tar
                
                else:
                    print('  source annotation to target space exists - returning image..')
                    return self.source_anno_img_target[index]
                
            else:
                print('  source annotation to target space exists - loading image..')
                return self.load_image(self.source_anno_path_target[index])
            
            
        elif (self.downsampling_img == 'target'):
            # source anno to ds target THEN ds to target image space
            
            im_path = self.source_anno_path[index]
            
            if self.source_anno_path_target[index].exists() == False: 
                # only transform if output does not exist
                if self.source_anno_img_target[index] == None: 
                    # and if the output anno is not already loaded!
                    
                    print('  loading source annotation..')
                    img_ds = self.load_image(im_path)
                    
                    
                    if self.src_tar_pm_anno is None:
                        print('  source to target annotation paramater maps not loaded - loading files..')
                        self.src_tar_pm = self.load_pm_files( self.src_tar_pm_paths )
                        if self.src_tar_pm == None:
                            print("ERROR : src_tar_ds_pm files do not exist - run register() first")
                        self.src_tar_pm_anno = self.edit_pms_nearest_neighbour(self.src_tar_pm)
                    
                    
                    print('  transforming source annotation to downsampled target..')
                    print('    image : ' + self.get_relative_path(im_path) )
                    
                    for i, pm in enumerate(self.src_tar_pm_paths):
                        print('    source-to-target parameter map file '+
                                str(i) + ' : ' + self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    anno_ds_tar = self.transform_image(img_ds, self.src_tar_pm_anno)
                    # not saving to self.source_anno_img_target[index] to minimise memory occupation
                    return self.move_anno_ds_img(anno_ds_tar)
                
                else:
                    print('  source annotation to target space exists - returning image..')
                    return self.source_anno_img_target[index]
                
            else:
                print('  source annotation to target space exists - loading image..')
                return self.load_image(self.source_anno_path_target[index])
            
            
        elif (self.downsampling_img == 'none'):
            # source image to target image space (no downsampling in this instance!)
            
            im_path = self.source_anno_path[index]
            
            if self.source_anno_path_target[index].exists() == False: 
                # only transform if output does not exist
                if self.source_anno_img_target[index] == None: 
                    # and if the output anno is not already loaded!
                    
                    print('  loading source annotation..')
                    img_ds = self.load_image(im_path)
                    
                    
                    if self.src_tar_pm_anno is None:
                        print('  source to target annotation paramater maps not loaded - loading files..')
                        self.src_tar_pm = self.load_pm_files( self.src_tar_pm_paths )
                        if self.src_tar_pm == None:
                            print("ERROR : src_tar_ds_pm files do not exist - run register() first")
                        self.src_tar_pm_anno = self.edit_pms_nearest_neighbour(self.src_tar_pm)
                    
                    
                    print('  transforming source annotation to target..')
                    print('    image : ' + self.get_relative_path(im_path) )
                    
                    for i, pm in enumerate(self.src_tar_pm_paths):
                        print('    source-to-target parameter map file '+
                                str(i) + ' : ' + self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    return self.transform_image(img_ds, self.src_tar_pm_anno)
                    # not saving to self.source_anno_img_target[index] to minimise memory occupation
                    
                else:
                    print('  source annotation to target space exists - returning image..')
                    return self.source_anno_img_target[index]
                
            else:
                print('  source annotation to target space exists - loading image..')
                return self.load_image(self.source_anno_path_target[index])
            
        
    
    
    
    
    def save_src_anno_tar(self, index, image):
        
        #if (self.downsampling_img == 'source'):
        # ds source images to target img 
        if self.source_anno_path_target[index].exists() == False: # only save if output does not exist
            print('  saving source annotation to target : ' +
                  self.get_relative_path(self.source_anno_path_target[index] ) )
            self.save_image(image, self.source_anno_path_target[index])
        
        
    
    
    
    def load_src_anno_tar(self):
        '''
        Load all source annotation images to target into instance variable self.source_image_img_target
        '''
        if (self.downsampling_img == 'source'):
            # ds source images to target img 
            for i,im_ds in enumerate(self.source_anno_path_ds):
                self.source_anno_img_target[i] = self.get_src_anno_tar(i)
        
    
    
    
    def get_src_image_tar(self, index):
        
        
        if (self.downsampling_img == 'source'):
            # ds source images to target img 
            im_path = self.source_image_path_ds[index]
            
            if self.source_image_path_target[index].exists() == False: 
                # only transform if output does not exist
                if self.source_image_img_target[index] == None: 
                    # and if the output image is not already loaded!
                    
                    if im_path.exists() == False:
                        print('  transforming downsampled source image from source image..')
                        img_ds = self.load_transform_image_img_ds(self.source_image_path[index])
                    
                    else:
                        print('  loading downsampled source image..')
                        img_ds = self.load_image(im_path)
                    
                    
                    if self.src_tar_pm is None:
                        print('  source to target paramater maps not loaded - loading files..')
                        self.src_tar_pm = self.load_pm_files( self.src_tar_pm_paths )
                    
                    
                    print('  transforming source downsampled image to target..')
                    print('    image : ' + 
                            self.get_relative_path(im_path) )
                    
                    for i, pm in enumerate(self.src_tar_pm_paths):
                        print('    source-to-target paramter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    img_tar = self.transform_image(img_ds, self.src_tar_pm)
                    # not saving to self.source_image_img_target[index] to minimise memory occupation
                    return img_tar
                
                else:
                    print('  downsampled source image to target space exists - returning image..')
                    return self.source_image_img_target[index]
                
            else:
                print('  downsampled source image to target space exists - loading image..')
                img_tar = self.load_image(self.source_image_path_target[index])
                return img_tar
            
            
        if (self.downsampling_img == 'target'):
            # source anno to ds target THEN ds to target image space
            im_path = self.source_image_path[index]
            
            if self.source_image_path_target[index].exists() == False: 
                # only transform if output does not exist
                if self.source_image_img_target[index] == None: 
                    # and if the output image is not already loaded!
                    
                    print('  loading source image..')
                    img_ds = self.load_image(im_path)
                    
                    
                    if self.src_tar_pm is None:
                        print('  source to target paramater maps not loaded - loading files..')
                        self.src_tar_pm = self.load_pm_files( self.src_tar_pm_paths )
                    
                    
                    print('  transforming source downsampled image to target..')
                    print('    image : ' + 
                            self.get_relative_path(im_path) )
                    
                    for i, pm in enumerate(self.src_tar_pm_paths):
                        print('    source-to-target paramter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    img_tar = self.transform_image(img_ds, self.src_tar_pm)
                    # not saving to self.source_image_img_target[index] to minimise memory occupation
                    return self.move_image_ds_img(img_tar)
                
                else:
                    print('  downsampled source image to target space exists - returning image..')
                    return self.source_image_img_target[index]
                
            else:
                print('  downsampled source image to target space exists - loading image..')
                img_tar = self.load_image(self.source_image_path_target[index])
                return img_tar
            
            
        if (self.downsampling_img == 'none'):
            # source anno to ds target THEN ds to target image space
            im_path = self.source_image_path[index]
            
            if self.source_image_path_target[index].exists() == False: 
                # only transform if output does not exist
                if self.source_image_img_target[index] == None: 
                    # and if the output image is not already loaded!
                    
                    print('  loading source image..')
                    img_ds = self.load_image(im_path)
                    
                    
                    if self.src_tar_pm is None:
                        print('  source to target paramater maps not loaded - loading files..')
                        self.src_tar_pm = self.load_pm_files( self.src_tar_pm_paths )
                    
                    
                    print('  transforming source downsampled image to target..')
                    print('    image : ' + 
                            self.get_relative_path(im_path) )
                    
                    for i, pm in enumerate(self.src_tar_pm_paths):
                        print('    source-to-target paramter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    return self.transform_image(img_ds, self.src_tar_pm)
                    # not saving to self.source_image_img_target[index] to minimise memory occupation
                    
                else:
                    print('  downsampled source image to target space exists - returning image..')
                    return self.source_image_img_target[index]
                
            else:
                print('  downsampled source image to target space exists - loading image..')
                img_tar = self.load_image(self.source_image_path_target[index])
                return img_tar
        
        
    
    
    
    def save_src_image_tar(self, index, image):
        
        #if (self.downsampling_img == 'source'):
        # ds source images to target img 
        if self.source_image_path_target[index].exists() == False: # only save if output does not exist
            print('  saving source image to target : ' +
                  self.get_relative_path(self.source_image_path_target[index] ) )
            self.save_image(image, self.source_image_path_target[index])
        
        
    
    
    
    def load_src_images_tar(self):
        '''
        Load all source images to target into instance variable self.source_image_img_target
        '''
        if (self.downsampling_img == 'source'):
            # ds source images to target img 
            for i,im_ds in enumerate(self.source_image_path_ds):
                self.source_image_img_target[i] = self.get_src_image_tar(i)
        
    
    
    
    
    
    
    def get_tar_template_src(self):
        '''
        Get the target template image in source image space

        Returns
        -------
        sitk Image
            Image of the target template in source image space.

        '''
        
        
        if (self.downsampling_img == 'target'):
            # target image is downsampled to source img transformation
            # so get ds target and transform this to source img
            
            if self.target_template_path_source.exists() == False: 
                # only transform if output does not exist
                if self.target_template_img_source == None: 
                    # and if the output image is not already loaded!
                    
                    self.target_template_img_ds = self.get_template_ds()
                    
                    
                    if self.tar_src_pm is None:
                        print('  target to source paramater maps not loaded - loading files..')
                        self.tar_src_pm = self.load_pm_files( self.tar_src_pm_paths )
                    
                    print('  transforming target template downsampled image to source..')
                    print('    image : ' + 
                            self.get_relative_path(self.target_template_path_ds) )
                    
                    for i, pm in enumerate(self.tar_src_pm_paths):
                        print('    target-to-source paramter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    
                    print('========================================================================')
                    print('')
                    print('')
                    return self.transform_image(self.target_template_img_ds, 
                                                  self.tar_src_pm )
                
                else:
                    print('  downsampled target template to source space exists - returning image..')
                    return self.target_template_img_source
            
            else:
                print('  downsampled target template to source space exists - loading image..')
                self.target_template_img_source = self.load_image(self.target_template_path_source)
                return self.target_template_img_source
            
            
        elif (self.downsampling_img == 'source'):
            # target images to ds source img THEN ds to source image space
            
            if self.target_template_path_source.exists() == False: 
                # only transform if output does not exist
                if self.target_template_img_source == None: 
                    # and if the output image is not already loaded!
                    
                    # get source image
                    if self.target_template_img is None: # AND path exists!
                        print('  target template image not loaded - loading image..')
                        self.target_template_img = self.load_image(self.target_template_path)
                    
                    
                    if self.tar_src_pm is None: # this gives source to ds target
                        print('  target to source paramater maps not loaded - loading files..')
                        self.tar_src_pm = self.load_pm_files( self.tar_src_pm_paths )
                    
                    print('  transforming target template image to downsampled source..')
                    print('    image : ' + 
                            self.get_relative_path(self.target_template_path) )
                    
                    for i, pm in enumerate(self.tar_src_pm_paths):
                        print('    target-to-downsampled source paramter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    
                    print('========================================================================')
                    print('')
                    print('')
                    img = self.transform_image(self.target_template_img, 
                                                  self.tar_src_pm )
                    
                    # and move source to ds target from ds target to raw target
                    return self.move_image_ds_img(img)
                    
                else:
                    print('  target template to source space exists - returning image..')
                    return self.target_template_img_source
            
            else:
                print('  target template to source space exists - loading image..')
                self.target_template_img_source = self.load_image(self.target_template_path_source)
                return self.target_template_img_source
        
        
        elif (self.downsampling_img == 'none'):
            # target image to source image space (no downsampling in this instance!)
            
            if self.target_template_path_source.exists() == False: 
                # only transform if output does not exist
                if self.target_template_img_source == None: 
                    # and if the output image is not already loaded!
                    
                    if self.target_template_img is None: # AND path exists!
                        print('  target template image not loaded - loading image..')
                        self.target_template_img = self.load_image(self.target_template_path)
                    
                    
                    if self.tar_src_pm is None:
                        print('  source to target paramater maps not loaded - loading files..')
                        self.tar_src_pm = self.load_pm_files( self.tar_src_pm_paths )
                    
                    print('  transforming target template image to source..')
                    print('    image : ' + 
                            self.get_relative_path(self.target_template_path) )
                    
                    for i, pm in enumerate(self.tar_src_pm_paths):
                        print('    target-to-source paramter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    
                    print('========================================================================')
                    print('')
                    print('')
                    return self.transform_image(self.target_template_img, 
                                                  self.src_tar_pm )
                
                else:
                    print('  target template to source space exists - returning image..')
                    return self.target_template_img_source
            
            else:
                print('  target template to source space exists - loading image..')
                self.target_template_img_source = self.load_image(self.target_template_path_source)
                return self.target_template_img_source
        
    
    
    
    def save_tar_template_src(self):
        
        if self.target_template_path_source.exists() == False:
            if self.source_template_img_target != None:
                print('  saving target template to source : ' + 
                      self.get_relative_path(self.target_template_path_source))
                self.save_image(self.target_template_img_source, self.target_template_path_source)
            else:
                print('  target template in source space does not exist - run get_tar_template_src()')
                
        else:
            print('  target template in source image space exists')
    
    
    
    
    def get_tar_anno_src(self, index):
        
        if (self.downsampling_img == 'target'):
            # target image is downsampled target to source img transformation
            # so get ds target and transform this to source img
            im_path = self.target_anno_path_ds[index]
            
            if self.target_anno_path_source[index].exists() == False: 
                # only transform if output does not exist
                if self.target_anno_img_source[index] == None: 
                    # and if the output anno is not already loaded!
                    
                    if im_path.exists() == False:
                        print('  transforming downsampled target annotation from target anno..')
                        img_ds = self.load_transform_anno_img_ds(self.target_anno_path[index])
                    
                    else:
                        print('  loading downsampled target annotation..')
                        img_ds = self.load_image(im_path)
                    
                    
                    if self.tar_src_pm_anno is None:
                        print('  target to source annotation paramater maps not loaded - loading files..')
                        self.tar_src_pm = self.load_pm_files( self.tar_src_pm_paths )
                        if self.tar_src_pm == None:
                            print("ERROR : tar_src_ds_pm files do not exist - run register() first")
                        self.tar_src_pm_anno = self.edit_pms_nearest_neighbour(self.tar_src_pm)
                    
                    
                    print('  transforming target downsampled annotation to source..')
                    print('    image : ' + self.get_relative_path(im_path) )
                    
                    for i, pm in enumerate(self.tar_src_pm_paths):
                        print('    target-to-source paramter map file '+
                                str(i) + ' : ' + self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    img_ds_tar = self.transform_image(img_ds, self.tar_src_pm_anno)
                    # not saving to self.target_anno_img_source[index] to minimise memory occupation
                    return img_ds_tar
                
                else:
                    print('  target annotation to source space exists - returning image..')
                    return self.target_anno_img_source[index]
                
            else:
                print('  target annotation to source space exists - loading image..')
                # not saving to self.target_anno_img_source[index] to minimise memory occupation
                return self.load_image(self.target_anno_path_source[index])
            
            
        elif (self.downsampling_img == 'source'):
            # target anno to ds source THEN ds to source image space
            
            im_path = self.target_anno_path[index]
            
            if self.target_anno_path_source[index].exists() == False: 
                # only transform if output does not exist
                if self.target_anno_img_source[index] == None: 
                    # and if the output anno is not already loaded!
                    
                    print('  loading target annotation..')
                    img_ds = self.load_image(im_path)
                    
                    
                    if self.tar_src_pm_anno is None:
                        print('  target to source annotation paramater maps not loaded - loading files..')
                        self.tar_src_pm = self.load_pm_files( self.tar_src_pm_paths )
                        if self.tar_src_pm == None:
                            print("ERROR : tar_src_ds_pm files do not exist - run register() first")
                        self.tar_src_pm_anno = self.edit_pms_nearest_neighbour(self.tar_src_pm)
                    
                    
                    print('  transforming target annotation to downsampled source..')
                    print('    image : ' + self.get_relative_path(im_path) )
                    
                    for i, pm in enumerate(self.tar_src_pm_paths):
                        print('    target-to-source parameter map file '+
                                str(i) + ' : ' + self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    anno_ds_src = self.transform_image(img_ds, self.tar_src_pm_anno)
                    # not saving to self.source_anno_img_target[index] to minimise memory occupation
                    return self.move_anno_ds_img(anno_ds_src)
                
                else:
                    print('  target annotation to source space exists - returning image..')
                    return self.target_anno_img_source[index]
                
            else:
                print('  target annotation to source space exists - loading image..')
                return self.load_image(self.target_anno_path_source[index])
            
            
        elif (self.downsampling_img == 'none'):
            # target image to source image space (no downsampling in this instance!)
            
            im_path = self.target_anno_path[index]
            
            if self.target_anno_path_source[index].exists() == False: 
                # only transform if output does not exist
                if self.target_anno_img_source[index] == None: 
                    # and if the output anno is not already loaded!
                    
                    print('  loading downsampled target annotation..')
                    img_ds = self.load_image(im_path)
                    
                    
                    if self.tar_src_pm_anno is None:
                        print('  target to source annotation paramater maps not loaded - loading files..')
                        self.tar_src_pm = self.load_pm_files( self.tar_src_pm_paths )
                        if self.tar_src_pm == None:
                            print("ERROR : tar_src_ds_pm files do not exist - run register() first")
                        self.tar_src_pm_anno = self.edit_pms_nearest_neighbour(self.tar_src_pm)
                    
                    
                    print('  transforming target annotation to source..')
                    print('    image : ' + self.get_relative_path(im_path) )
                    
                    for i, pm in enumerate(self.tar_src_pm_paths):
                        print('    target-to-source parameter map file '+
                                str(i) + ' : ' + self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    return self.transform_image(img_ds, self.tar_src_pm_anno)
                    # not saving to self.target_anno_img_source[index] to minimise memory occupation
                    
                else:
                    print('  target annotation to source space exists - returning image..')
                    return self.target_anno_img_source[index]
                
            else:
                print('  target annotation to source space exists - loading image..')
                # not saving to self.target_anno_img_source[index] to minimise memory occupation
                return self.load_image(self.target_anno_path_source[index])
            
        
    
    
    
    
    def save_tar_anno_src(self, index, image):
        
        #if (self.downsampling_img == 'source'):
        # ds source images to target img 
        if self.target_anno_path_source[index].exists() == False: # only save if output does not exist
            print('  saving target annotation to source : ' +
                  self.get_relative_path(self.target_anno_path_source[index] ) )
            self.save_image(image, self.target_anno_path_source[index])
        
        
    
    
    
    def load_tar_anno_src(self):
        '''
        Load all target annotation images to source into instance variable self.target_image_img_source
        '''
        if (self.downsampling_img == 'target'):
            # ds source images to target img 
            for i,im_ds in enumerate(self.target_anno_path_ds):
                self.target_anno_img_source[i] = self.get_tar_anno_src(i)
        
    
    
    
    def get_tar_image_src(self, index):
        
        
        if (self.downsampling_img == 'target'):
            # ds target images to source img 
            im_path = self.target_image_paths_ds[index]
            
            if self.target_image_paths_source[index].exists() == False: 
                # only transform if output does not exist
                if self.target_image_img_source[index] == None: 
                    # and if the output image is not already loaded!
                    
                    if im_path.exists() == False:
                        print('  transforming downsampled target image from target image..')
                        img_ds = self.load_transform_image_img_ds(self.target_image_path[index])
                    
                    else:
                        print('  loading downsampled target image..')
                        img_ds = self.load_image(im_path)
                    
                    
                    if self.tar_src_pm is None:
                        print('  target to source paramater maps not loaded - loading files..')
                        self.tar_src_pm = self.load_pm_files( self.tar_src_pm_paths )
                    
                    
                    print('  transforming target downsampled image to source..')
                    print('    image : ' + 
                            self.get_relative_path(im_path) )
                    
                    for i, pm in enumerate(self.tar_src_pm_paths):
                        print('    target-to-source paramter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    img_src = self.transform_image(img_ds, self.tar_src_pm)
                    # not saving to self.target_image_img_source[index] to minimise memory occupation
                    return img_src
                
                else:
                    print('  downsampled target image to source space exists - returning image..')
                    return self.target_image_img_source[index]
                
            else:
                print('  downsampled target image to source space exists - loading image..')
                img_src = self.load_image(self.target_image_paths_source[index])
                # not saving to self.target_image_img_source[index] to minimise memory occupation
                return img_src
            
            
        if (self.downsampling_img == 'source'):
            # target anno to ds source THEN ds to source image space
            im_path = self.target_image_path[index]
            
            if self.target_image_paths_source[index].exists() == False: 
                # only transform if output does not exist
                if self.target_image_img_source[index] == None: 
                    # and if the output image is not already loaded!
                    
                    print('  loading downsampled target image..')
                    img_ds = self.load_image(im_path)
                    
                    
                    if self.tar_src_pm is None:
                        print('  target to source paramater maps not loaded - loading files..')
                        self.tar_src_pm = self.load_pm_files( self.tar_src_pm_paths )
                    
                    
                    print('  transforming target downsampled image to source..')
                    print('    image : ' + 
                            self.get_relative_path(im_path) )
                    
                    for i, pm in enumerate(self.tar_src_pm_paths):
                        print('    target-to-source paramter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    img_src = self.transform_image(img_ds, self.tar_src_pm)
                    # not saving to self.target_image_img_source[index] to minimise memory occupation
                    return self.move_image_ds_img(img_src)
                
                else:
                    print('  downsampled target image to source space exists - returning image..')
                    return self.target_image_img_source[index]
                
            else:
                print('  downsampled target image to source space exists - loading image..')
                img_src = self.load_image(self.target_image_paths_source[index])
                # not saving to self.target_image_img_source[index] to minimise memory occupation
                return img_src
            
            
        if (self.downsampling_img == 'none'):
            # target anno to source image space (no downsampling)
            im_path = self.target_image_path[index]
            
            if self.target_image_paths_source[index].exists() == False: 
                # only transform if output does not exist
                if self.target_image_img_source[index] == None: 
                    # and if the output image is not already loaded!
                    
                    print('  loading downsampled target image..')
                    img_ds = self.load_image(im_path)
                    
                    
                    if self.tar_src_pm is None:
                        print('  target to source paramater maps not loaded - loading files..')
                        self.tar_src_pm = self.load_pm_files( self.tar_src_pm_paths )
                    
                    
                    print('  transforming target downsampled image to source..')
                    print('    image : ' + 
                            self.get_relative_path(im_path) )
                    
                    for i, pm in enumerate(self.tar_src_pm_paths):
                        print('    target-to-source parameter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    return self.transform_image(img_ds, self.tar_src_pm)
                    # not saving to self.target_image_img_source[index] to minimise memory occupation
                    
                else:
                    print('  downsampled target image to source space exists - returning image..')
                    return self.target_image_img_source[index]
                
            else:
                print('  downsampled target image to source space exists - loading image..')
                img_src = self.load_image(self.target_image_paths_source[index])
                # not saving to self.target_image_img_source[index] to minimise memory occupation
                return img_src
        
        
    
    
    
    def save_tar_image_src(self, index, image):
        
        #if (self.downsampling_img == 'source'):
        # ds target images to source img 
        if self.target_image_paths_source[index].exists() == False: # only save if output does not exist
            print('  saving target image to source : ' +
                  self.get_relative_path(self.target_image_paths_source[index] ) )
            self.save_image(image, self.target_image_paths_source[index])
        
        
    
    
    
    def load_tar_images_src(self):
        '''
        Load all target images to source into instance variable self.target_image_img_source
        '''
        if (self.downsampling_img == 'target'):
            # ds target images to source img 
            for i,im_ds in enumerate(self.target_image_paths_ds):
                self.target_image_img_source[i] = self.get_tar_image_src(i)
        
    
    
    
    
    def edit_pms_nearest_neighbour(self, pms):
        
        if pms == None:
            return None # this is so initial calls in resolve_param_paths()
                        # is set to None if pm files dont exist
        else:
            # FIRST alter the pm files FinalBSplineInterpolationOrder to 0
            # 0 - nearest neighbour interpolation for annotation images
            for pm in pms:
                pm['FinalBSplineInterpolationOrder'] = tuple( [ str(0) ] )
            
            return pms
    
    
    
    
    def transform_lowres_to_downsampled(self):
        
        
        if (self.downsampling_img == 'source'):
            # TARGET is low res. : move target images from target to ds source
            print('')
            print('')
            print('=====================')
            print('TARGET TO DOWNSAMPLED')
            print('=====================')
            print('')
            
            # transform and save target template to ds source image space as requested
            self.transform_save_low_ds_template()
            
            # also transform and save target annotation images - if requested in the params file
            self.transform_save_low_ds_anno()
            
            # also transform and save other target images - if requested in the params file
            self.transform_save_low_ds_images()
            
            
        elif (self.downsampling_img == 'target'):
            # SOURCE is low res. : move source images from source to ds target
            
            print('')
            print('')
            print('=====================')
            print('SOURCE TO DOWNSAMPLED')
            print('=====================')
            print('')
            
            # transform and save source template to ds image as requested
            self.transform_save_low_ds_template()
            
            # also transform and save source annotation images - if requested in the params file
            self.transform_save_low_ds_anno()
            
            # also transform and save other source images - if requested in the params file
            self.transform_save_low_ds_images()
            
        else:
            # no downsampling!
            print('source and target template same resolution - no downsampling performed.')
        
    
    
    
    def transform_save_low_ds_template(self):
        
        if self.downsampling_img == 'source':
            # transform and save target template to ds source image space as requested
            if self.brp['target-to-source-downsampling-save-template'] == True:
                
                if self.target_template_path_ds.exists() == False: 
                    # only transform if output does not exist
                    if self.target_template_img == None:
                        print('  loading target template image : ' + 
                          self.get_relative_path(self.target_template_path) )
                        self.target_template_img = self.load_image(self.target_template_path)
                    
                    
                    if self.tar_src_pm is None:
                        print('  target to source paramater maps not loaded - loading files..')
                        self.tar_src_pm = self.load_pm_files( self.tar_src_pm_paths )
                    
                    
                    print('  transforming target template to downsampled source..')
                    print('    image : ' + 
                            self.get_relative_path(self.target_template_path) )
                    
                    for i, pm in enumerate(self.tar_src_pm_paths):
                        print('    target-to-source paramter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    img_ds_src = self.transform_image(self.target_template_img, self.tar_src_pm)
                    
                    self.save_image(img_ds_src, self.target_template_path_ds)
                    
                    self.target_template_img = None
                    garbage = gc.collect() # run garbage collection to ensure memory is freed
                    
                    
                else:
                    print('')
                    print('  target template to downsampled source : exists')
                    print('')
            else:
                print('')
                print('  target template to downsampled source : not requested')
                print('')
            
            
        elif self.downsampling_img == 'target':
            # transform and save source template to ds target image space as requested
            if self.brp['source-to-target-downsampling-save-template'] == True:
                
                if self.source_template_path_ds.exists() == False: 
                    # only transform if output does not exist
                    if self.source_template_img == None:
                        print('  loading source template image : ' + 
                          self.get_relative_path(self.source_template_path) )
                        self.source_template_img = self.load_image(self.source_template_path)
                    
                    if self.src_tar_pm is None:
                        print('  source to target paramater maps not loaded - loading files..')
                        self.src_tar_pm = self.load_pm_files( self.src_tar_pm_paths )
                    
                    
                    print('  transforming source template to downsampled target..')
                    print('    image : ' + 
                            self.get_relative_path(self.source_template_path) )
                    
                    for i, pm in enumerate(self.src_tar_pm_paths):
                        print('    source-to-target paramter map file '+
                                str(i) + ' : ' + 
                                self.get_relative_path(pm) )
                    print('========================================================================')
                    print('')
                    print('')
                    
                    img_ds_tar = self.transform_image(self.source_template_img, self.src_tar_pm)
                    
                    self.save_image(img_ds_tar, self.source_template_path_ds)
                    
                    self.source_template_img = None
                    garbage = gc.collect() # run garbage collection to ensure memory is freed
                    
                    
                else:
                    print('')
                    print('  source template to downsampled target : exists')
                    print('')
            else:
                print('')
                print('  transforming and saving source template to downsampled target image space : not requested')
                print('')
        
    
    
    
    
    def transform_save_low_ds_anno(self):
        
        if self.downsampling_img == 'source':
            # transform and save target template to ds source image space as requested
            if self.brp['target-to-source-downsampling-save-annotations'] == True:
                
                if self.target_anno_path != []:
                    print('')
                    print('  transforming and saving target annotations to ds..')
                    
                    for i, s in enumerate(self.target_anno_path):
                        
                        if self.target_anno_path_ds[i].exists() == False: 
                            # only transform if output does not exist
                            if self.target_anno_img[i] == None:
                                print('  loading target anno image : ' + 
                                  self.get_relative_path(self.target_anno_path[i]) )
                                tar_anno_img = self.load_image(self.target_anno_path[i])
                            else:
                                tar_anno_img = self.target_anno_img[i]
                            
                            
                            if self.tar_src_pm is None:
                                print('  target to source paramater maps not loaded - loading files..')
                                self.tar_src_pm = self.load_pm_files( self.tar_src_pm_paths )
                                if self.tar_src_pm == None:
                                    print("ERROR : tar_src_ds_pm files do not exist - run register() first")
                                self.tar_src_pm_anno = self.edit_pms_nearest_neighbour(self.tar_src_pm)
                            
                            print('  transforming target annotation to downsampled source..')
                            print('    image : ' + 
                                    self.get_relative_path(self.target_anno_path[i]) )
                            
                            for j, pm in enumerate(self.tar_src_pm_paths):
                                print('    target-to-source paramter map file '+
                                        str(j) + ' : ' + 
                                        self.get_relative_path(pm) )
                            print('========================================================================')
                            print('')
                            print('')
                            
                            img_ds_src = self.transform_image(tar_anno_img, self.tar_src_pm_anno)
                            
                            self.save_image(img_ds_src, self.target_anno_path_ds[i])
                            
                        else:
                            print('')
                            print('  target annotation to downsampled source : exists')
                            print('')
                    
                else:
                    print('')
                    print('  transforming and saving target annotations to downsampled source image space : no annotations to process')
                    print('')
                    
                
            else:
                print('')
                print('  transforming and saving target annotations to downsampled source image space : not requested')
                print('')
            
            
        elif self.downsampling_img == 'target':
            # transform and save source template to ds target image space as requested
            if self.brp['source-to-target-downsampling-save-annotations'] == True:
                
                if self.source_anno_path != []:
                    print('')
                    print('  transforming and saving source annotations to ds..')
                    
                    for i, s in enumerate(self.source_anno_path):
                        
                        if self.source_anno_path_ds[i].exists() == False: 
                            # only transform if output does not exist
                            if self.source_anno_img[i] == None:
                                print('  loading source anno image : ' + 
                                  self.get_relative_path(self.source_anno_path[i]) )
                                src_anno_img = self.load_image(self.source_anno_path[i])
                            else:
                                src_anno_img = self.source_anno_img[i]
                            
                            
                            if self.src_tar_pm is None:
                                print('  source to target paramater maps not loaded - loading files..')
                                self.src_tar_pm = self.load_pm_files( self.src_tar_pm_paths )
                                if self.src_tar_pm == None:
                                    print("ERROR : src_tar_ds_pm files do not exist - run register() first")
                                self.src_tar_pm_anno = self.edit_pms_nearest_neighbour(self.src_tar_pm)
                            
                            print('  transforming source annotation to downsampled target..')
                            print('    image : ' + 
                                    self.get_relative_path(self.source_anno_path[i]) )
                            
                            for j, pm in enumerate(self.src_tar_pm_paths):
                                print('    source-to-target paramter map file '+
                                        str(j) + ' : ' + 
                                        self.get_relative_path(pm) )
                            print('========================================================================')
                            print('')
                            print('')
                            
                            img_ds_tar = self.transform_image(src_anno_img, self.src_tar_pm_anno)
                            
                            self.save_image(img_ds_tar, self.source_anno_path_ds[i])
                            
                        else:
                            print('')
                            print('  source annotation to downsampled target : exists')
                            print('')
                    
                else:
                    print('')
                    print('  transforming and saving source annotations to downsampled target image space : no annotations to process')
                    print('')
                
            else:
                print('')
                print('  transforming and saving source annotations to downsampled target image space : not requested')
                print('')
        
    
    
    
    
    
    def transform_save_low_ds_images(self):
        
        if self.downsampling_img == 'source':
            # transform and save target template to ds source image space as requested
            if self.brp['target-to-source-downsampling-save-images'] == True:
                
                if self.target_image_paths != []:
                    print('')
                    print('  transforming and saving target images to ds..')
                    
                    for i, s in enumerate(self.target_image_paths):
                        
                        if self.target_image_paths_ds[i].exists() == False: 
                            # only transform if output does not exist
                            if self.target_image_imgs[i] == None:
                                print('  loading target image : ' + 
                                  self.get_relative_path(self.target_image_paths[i]) )
                                tar_img = self.load_image(self.target_image_paths[i])
                            else:
                                tar_img = self.target_image_imgs[i]
                            
                            
                            if self.tar_src_pm is None:
                                print('  target to source paramater maps not loaded - loading files..')
                                self.tar_src_pm = self.load_pm_files( self.tar_src_pm_paths )
                                if self.tar_src_pm == None:
                                    print("ERROR : tar_src_ds_pm files do not exist - run register() first")
                            
                            print('  transforming target image to downsampled source..')
                            print('    image : ' + 
                                    self.get_relative_path(self.target_image_paths[i]) )
                            
                            for j, pm in enumerate(self.tar_src_pm_paths):
                                print('    target-to-source paramter map file '+
                                        str(j) + ' : ' + 
                                        self.get_relative_path(pm) )
                            print('========================================================================')
                            print('')
                            print('')
                            
                            img_ds_src = self.transform_image(tar_img, self.tar_src_pm)
                            
                            self.save_image(img_ds_src, self.target_image_paths_ds[i])
                            
                        else:
                            print('')
                            print('  target image to downsampled source : exists')
                            print('')
                    
                else:
                    print('')
                    print('  transforming and saving target images to downsampled source image space : no images to process')
                    print('')
                    
                
            else:
                print('')
                print('  transforming and saving target images to downsampled source image space : not requested')
                print('')
            
            
        elif self.downsampling_img == 'target':
            # transform and save source template to ds target image space as requested
            if self.brp['source-to-target-downsampling-save-images'] == True:
                
                if self.source_image_paths != []:
                    print('')
                    print('  transforming and saving source images to ds..')
                    
                    for i, s in enumerate(self.source_image_paths):
                        
                        if self.source_anno_path_ds[i].exists() == False: 
                            # only transform if output does not exist
                            if self.source_image_imgs[i] == None:
                                print('  loading source image : ' + 
                                  self.get_relative_path(self.source_image_paths[i]) )
                                src_img = self.load_image(self.source_image_paths[i])
                            else:
                                src_img = self.source_image_imgs[i]
                            
                            
                            if self.src_tar_pm is None:
                                print('  source to target paramater maps not loaded - loading files..')
                                self.src_tar_pm = self.load_pm_files( self.src_tar_pm_paths )
                                if self.src_tar_pm == None:
                                    print("ERROR : src_tar_ds_pm files do not exist - run register() first")
                            
                            print('  transforming source image to downsampled target..')
                            print('    image : ' + 
                                    self.get_relative_path(self.source_image_paths[i]) )
                            
                            for j, pm in enumerate(self.src_tar_pm_paths):
                                print('    source-to-target paramter map file '+
                                        str(j) + ' : ' + 
                                        self.get_relative_path(pm) )
                            print('========================================================================')
                            print('')
                            print('')
                            
                            img_ds_tar = self.transform_image(src_img, self.src_tar_pm)
                            
                            self.save_image(img_ds_tar, self.source_image_paths_ds[i])
                            
                        else:
                            print('')
                            print('  source image to downsampled target : exists')
                            print('')
                    
                else:
                    print('')
                    print('  transforming and saving source images to downsampled target image space : no images to process')
                    print('')
                
            else:
                print('')
                print('  transforming and saving source images to downsampled target image space : not requested')
                print('')
        
    
    
    



class ImageFilterPipeline(object):
    
    
    def __init__(self, filter_string):
        
        self.img_filter = []
        self.img_filter_name = []
        self.img_filter_kernel = []
        # process string to determine the filter pipe
        # eg. M,1,1,0-GH,10,10,4 -> translates to 
            # median 4x4 XY THEN gaussian high-pass 10x10x4 XYZ
        filter_list = filter_string.split(sep='-')
        
        for f in filter_list:
            
            filter_code = ''.join([c for c in f if c.isupper()])
            filter_kernel = tuple([int(s) for s in f.split(',') if s.isdigit()])
            
            if filter_code == 'M':
                
                flt = sitk.MedianImageFilter()
                flt.SetRadius(filter_kernel)
                
                self.img_filter.append(flt)
                self.img_filter_name.append('Median')
                self.img_filter_kernel.append(filter_kernel)
                
            elif filter_code == 'E':
                
                flt = sitk.MeanImageFilter()
                flt.SetRadius(filter_kernel)
                
                self.img_filter.append(flt)
                self.img_filter_name.append('Mean')
                self.img_filter_kernel.append(filter_kernel)
                
            elif filter_code == 'G':
                
                flt = sitk.SmoothingRecursiveGaussianImageFilter()
                flt.SetSigma(filter_kernel)
                
                self.img_filter.append(flt)
                self.img_filter_name.append('Gaussian')
                self.img_filter_kernel.append(filter_kernel)
                
            elif filter_code == 'GH':
                
                flt = sitk.SmoothingRecursiveGaussianImageFilter()
                flt.SetSigma(filter_kernel)
                
                self.img_filter.append(flt)
                self.img_filter_name.append('Gaussian-High-Pass')
                self.img_filter_kernel.append(filter_kernel)
                
            
        
    
    
    def set_image(self, img):
        """
        Set the image
        
        MUST be of type sitk.Image

        Parameters
        ----------
        img : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        
        
        self.img = img
    
    
    
    def get_image(self):
        return self.img
    
    
    
    def dereference_image(self):
        """
        Dereference the images  in this filter pipeline
        
        This may be required to help free memory by discarding this objects 
        reference to the raw image.

        Returns
        -------
        None.

        """
        self.img = None
    
    def get_filtered_image(self):
        return self.filtered_img
    
    
    
    def execute_pipeline(self):
        
        img = self.img
        
        #print('')
        #print('  Execute ImageFilterPipeline:')
        for i, f in enumerate(self.img_filter):
            #print('    Filter Type : ' + self.img_filter_name[i])
            #print('    Filter Kernel : ' + str(self.img_filter_kernel[i]) )
            img = f.Execute(img)
            
        self.filtered_img = img
        
        return self.filtered_img
    
    
    
    def cast_image(self):
        
        # get the minimum and maximum values in self.img
        minMax = sitk.MinimumMaximumImageFilter()
        minMax.Execute(self.img)
        
        # cast with numpy - as sitk casting has weird rounding errors..?
        filtered_img_np = sitk.GetArrayFromImage(self.filtered_img)
        
        # first rescale the pixel values to those in the original matrix
        # THIS IS NEEDED as sometimes the rescaling produces values above or below
        # the ORIGINAL IMAGE - clearly this is an error, so just crop the pixel values
        # check the number of pixels below the Minimum for example:
        #np.count_nonzero(filtered_img_np < minMax.GetMinimum())
        
        filtered_img_np[ 
            filtered_img_np < 
            minMax.GetMinimum() ] = minMax.GetMinimum()
        
        filtered_img_np[ 
            filtered_img_np > 
            minMax.GetMaximum() ] = minMax.GetMaximum()
        
        # NO NEED TO CAST - this is incorrect as if one pixel is aberrantly set below
        # 0 by a long way, this permeates into this casting, where the 0 pixels are
        # artifically pushed up
        #self.filtered_img_cast = np.interp(
        #    filtered_img_np, 
        #    ( filtered_img_np.min(), filtered_img_np.max() ), 
        #    ( minMax.GetMinimum(), minMax.GetMaximum() ) 
        #        )
        
        # then CONVERT matrix to correct datatype
        if self.img.GetPixelIDTypeAsString() == '16-bit signed integer':
            filtered_img_np = filtered_img_np.astype('int16')
            
        elif self.img.GetPixelIDTypeAsString() == '8-bit signed integer':
            filtered_img_np = filtered_img_np.astype('int8')
            
        elif self.img.GetPixelIDTypeAsString() == '8-bit unsigned integer':
            filtered_img_np = filtered_img_np.astype('uint8')
            
        elif self.img.GetPixelIDTypeAsString() == '16-bit unsigned integer':
            filtered_img_np = filtered_img_np.astype('uint16')
            
        else: # default cast to unsigned 16-bit
            filtered_img_np = filtered_img_np.astype('uint16')
        
        # discard the np array
        #filtered_img_np = None
        
        self.filtered_img = filtered_img_np
        
    
    
    


