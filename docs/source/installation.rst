============
Installation
============
This chapter describes how to install and setup the metadata registration API (hereafter API). Before you can install
the project, make sure that you meet the requisites:

Requisites
==========

**Database**
The API uses MongoDB as data store. Independent on how you install the API, make sure you have the necessary
credentials to access your MongoDB instance.

**Dependencies**
The API has two internal dependencies. These dependencies are the 'State Machine' and the 'Dynamic Form'. Both
projects are listed as git repositories in the `requirements.txt` document. To download them, you must be able
to access github with a SSH key. Check
`here <https://help.github.com/en/github/authenticating-to-github/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent>`_
for a better description.

**Credentials**
A configuration file is needed. Since the file stores all credentials of the application, it is called
`.credentials .yaml`. We have to create it because it is not shipped with the git repository. Create this file and add
all the config information.

Setup
============

The API can be installed in three different ways:

* :ref:`As a podman container <Run as podman container>`
* :ref:`As a docker container <Run as docker container>`
* :ref:`In a conda environment <Run in a conda environment>`

Although all three approaches work, we recommend running it either as a docker or podman container since it usually
takes longer and is more error prone when installing the API in a conda environment.


Run as podman container
-----------------------------

After, you we have met the requestsite, clone the git repository into our preferred directory. Change into the root
directory of the project and copy the ssh private key (i. e. id_rsa) and the `.credentials.yaml`. Finally execute the
following command:

.. code-block:: console

    $ ./start_podman.sh

The script checks if an identical container is already running. If this is the case, the container is stopped and
removed, and a new container is build and executed.


Run as docker container
-----------------------------

After, you we have met the requestsite, clone the git repository into our preferred directory. Change into the root
directory of the project and copy the ssh private key (i. e. id_rsa) and the `.credentials.yaml`. Finally execute the
following command:

.. code-block:: console

    $ ./start_docker.sh

The script checks if an identical container is already running. If this is the case, the container is stopped and
removed, and a new container is build and executed.

Run in a conda environment
------------------------------
[Documentation not available]

..
        **Get code and create environment**

        In a first step, we clone the git repository into our preferred directory and create a new conda environment. After
        we activated the environment, we install the required python packages through pip.

        .. code-block:: bash

            $git clone git@github.roche.com:rafaelsm/metadata_registration_API.git
            $conda env --name metadata_registration python=3.7`
            $conda activate metadata_registration`
            $pip install -r requirements.txt


        **Configure application**

        Secondly, we need to configure the application. This is done through a file called `.credentials.yaml`. Currently,
        this file does not exist in our directory. However, in the application root directory you will find a template file
        called `.credentials_template.yaml`. Create a copy of this file and assign it the name `.credentials.yaml`. we open the
        file in our preferred text editor and replace the empty strings with our authentication data.

        .. code-block:: bash

            $cp .credentials_template.yaml .credentials.yaml
            $vim .credentials.yaml


        **Run the application**

        Finally, we can run the application. In our example, we will used `gunicorn` with four workers. Before executing the
        application make sure that the set port is free and that you created the log file .

        .. code-block:: bash

            $touch ./metadata_registration.log
            $gunicorn --bind 0.0.0.0:5001 -w 4 --access-logfile ./metadata_registration_api.log --error-logfile ./metadata_registration_api.log --chdir ./metadata/app wsgi:app&


