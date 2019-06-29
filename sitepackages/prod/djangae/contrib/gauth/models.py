"""This file exists for backwards compatability.
Please use the abstract or concrete models found in either:
`djangae.contrib.gauth.datastore` for applications using the datastore
backend or `djangae.contrib.gauth.sql` for applications using a relational
database backend
"""

import warnings

from djangae.contrib.gauth.datastore.models import (
    GaeAbstractDatastoreUser, GaeDatastoreUser
)


warnings.warn(
    'GaeAbstractDatastoreUser and GaeDatastoreUser have moved to djangae.contrib.gauth.datastore.models'
)
