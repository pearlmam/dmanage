# -*- coding: utf-8 -*-
import natsort
import numpy as np
import re
import decimal
from pathlib import Path

from dmanage._compat import pd, HAS_PANDAS
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

def parse(files, checkVars=None, equiv='-', sep=['/','_'], asstring=False, nc=1):
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
    if not is_iterable(files): 
        files = [files]
        
    parse_filename_ = parallelize_iterator_method(_parse)
    results = parse_filename_(files, checkVars, equiv=equiv, sep=sep, asstring=asstring, nc=nc)

    # If pandas is installed, return a DataFrame; otherwise, fall back to a list of dicts
    if HAS_PANDAS:
        return pd.DataFrame(results)
    return results


def _parse(file, checkVars=None, equiv='-', sep=['/','_'], asstring=False):
    file = Path(file)
    if not isinstance(sep, (list, tuple)):
        sep = [sep]
    if (not is_iterable(checkVars)) and (checkVars is not None): 
        checkVars = [checkVars]
    
    # Pure Python dict eliminates Pandas dependency inside worker process
    row = {}

    file_name = str(file) if file.is_dir() else str(file.parent / file.stem)
    
    regex_pattern = '|'.join(map(re.escape, sep))
    file_name = re.split(regex_pattern, file_name)
    
    matchNumber = re.compile(r'-?\ *[0-9]+\.?[0-9]*(?:[Ee]\ *-?\ *[0-9]+)?')
    for part in file_name:
        if '-' in part:
            colVal = part.split(equiv, 1)
            col = colVal[0]
            valueStr = colVal[1]
            
            if valueStr[0].isalpha():
                value = []
            else:
                value = re.findall(matchNumber, valueStr)
            
            if (checkVars is None) or (col in checkVars):
                if len(value) == 0 or asstring:
                    row[col] = valueStr
                else:
                    row[col] = float(value[0])
                    
    return row


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