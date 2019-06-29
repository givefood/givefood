"""This file exists for backwards compatability.
Please use the separate backends found in either `djangae.contrib.gauth.datastore.backends` or
`djangae.contrib.gauth.sql.backends`.
"""
import warnings
from djangae.contrib.gauth.datastore.backends import AppEngineUserAPIBackend


warnings.warn(
    'AppEngineUserAPI is deprecated. Please use the specific backends from gauth.datastore '
    'or gauth.sql instead.'
)


class AppEngineUserAPI(AppEngineUserAPIBackend):
    pass



