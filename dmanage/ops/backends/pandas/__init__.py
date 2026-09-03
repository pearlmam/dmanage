# -*- coding: utf-8 -*-

from dmanage._compat import HAS_PANDAS

if not HAS_PANDAS:
    raise ImportError(
        "The Pandas backend requires 'pandas'. "
        "Please install it using 'pip install pandas'."
    )

from . import convert,plot,fft,signal,helper,linalg,vector