# -*- coding: utf-8 -*-
import natsort
import numpy as np
import re
import decimal
from datetime import datetime
from pathlib import Path

from dmanage import _compat
from dmanage._compat import pd
from dmanage.utils.objinfo import is_iterable
from dmanage.parallel import parallelize_iterator_method

__all__ = ["compose","parse","smartString"]

def adjusted_scientific_notation(val,num_decimals=2,exponent_pad=1):
    exponent_template = "{:0>%d}" % exponent_pad
    mantissa_template = "{:.%df}" % num_decimals
    
    order_of_magnitude = decimal.Decimal(val).adjusted()
    nearest_lower_third = 3*(order_of_magnitude//3)
    adjusted_mantissa = val*10**(-nearest_lower_third)
    adjusted_mantissa_string = mantissa_template.format(adjusted_mantissa)
    adjusted_exponent_string = "+-"[nearest_lower_third<0] + exponent_template.format(abs(nearest_lower_third))
    return adjusted_mantissa_string+"E"+adjusted_exponent_string

def smartString(val,numDecimals=3):
    if isinstance(val, np.generic):  # catches np.bool_, np.float64, etc.
        val = val.item()
    if (val == 1 or val == 0) and isinstance(val,(bool,int)):
        string = str(int(val))   # write booleans as '0' or '1'
    elif -3 < decimal.Decimal(val).adjusted() < 3:
        mantissa_template = "{:.%df}" % numDecimals
        string = mantissa_template.format(val)
    else:
        string = adjusted_scientific_notation(val,num_decimals=numDecimals,exponent_pad=1)
        # string = "{0: >10}".format(string)
    
    return string



def compose(dataStruct, equiv='-', sep='_', order=False, format=None, numDecimals=3):
    if len(dataStruct) < 1:
        return ''

    # Check object type strings to avoid importing pandas
    obj_type = type(dataStruct).__name__
    obj_module = getattr(type(dataStruct), '__module__', '')

    if obj_module.startswith('pandas'):
        if obj_type == 'DataFrame':
            dataStruct = dataStruct.iloc[0].to_dict()
        elif obj_type == 'Series':
            dataStruct = dataStruct.to_dict()

    ## ensure lengths of format and dataStruct are equal and coerce them
    if not isinstance(format, (list, tuple)):
        format = [format] * len(dataStruct)
    lenDiff = len(dataStruct) - len(format)
    if lenDiff > 0:
        format = format + [None] * lenDiff
    elif lenDiff < 0:
        format = format[:lenDiff]
    outString = ''

    if isinstance(dataStruct, dict):
        if order:
            keys = natsort.natsorted(list(dataStruct.keys()))
        else:
            keys = list(dataStruct.keys())
        for key, f in zip(keys, format):
            value = dataStruct[key]
            if not isinstance(value, str) and f is None:
                value = smartString(value, numDecimals)
            elif not isinstance(value, str) and f is not None:
                value = f % value
            outString = outString + key + equiv + value + sep

    elif isinstance(dataStruct, list):
        if order:
            dataStruct = natsort.natsorted(dataStruct)

        for item in dataStruct:
            outString = outString + item + sep

    outString = (outString[::-1].replace(sep[::-1], '', 1))[::-1]  # remove last occurrence of sep
    return outString


# ??? this function also needs to also read all metadata with checkVars undefined
# ??? this also can only handle number values, need to include strings.
# ??? should return DF

def parse(files, checkVars=None, equiv='-', sep=['/','_'], fmt=None, nc=1):
    """ Description
    this parses through the filename to get variable values

    Parameters
    ----------
    files : str, list
        string or list/array of strings, file location(s)
    checkVars : list
        contains the identifiers of the desired variables (ex. ['L-','T-','exp-','ND-']).

    Returns
    -------
    data : numpy.array
        A numpy array containing the values associated with the identifiers for all the files
        Examples:
        filename = '/path/to/file/name_L-10mW_T-100C_exp-1ms_ND-0.tiff'
        output1 = parseFilename(files=filename, checkVars=['L-','T-','exp-','ND-'])
        output1 = np.array([10,100,1,0])

        filenames = ['/path/to/file/name_L-10mW_T-100C_exp-1ms_ND-0.tiff', '/path/to/file/name_L-500mW_T-400C_exp-25ms_ND-0.tiff']
        output2 = parseFilename(file=filenames, checkVars=['L-','T-','exp-'])
        output2 = np.array([[10,100,1],[500,400,25]])
    """
    if not is_iterable(files) or isinstance(files, str): 
        files = [files]
        
    parse_filename_ = parallelize_iterator_method(_parse)
    results = parse_filename_(files, checkVars, equiv=equiv, sep=sep, fmt=fmt, nc=nc)

    if getattr(_compat, "HAS_PANDAS", False):
        return pd.DataFrame(results)
    return results


def _parse(file, checkVars=None, equiv='-', sep=['/', '_'], fmt=None):
    file = Path(file)
    if not isinstance(sep, (list, tuple)):
        sep = [sep]

    if checkVars is not None:
        if isinstance(checkVars, str) or not hasattr(checkVars, '__iter__'):
            checkVars = [checkVars]
        checkVars = [str(v).rstrip(equiv) for v in checkVars]

    # Normalize list-like `fmt` (lists, tuples, arrays)
    fmt_map = None
    is_fmt_sequence = (
        hasattr(fmt, '__iter__') 
        and not isinstance(fmt, (str, bytes, dict, type))
    )

    if is_fmt_sequence:
        fmt_list = list(fmt)
        if checkVars is not None:
            # Pair checkVars order directly to fmt rules
            fmt_map = {var: fmt_list[i] for i, var in enumerate(checkVars) if i < len(fmt_list)}

    row = {}
    file_name = str(file) if file.is_dir() else str(file.parent / file.stem)
    regex_pattern = '|'.join(map(re.escape, sep))
    parts = re.split(regex_pattern, file_name)
    
    discovery_idx = 0
    for part in parts:
        if equiv in part:
            col, value_str = part.split(equiv, 1)

            if checkVars is None or col in checkVars:
                # Rule selection priority: Dict -> Formatted Sequence -> Discovery Order -> Scalar Rule
                if isinstance(fmt, dict):
                    col_rule = fmt.get(col)
                elif fmt_map is not None:
                    col_rule = fmt_map.get(col)
                elif is_fmt_sequence:
                    col_rule = fmt_list[discovery_idx] if discovery_idx < len(fmt_list) else None
                else:
                    col_rule = fmt

                try:
                    row[col] = format_value(value_str, col_rule)
                except (ValueError, TypeError):
                    row[col] = value_str

                discovery_idx += 1

    return row


def format_value(val_str, rule):
    regex_number = re.compile(r'-?\ *[0-9]+\.?[0-9]*(?:[Ee]\ *-?\ *[0-9]+)?')

    # Forced string
    if rule in (str, 'str'):
        return val_str

    # Forced numeric types
    if rule in (int, 'int'):
        nums = regex_number.findall(val_str)
        return int(float(nums[0])) if nums else int(val_str)
    if rule in (float, 'float'):
        nums = regex_number.findall(val_str)
        return float(nums[0]) if nums else float(val_str)

    # Forced datetime by strptime pattern or ISO
    if isinstance(rule, str) and '%' in rule:
        return datetime.strptime(val_str, rule)
    if rule in (datetime, 'datetime', 'iso'):
        return datetime.fromisoformat(val_str)

    # Automatic / Default Mode (rule is None)
    if len(val_str) >= 8 and '-' in val_str:
        try:
            return datetime.fromisoformat(val_str)
        except ValueError:
            pass

    if val_str and not val_str[0].isalpha():
        nums = regex_number.findall(val_str)
        if nums and nums[0]:
            return float(nums[0])

    return val_str

if __name__ == "__main__":
    # fileName = '/path/to/file/name_L-10mW_T--100C_exp-1ms_V--100.0e-3_ND-0_target-seeds/'
    # checkVars=['target','L','T','exp','ND']
    
    # DF = parse(fileName, checkVars=None, nc=1)
    # print(DF)
    # fileNames = ['/path/to/file/name_L-10mW_T-2.0e-2_exp-1ms_V--100e-3_ND-0_target-seeds.tiff']*10
    # DF = parse(fileNames, checkVars=None, nc=1)
    # print(DF)

    a = {'var0':12e-3,'var1':12e-6}
    
    b = compose(a,format='%.6f')
    print(b)