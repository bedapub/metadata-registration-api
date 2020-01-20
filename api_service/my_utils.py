import yaml
import os
from pathlib import Path


def load_credentials(filename=".credentials.yaml"):
    """" Load credential from file. """
    try:
        # Navigate to project root directory
        location = Path(__file__).parents[1]
        path = os.path.join(location, filename)
        with open(path, 'r') as f:
            # load credentials from file
            credentials = yaml.load(f, Loader=yaml.SafeLoader)
            return credentials
    except IOError:
        print("Could not find credentials file. Credentials are expected to be in the project root directory.")

