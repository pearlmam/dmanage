# -*- coding: utf-8 -*-

import inspect

def rebuild_signature(params):
    pos_or_kw = []
    var_pos = None
    kw_only = []
    var_kw = None

    for p in params:
        if p.kind == inspect.Parameter.VAR_POSITIONAL:
            var_pos = p
        elif p.kind == inspect.Parameter.VAR_KEYWORD:
            var_kw = p
        elif p.kind == inspect.Parameter.KEYWORD_ONLY:
            kw_only.append(p)
        else:
            pos_or_kw.append(p)

    ordered = pos_or_kw
    if var_pos:
        ordered.append(var_pos)
    ordered.extend(kw_only)
    if var_kw:
        ordered.append(var_kw)

    return ordered

def check_variadic(sig):
    check_kwarg = False
    check_arg = False
    for p in sig.parameters.values():
        if p.kind == inspect.Parameter.VAR_POSITIONAL:
            check_arg = True
        if p.kind == inspect.Parameter.VAR_KEYWORD:
            check_kwarg = True
    return check_kwarg and check_arg

def overwrite_defaults(sig, **overrides):
    new_params = [
        p.replace(default=overrides[p.name]) if p.name in overrides else p
        for p in sig.parameters.values()
    ]
    return sig.replace(parameters=new_params)