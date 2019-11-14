import yaml
import os
import shutil


def load_credentials(path='./.credentials.yaml', template_location='./templates'):
    ''''
    Load credential from file.

    If the file is not found in the expected location, a template file is copied at this place. The user can thenappend
    the credentials.
    '''
    try:
        with open(path, 'r') as f:

            # load credentials from file
            credentials = yaml.load(f, Loader=yaml.SafeLoader)
            return credentials
    except IOError:
        print("Credentials could not be found. A template file was copied to {}. Please insert credentials into "
              "template and rerun code.".format(os.path.abspath(path)))
        shutil.copy(template_location, path)




