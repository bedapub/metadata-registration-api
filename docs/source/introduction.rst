===============
Getting started
===============
The API consists of multiple resources. An overview of the resources is available as swagger documentation. The
swagger documentation is accessible via the index of the url. If you run the software locally, the swagger
documentation is found under `http://127.0.0.1:5001`_.


Resources
-------------
The API has several resources including `properties`, `controlled vocabularies`, `forms`, `studies` and `users`. The
API follows the REST principle.


Access
------
Some API commands require an access token. As a registered user you can generate an access token by sending your
email address and password as a post request to `user/login`_. The server will response with an access token.

The access token has to be transmitted in the header of each restricted request as value of `x-access-token`.

.. code-block:: json

   {"x-access-token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiNWRmMjMyMzE2MzI4MzdiYmU2YmFmODY4IiwiaWF0IjoxNTc4NTg3MjczLCJleHAiOjE1Nzg1ODkwNzN9.PGB-jyqdcpz3LmwOeMP1rxa9a7tVizHqh3EceFWy9dI"}

The access token is only limited for a limited time span. Afterwards, a new token has to be generated.
