Metadata Registration API
=========================
A flask microservice to register and manage Study metadata via an API.

Documentation
-------------
Sphinx documentation is available in :ref:`./docs/source/index.rst` to directly access the documentation.


Purpose
-------
This package was written during a six month internship and was developed as part of the Study Registration Tool
prototype.

Coverage & Documentation
------------
Run coverage with:

.. code-block:: console

    $ coverage run ./test/test_main.py && coverage report -m

Run sphinx documentation with:

.. code-block:: console

    $ cd docs
    $ sphinx-apidoc -f -o ./source/modules ../ && make html


Authors
-------
* **Rafael Müller** <mailto:rafael.mueller1@gmail.com> - Initial work
* **Laura Badi** - Supervisor