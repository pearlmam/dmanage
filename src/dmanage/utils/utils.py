# -*- coding: utf-8 -*-

import collections
import pandas as pd

def is_iterable(obj):
    if isinstance(obj,collections.abc.Iterable) and not isinstance(obj, str) and not isinstance(obj,pd.core.frame.DataFrame):
        return True
    else:
        return False


if __name__ == "__main__":
    pass
