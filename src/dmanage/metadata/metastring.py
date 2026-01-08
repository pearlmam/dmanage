# -*- coding: utf-8 -*-
import natsort
import os
import pandas as pd
import re
import decimal

from dmanage.utils.objinfo import is_iterable
from dmanage.methods.wrapper import parallelize_iterator_method

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
    if -3 < decimal.Decimal(val).adjusted() < 3:
        mantissa_template = "{:.%df}" % numDecimals
        string = mantissa_template.format(val)
    else:
        string = adjusted_scientific_notation(val,num_decimals=numDecimals,exponent_pad=1)
        # string = "{0: >10}".format(string)
    
    return string



def compose(dataStruct, equiv='-', sep='_', order=False,numDecimals=3):
    outString = ''
    if type(dataStruct) is dict:
        if order: keys = natsort.natsorted(list(dataStruct.keys()))
        else: keys = list(dataStruct.keys())
        for key in keys:
            value = dataStruct[key]
            if type(value) is not str:
                value = smartString(value,numDecimals)
            outString = outString + key + equiv + value + sep
        
    elif type(dataStruct) is list:
        if order: dataStruct = natsort.natsorted(dataStruct)
        
        for item in dataStruct:
            outString = outString + item + sep
            
    outString = (outString[::-1].replace(sep[::-1], '', 1))[::-1]  # remove last occurrence of sepStr
    return outString


# ??? this function also needs to also read all metadata with checkVars undefined
# ??? this also can only handle number values, need to include strings.
# ??? should return DF

def parse(files, checkVars=None, equiv='-', sep='_', nc=1):
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
    
    if not is_iterable(files): files = [files]
    parse_filename_ = parallelize_iterator_method(_parse)
    DF = parse_filename_(files,checkVars, equiv=equiv, sep=sep,nc=nc)
    if type(DF) is list:
        DF = pd.concat(DF).reset_index(drop=True)
    return DF


def _parse(file, checkVars=None, equiv='-', sep='_'):
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
    data : numpy.ndarray
        A numpy array containing the values associated with the identifiers for all the files
        Examples:
        filename = '/path/to/file/name_L-10mW_T-100C_exp-1ms_ND-0.tiff'
        output1 = parseFilename(files=filename, checkVars=['L-','T-','exp-','ND-'])
        output1 = np.array([10,100,1,0])

        filenames = ['/path/to/file/name_L-10mW_T-100C_exp-1ms_ND-0.tiff', '/path/to/file/name_L-500mW_T-400C_exp-25ms_ND-0.tiff']
        output2 = parseFilename(file=filenames, checkVars=['L','T','exp'])
        output2 = np.array([[10,100,1],[500,400,25]])
    """
    
    if (not is_iterable(checkVars)) and (checkVars is not None): checkVars = [checkVars]
    DF = pd.DataFrame()
    
    if os.path.basename(file) == '':
        # it's a directory and do not remove extension
        file_name = os.path.basename(os.path.dirname(file))
    else:
        
        file_name = os.path.basename(file)
        file_name, _ = os.path.splitext(file_name) # remove extension
    #file_name = file_name.replace('.tiff','')
    file_name = file_name.split(sep) # the data looks like [randomName, L-10000mW, T-100C, exp-100ms,ND-0 ]
    matchNumber = re.compile('-?\\ *[0-9]+\\.?[0-9]*(?:[Ee]\\ *-?\\ *[0-9]+)?')
    for part in file_name:
        if '-' in part:
            colVal = part.split(equiv,1)
            col = colVal[0]
            valueStr = colVal[1] # now the number and units remain: 10000mW
            #data[i] = float(re.sub("[^0123456789\.-]","",valueStr))
            
            if valueStr[0].isalpha():
                value = []
            else:
                value = re.findall(matchNumber, valueStr)  # get value without units (if units exist)
            
            if (checkVars is None) or (col in checkVars):
                if len(value) == 0:     # the value is a string
                    DF[col] = [valueStr]
                else:    # the value has a number in it, we hope it is a number and not 'value1'
                    # add units if they exist ???
                    DF[col] = [float(value[0])] # this removes all but numbers, '-', and '.'
    return DF


if __name__ == "__main__":
    fileName = '/path/to/file/name_L-10mW_T--100C_exp-1ms_V--100.0e-3_ND-0_target-seeds/'
    checkVars=['target','L','T','exp','ND']
    
    DF = parse(fileName, checkVars=None, nc=1)
    print(DF)
    fileNames = ['/path/to/file/name_L-10mW_T-2.0e-2_exp-1ms_V--100e-3_ND-0_target-seeds.tiff']*10
    DF = parse(fileNames, checkVars=None, nc=1)
    print(DF)

    

