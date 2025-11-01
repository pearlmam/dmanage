# -*- coding: utf-8 -*-
import natsort
import numpy as np
import ntpath
import os


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

def parseFilename(files,checkVars):
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
    
    if type(files) == str: files = [files]
    data = np.zeros((len(files),len(checkVars)))
    for i in range(len(files)):
        file_name = ntpath.basename(files[i])
        file_name, _ = os.path.splitext(file_name) # remove extension
        #file_name = file_name.replace('.tiff','')
        file_name = file_name.split('_') # the data looks like [randomName, L-10000mW, T-100C, exp-100ms,ND-0 ]
        for j,checkVar in enumerate(checkVars):
            for part in file_name:
                if checkVar in part:
                    valueStr = part.replace(checkVar, '') # now the number and units remain: 10000mW
                    #data[i] = float(re.sub("[^0123456789\.-]","",valueStr))
                    data[i,j] = float(valueStr.translate(DD)) # this removes all but numbers, '-', and '.'
    if len(files)==1: data = data[0]
    return data
