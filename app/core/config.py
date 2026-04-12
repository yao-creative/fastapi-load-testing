"""
Configuration skeleton for the tutorial track.

Use this file when you are ready to move hard-coded tutorial values into one place.
"""


# TODO: define Redis broker URL.
# TODO: define Redis result backend URL.
# TODO: define queue names such as `light` and `heavy`.
# TODO: define any beat schedule intervals you want to reuse.
# TODO: switch to environment variables before adding a real Redis/Celery stack.


DEFAULT_CELERY_QUEUE = "light"
HEAVY_CELERY_QUEUE = "heavy"
