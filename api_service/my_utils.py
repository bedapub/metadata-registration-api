import yaml
import os
import shutil


def load_credentials(path='./.credentials.yaml'):
    """" Load credential from file. """
    try:
        with open(path, 'r') as f:
            # load credentials from file
            credentials = yaml.load(f, Loader=yaml.SafeLoader)
            return credentials
    except IOError:
        print("Credentials could not be found.")

