""" Script to automatically create a credential template file from an existing .credential file """

import re


def remove_credentials(input_filename, output_filename):
    """ Remove credentials from file

    Read input_filename and loops through every line, removes the text after the first colon, and writes the
    remaining content into the output_file
    """
    pattern = re.compile(r"([ \t]*\w+:)[?\s]([^&|\s].*)")
    header = \
        """\
# ----------------------------------------------------------------------------------------------------------------------
# Credentials template file
# Use this file as a template for the .credentials file. Before use, rename this file to `.credentials` and replace 
# all quotes (\"\") with your credentials.
# ----------------------------------------------------------------------------------------------------------------------
        """

    with open(input_filename, "r") as f_input:
        with open(output_filename, "w") as f_output:

            f_output.write(header)

            for line in f_input:
                if pattern.match(line):
                    line = pattern.sub(r'\1 ""', line)
                f_output.write(line)


if __name__ == '__main__':

    remove_credentials(input_filename=".credentials.yaml",
                       output_filename="credentials_template.yaml")
