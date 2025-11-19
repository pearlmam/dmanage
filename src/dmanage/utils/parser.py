# -*- coding: utf-8 -*-
import natsort
import numpy as np
import ntpath
import os
import pandas as pd
import re

from dmanage.utils.utils import isIterable
from dmanage.methods.wrapper import parallelize_iterator_method

def genSaveLoc(varDict):
    outString = ''
    for key,value in varDict.items():
        outString = outString + key + '-' + value + '/'
    return outString


def genSaveString(dataStruct,equivStr='-',sepStr='/',order=False):
    outString = ''
    if type(dataStruct) is dict:
        if order: keys = natsort.natsorted(list(dataStruct.keys()))
        else: keys = list(dataStruct.keys())
        for key in keys:
            outString = outString + key + equivStr + dataStruct[key] + sepStr
        
    elif type(dataStruct) is list:
        if order: dataStruct = natsort.natsorted(dataStruct)
        
        for item in dataStruct:
            outString = outString + item + sepStr
            
    outString = (outString[::-1].replace(sepStr[::-1],'',1))[::-1]  # remove last occurance of sepStr
    return outString

class Del:
    def __init__(self, keep='0123456789-.'):
      self.comp = dict((ord(c),c) for c in keep)
    def __getitem__(self, k):
      return self.comp.get(k)
DD = Del()


# ??? this function also needs to also read all metadata with checkVars undefined
# ??? this also can only handle number values, need to include strings.
# ??? should return DF

def parseFilename(files,checkVars=None,nc=1):
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
        A numpy array containing the values associated with the identifiers for all of the files
        Examples:
        filename = '/path/to/file/name_L-10mW_T-100C_exp-1ms_ND-0.tiff'
        output1 = parseFilename(files=filename, checkVars=['L-','T-','exp-','ND-'])
        output1 = np.array([10,100,1,0])

        filenames = ['/path/to/file/name_L-10mW_T-100C_exp-1ms_ND-0.tiff', '/path/to/file/name_L-500mW_T-400C_exp-25ms_ND-0.tiff']
        output2 = parseFilename(file=filenames, checkVars=['L-','T-','exp-'])
        output2 = np.array([[10,100,1],[500,400,25]])
    """
    
    if not isIterable(files): files = [files]
    parseFileName = parallelize_iterator_method(_parseFilename)
    DF = parseFileName(files,checkVars,nc=nc)
    if type(DF) is list:
        DF = pd.concat(DF).reset_index(drop=True)
    return DF


def _parseFilename(file,checkVars):
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
        A numpy array containing the values associated with the identifiers for all of the files
        Examples:
        filename = '/path/to/file/name_L-10mW_T-100C_exp-1ms_ND-0.tiff'
        output1 = parseFilename(files=filename, checkVars=['L-','T-','exp-','ND-'])
        output1 = np.array([10,100,1,0])

        filenames = ['/path/to/file/name_L-10mW_T-100C_exp-1ms_ND-0.tiff', '/path/to/file/name_L-500mW_T-400C_exp-25ms_ND-0.tiff']
        output2 = parseFilename(file=filenames, checkVars=['L-','T-','exp-'])
        output2 = np.array([[10,100,1],[500,400,25]])
    """
    
    if (not isIterable(checkVars)) and (checkVars is not None): checkVars = [checkVars]
    DF = pd.DataFrame()
    
    if os.path.basename(file) == '':
        # its a directory and do not remove extension
        file_name = os.path.basename(os.path.dirname(file))
    else:
        
        file_name = os.path.basename(file)
        file_name, _ = os.path.splitext(file_name) # remove extension
    #file_name = file_name.replace('.tiff','')
    file_name = file_name.split('_') # the data looks like [randomName, L-10000mW, T-100C, exp-100ms,ND-0 ]
    matchNumber = re.compile('-?\\ *[0-9]+\\.?[0-9]*(?:[Ee]\\ *-?\\ *[0-9]+)?')
    for part in file_name:
        if '-' in part:
            colVal = part.split('-',1)
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
    
    DF = parseFilename(fileName,checkVars=None,nc=1)
    print(DF)
    fileNames = ['/path/to/file/name_L-10mW_T-2.0e-2_exp-1ms_V--100e-3_ND-0_target-seeds.tiff']*10
    DF = parseFilename(fileNames,checkVars=None,nc=1)
    print(DF)

    

