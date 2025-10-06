#!/usr/bin/env python3
#
# @file    VsHdf5.py
#
# @brief   Methods for reading and writing VizSchema-compliant files
#
# @version $Id: VsHdf5.py 5520 2023-06-26 20:57:36Z veitzer $
#
# Copyright &copy; 2014-2022, Tech-X Corporation, Boulder, CO.
# All rights reserved.
#

import os
import sys
import six

try:
  import numpy
except ImportError as ex:
  print('Could not import numpy. Exiting.', file=sys.stderr)
  print(f'Import Error = {ex}', file=sys.stderr)
  print('\nsys.path (includes PYTHONPATH at startup):\n' + '\n'.join(sys.path), file=sys.stderr)
  sys.exit(1)

try:
  import tables
except ImportError as ex:
  print('Could not import tables. Exiting.', file=sys.stderr)
  print(f'Import Error = {ex}', file=sys.stderr)
  print('\nsys.path (includes PYTHONPATH at startup):\n' + '\n'.join(sys.path), file=sys.stderr)
  sys.exit(1)

# Check version of PyTables
tablesExplanation = '\nImported PyTables has version: ' + \
  str(tables.__version__) + '(' + str(os.path.dirname(tables.__file__)) + \
  '). \nModule VsHdf5 requires PyTables of version: 3.x. \
   \nSome functionality could not be available, especially for writing Histories.'
try:
  if int(tables.__version__.split('.')[0]) != 3:
    print('PyTables Version Warning: ' + str(tablesExplanation), file=sys.stderr)
except ValueError as ex:
  print('Could not determine PyTables version correctly. Exiting.', file=sys.stderr)
  print(f'Value Error = {ex}', file=sys.stderr)
  sys.exit(2)

class nullDev(object):
  @classmethod
  def write(self, w):
    pass

VsDEBUG = os.getenv('VsDEBUG')
DEBUG = False
if not VsDEBUG:
  import warnings
  warnings.simplefilter('ignore', FutureWarning)
else:
  DEBUG = True

def debug(str):
  if DEBUG:
    print(str)

class VsHdf5:
  """ Class containing low-level methods specific to Hdf5 reading and writing. This class is intended to be used as a data member for other, higher-level classes that need to access files using PyTables."""
## constructor
#
# @param self object pointer
#
  def __init__(self):
    self.fh = None;

## Open a file using tables. Could be called more than once
#
# @ param fileName name of the file to open
# @ param overWrite if it is ok to delete and existing file
#
  def open_file(self, fileName, mode='r'):
    debug('[open_file] Opening file: ' + fileName + ' in mode: ' + mode)
    try:
      self.fh = tables.open_file(fileName,mode=mode)
      debug('[open_file] Successfully opened file: ' + fileName)
    except:
      msg = '[open_file] Unable to open file, ' + fileName + '.  Does not exist?  Already open?'
      sys.stderr.write(msg + "\n")
      self.fh = None

## Close a file using tables
#
  def closeFile(self):
   if not self.fh:
     debug('[closeFile] No file has been opened yet, so can not close the file.')
     return
   else:
     if self.fh.isopen:
       try:
         debug('[closeFile] Trying to close file: ' + self.fh.filename)
         self.fh.close()
         debug('[closeFile] Closed file successfully.')
       except:
         debug('[closeFile] Could not close file. Assuming it does not exist.')
     else:
       debug('[closeFile] File is not open so it can not be closed.')

## Get an existing group. Return None if the group does not exist
#
# @param location file location where the group is
# @param name name of group to read
# @return gh handle to the group
#
  def openGroup(self, location, name):
    gh = None
    pathname = location + name
    pathname = pathname.replace('//','/')
    groupList = []
    for g in self.fh.walk_nodes(location, 'Group'):
      groupList.append((g._v_pathname).replace('//','/'))
      debug('[openGroup] Found groups: ' + ', '.join(groupList))
    if pathname in groupList:
      debug('[openGroup] Found: ' + pathname + ' in the list of groups in this file')
      try:
        debug('[openGroup] Trying to get group named: ' + pathname)
        gh = self.fh.get_node(location,name, 'Group')
        debug('[openGroup] success.')
      except:
        debug('[openGroup] Could not get a handle to group object: ' + pathname + '. Probably not a group.')
    else:
      debug('[openGroup] Did not find ' + name + ' in the list of groups in this file.')
    return gh

## Create and open a group. Return a handle to that group or None if unable to create the group.
#
# @param location file location to which the group is written
# @param name name of group to write and open
# @return gh handle to the group
#
  def create_group(self, location, name):
    gh = None
    qualifiedName = location + name
    groupList = []
    for g in self.fh.walk_nodes(location, 'Group'):
      groupList.append((g._v_pathname).replace('//','/'))
      debug('[create_group] Found groups: ' + ', '.join(groupList))
    if qualifiedName in groupList:
      debug('[create_group] Found ' + qualifiedName + ' in the list of groups in this file.')
      debug('[create_group] Not overwriting the group. Use openGroup() instead')
    else:
      try:
        debug('[create_group] Trying to create group named: ' + name)
        gh = self.fh.create_group(location, name)
        debug('[create_group] success.')
      except:
        debug('[create_group] Could not create group object: ' + name + '. Aborting mission.')
    return gh

## Delete an existing group.
#
# @param location file location where the group is
# @param name name of group to delete
# @return wasDeleted whether or not the group was deleted
#
  def deleteGroup(self, name, location='/'):
    wasDeleted = False
    pathname = location + name
    pathname = pathname.replace('//','/')
    groupList = []
    for g in self.fh.walk_nodes(location,'Group'):
      groupList.append((g._v_pathname).replace('//','/'))
      debug('[deleteGroup] Found groups: ' + ', '.join(groupList))
    if pathname in groupList:
      debug('[deleteGroup] Found ' + pathname + ' in the list of groups in this file')
      try:
        debug('[deleteGroup] Trying to delete group named: ' + pathname)
        gh = self.fh.remove_node(location, name, True) # recursive remove
        wasDeleted = True
        debug('[deleteGroup] success.')
      except:
        debug('[deleteGroup] Could not get a handle to group object: ' + pathname + '. Probably not a group.')
        debug('[deleteGroup] Not deleting: ' + pathname + '.')
    else:
      debug('[deleteGroup] Did not find ' + name + ' in the list of groups in this file')
    return wasDeleted

## Find an object in a file that has a named attribute with a given value
#
# @param attributeName name of the attribute to search for
# @param attributeValue value of the attribute to check for
#
# @return oh a handle to the object (group or dataset) or None if there is no match
  def findObject(self, attributeName, attributeValue):
    oh = None
    if self.fh.isopen == 0:
      debug('[findObject] No file is open. Bailing.')
      pass
    else:
      for nh in self.fh.walk_nodes('/'):
        for name in nh._v_attrs._f_list('user'):
          attr = nh._v_attrs[name].tolist() if type(nh._v_attrs[name]) is numpy.ndarray else nh._v_attrs[name]
          if type(attr) is numpy.bytes_:  attr = attr.decode('UTF-8')
          strAttr = str(attr)
          debug('[findObject] ' + name + ' : ' + strAttr)
          if (name, attr) == (attributeName, attributeValue):
            debug('[findObject] Found object with attribute/value pair: ' + str(attributeName) + ' : ' + str(attributeValue))
            return nh
    return oh

## Close a group
#
# @param gh handle to group to be closed
#
  def closeGroup(self, gh):
    if not gh:
      debug('[closeGroup] group is not open.')
    else:
      try:
        debug('[closeGroup] Trying to close group named: ' + gh._v_pathname)
        gh._f_close()
        debug('[closeGroup] success.')
      except:
        print('[closeGroup] Unable to close group. Assuming it is not open')

##
#
# Write an attribute
#
# @param pathname qualified pathname to which the attribute is written
# @param name name of attribute to write
# @param attribute attribute value
#
  def writeAttribute(self, pathname, name, attribute):
    nh = self.getNodeHandle(pathname)
    if nh is None:
      debug('[writeAttribute] Could not get handle to node ' + pathname + '.')
    else:
      try:
        debug('[writeAttribute] Trying to set attribute: ' + name + ' to path: ' + pathname)
        self.fh.set_node_attr(nh, name, attribute)
        debug('[writeAttribute] success.')
      except:
        print(f'[writeAttribute] Unable to set attribute: {name} to path: {pathname}. Attribute not written', file=sys.stderr)
        print(f'[writeAttribute] File: {self.fh.filename} was opened in mode: {self.fh.mode}', file=sys.stderr)

##
#
# Read an attribute
#
# @param pathname file pathname to which the attribute is written
# @name name of the attribute to read
# @return attribute the value of the attribute
#
  def readAttribute(self, pathname, name):
    attribute = None
    nh = self.getNodeHandle(pathname)
    if nh is None:
      debug('[readAttribute] Could not get handle to node ' + pathname + '.')
      debug('[readAttribute] The Dataset could be empty, which is ok, but it is '
            'possible that the program really could not get handle to the '
            'node ' + pathname + '.')
    try:
      debug('[readAttribute] Trying to get attribute: ' + name + ' at pathname: ' + pathname)
      attribute = self.fh.get_node_attr(nh, name)
      debug('[readAttribute] success.')
    except:
      print(f'[readAttribute] Unable to get attribute: {name} at pathname: {pathname}. Attribute not read', file=sys.stderr)
    return attribute

## Delete an existing attribute by pathname.
#
# @param location file location where the attribute is
# @param name name of attribute to delete
# @return wasDeleted whether or not the attribute was deleted
#
  def deleteAttribute(self, location, name):
    wasDeleted = False
    pathname = location + '/' + name
    pathname = pathname.replace('//','/')
    debug('[deleteAttribute] Trying to delete attribute named: ' + name + ' to location ' + location)
    try:
      self.fh.del_node_attr(location,name)
      wasDeleted = True
      debug('[deleteAttribute] success.')
    except:
      debug('[deleteAttribute] Could not delete Attribute: ' + pathname + '. Maybe it doesn\'t exist?')
    return wasDeleted

##
#
# Write a dataset
#
# @param location file location to which the attribute is written
# @param name name of dataset to write
# @param array name of the numpy array to write
# @param extendable False if dataset to be written should be extendable, e.g. Histories
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeDataset(self,
                   location,
                   name,
                   array,
                   extendable=False,
                   overwrite=False):
    if location is None:
      location = '/'
    if len(array) == 0:
      debug('[writeDataset] NOTE: Array ' + str(name) + ' is empty.')
    nh = self.getNodeHandle(location)
    if nh is None:
      debug('[writeDataset] Could not get handle to node ' + location + '.')
    else:
      try:
        if overwrite:
          debug('[writeDataset] Trying to delete array: ' + name + ' to location: ' + location)
          self.remove_node(name, location=location)
        ####debug('[writeDataset] Trying to write array: ' + name + ' to location: ' + location)
        if extendable:
          debug('[writeDataset] Trying to write extendable array: ' + name + ' to location: ' + location)
          try:
            arr = self.fh.create_earray(nh, name, obj=array)
            debug('[writeDataset] success.')
          except:
            print(f'[writeDataset] Unable to write extendable array: {name} to location: {location}. Dataset not written', file=sys.stderr)
            print(f'[writeDataset] File: {self.fh.filename} was opened in mode: {self.fh.mode}', file=sys.stderr)
            print('[writeDataset] Dataset will not be overwritten if it already exists.', file=sys.stderr)
            print('[writeDataset] Specify the overwrite keyword to be True to override.', file=sys.stderr)
        else:
          debug('[writeDataset] Trying to write constant-length array: ' + name + ' to location: ' + location)
          try:
            self.fh.create_array(nh, name, array)
            debug('[writeDataset] success.')
          except:
            print(f'[writeDataset] Unable to write array: {name} to location: {location}. Dataset not written', file=sys.stderr)
            print(f'[writeDataset] File: {self.fh.filename} was opened in mode: {self.fh.mode}', file=sys.stderr)
            print('[writeDataset] Dataset will not be overwritten if it already exists.', file=sys.stderr)
            print('[writeDataset] Specify the overwrite keyword to be True to override.', file=sys.stderr)
      except:
        print(f'[writeDataset] Unable to write array: {name} to location: {location}. Dataset not written', file=sys.stderr)
        print(f'[writeDataset] File: {self.fh.filename} was opened in mode: {self.fh.mode}', file=sys.stderr)
        print('[writeDataset] Dataset will not be overwritten if it already exists.', file=sys.stderr)
        print('[writeDataset] Specify the overwrite keyword to be True to override.', file=sys.stderr)

##
#
# Read a dataset.
#
# @param location location of the dataset to be read
# @param name name of the dataset
# @return array,attributes a numarray with the data if the dataset exists, empty numarray otherwise
# @return attributeList list of tuples of all attribute/value pairs in the dataset, None otherwise
#
  def readDataset(self, location, name):
######!!!!NOTE 7/2014 I don't think that this method is ever being called directly from within VsHdf5 classes. Mostly VsDatasetBase.readDataset() is being used, and it has a different signature. *sv
    pathname = location + '/' + name
    pathname = pathname.replace('//','/')
    array = numpy.empty(0)
    attributeList = []
    nh = self.getNodeHandle(pathname)
    if nh is None:
      debug('[readDataset] Could not get handle to node ' + pathname + '.')
      debug('[readAttribute] The Dataset could be empty, which is ok, but it is '
            'possible that the program really could not get handle to the '
            'node ' + pathname + '.')
    try:
      debug('[readDataset] Trying to read dataset at: ' + pathname)
      array = nh.read()
      debug('[readDataset] success.')
    except:
      debug('[readDataset] Could not read dataset at: ' + pathname)
    try:
      debug('[readDataset] Trying to read attributes in dataset: ' + pathname)
      for name in nh._v_attrs._f_list('user'):
        attr = nh._v_attrs[name]
        if type(attr) is numpy.bytes_:  attr = attr.decode('UTF-8')
        attributeList.append((name, attr))
      debug('[readDataset] success.')
    except:
      debug('[readDataset] Could not read any attributes in dataset: ' + pathname)
      debug('[readDataset] Assuming there are none.')
      attributeList = None
    if attributeList is not None and len(attributeList) == 0:
      attributeList = None

# Check and fix component Order if needed
    if attributeList is not None:
      compOrder = next((v[1] for v in attributeList if v[0] == 'vsIndexOrder'), None)
      if compOrder is not None and 'compMajorC' in compOrder:
# Make the first column the last column, e.g. convert compMajorC to compMinorC ordering
        for ind in list(range(array.ndim-1)):
          array = numpy.swapaxes(array, ind, ind+1)
    return array, attributeList

##
#
# Delete a dataset or group.
#
# @param location location of the dataset to be read
# @param name name of the dataset
#
  def remove_node(self, name, location='/'):
    try:
      debug('[remove_node] Removing node ' + location + name + '.')
      self.fh.remove_node(location, name=name)
      debug('[remove_node] success.')
    except:
      debug('[remove_node] Could not remove dataset at: ' + location + name)

##
#
# Get a handle to a node by pathname. Returns 0 if node does not exist
#
# @param pathname qualified pathname to the node
# @return nh handle to the node if it exists, zero otherwise
#
  def getNodeHandle(self, pathname):
    nh = None
    try:
      debug('[getNodeHandle] Trying to get the handle to node: ' + pathname)
      nh = self.fh.get_node(pathname)
      debug('[getNodeHandle] success.')
    except:
      debug('[getNodeHandle] There is no such node named: ' + pathname + '.')

# external link will be None if nh is not an external link or it can not be dereferenced
    tp = self.getExternalLinkHandle(nh)
    if tp != None: return tp
    else: return nh

## Get an attribute value by name from a list, namely the internal attribute list
#
# @param lst name of the attribute list
# @param attributeName name of the attribute
# @return attributeValue the value to be returned, or None if attribute is not in the list
#
  def attribute(self, lst, attributeName):
    attributeValue = None
    debug('[attribute] Searching list of attributes for entry named: ' + attributeName)
    for tup in lst:
      if tup[0] == attributeName:
        attributeValue = tup[1]
        debug('[attribute] Found attribute in list with value: ' + str(attributeValue))
    return attributeValue

## Assign an attribute. Namely, add an attribute to a list member.
#  Overwrites any attribute in the list with the same name.
#
# @param lst name of the attribute list
# @param name attribute name
# @param value attribute value
#
  def assignAttribute(self, lst, name, value):
    for att in lst:
      if att[0] == name:
        debug('[assignAttribute] Attribute: ' + name + ' exists in the list. Overwriting')
        self.removeAttribute(lst, name)
    lst.append((name, value))

## Remove an attribute from a list of attributes, namely the internal list
#
# @param lst name of the attribute list
# @param name attribute name to be removed
#
  def removeAttribute(self, lst, name):
    debug('Trying to remove attribute named: ' + name + ' from the attribute list.')
# A list of tuples, and the second could be of type numpy.bytes_, which need to be converted to str
    for ind in list(range(len(lst))):
      if type(lst[ind][1]) is numpy.bytes_: lst[ind] = (lst[ind][0], lst[ind][1].decode('UTF-8'))
    nAttributes = len(lst)
    attributeList = [(att[0], repr(att[1].tolist()) if type(att[1]) is numpy.ndarray else att[1]) for att in lst]
    debug('There are: ' + str(nAttributes) + ' attributes in the list of attributes for this object: ' + repr(attributeList))
    for att in lst:
      if att[0] == name:
        lst.remove(att)
        debug('Successfully removed attribute named: ' + name + ' from the attribute list.')
    nAttributes = len(lst)
    attributeList = [(att[0], repr(att[1].tolist()) if type(att[1]) is numpy.ndarray else att[1]) for att in lst]
    debug('There are: ' + str(nAttributes) + ' attributes in the list of attributes for this object: ' + repr(attributeList))

## Write an external link to a file
#
# @param fileName name of the file in which to create the link
# @param name name of the link to create in fileName
# @param target the target of the link, in file:ojbectPath notation
# @param location location to which the link is written
#
  def writeExternalLink(self, fileName, name, target, location='/'):
    pathname = location + '/' + name
    pathname = pathname.replace('//','/')
    self.open_file(fileName, mode='a')
    if not self.fh:
      debug('[VsHdf5:writeExternalLink] Could not open file: ' + fileName + ' for writing. Not writing external link.')
      return

    try:
      debug('[VsHdf5:writeExternalLink] Trying to create external link in file: ' + fileName + ' named: ' + name + ' pointing to target: ' + target)
      #print(location,name,target)
      try:
        nh = self.fh.get_node(pathname)
        if nh != None:
          if nh.__class__ is tables.link.ExternalLink:
            debug('[VsHdf5:writeExternalLink] An external link named: ' + pathname + ' already exists in the file: ' + fileName + '. Removing.')
            try:
              self.fh.remove_node(nh)
              debug('[VsHdf5:writeExternalLink] Removed external link: ' + pathname + ' from the file: ' + fileName + '.')
            except:
              debug('[VsHdf5:writeExternalLink] Could not remove external link: ' + pathname + ' from the file: ' + fileName + '.')
          else:
            debug('[VsHdf5:writeExternalLink] ' + pathname + ' already exists in the file: ' + fileName + ' but is not an external link. Not overwriting. Link not created.')
            self.closeFile()
            return
      except:
        debug('[VsHdf5:writeExternalLink] ' + pathname + ' does not exist in the file: ' + fileName + '. Trying to create it.')
      self.fh.create_external_link(location, name, target, createparents=True)
      debug('[VsHdf5:writeExternalLink] Success.')
    except:
      debug('[VsHdf5:writeExternalLink] Could not create external link in file: ' + fileName + ' named: ' + name + ' pointing to target: ' + target)
    self.closeFile()

## Dereference an external link. If the link is broken because the file does not exist, look for the linked file in the current directory.
#
# @param nh A handle to the link object
#
  def getExternalLinkHandle(self, nh):
    tp = None
    if nh != None and nh.__class__ is tables.link.ExternalLink:
      targetFile = (nh.target.split(':'))[0]
      targetGroup = (nh.target.split(':'))[1]
# check for existence of linked file
      if os.path.exists(targetFile):
        debug('[VsHdf5.getExternalLinkHandle] Found external link target file: ' + targetFile + '.')
      elif os.path.exists(os.path.basename(targetFile)):
        debug('[VsHdf5.getExternalLinkHandle] Could not find external link target file in directory: ' + targetFile + '. Trying to locate file in current directory.')
        debug('[VsHdf5.getExternalLinkHandle] Found external link target file in current working directory: ' + os.path.basename(targetFile) + '.')
        debug('[VsHdf5.getExternalLinkHandle] Renaming external link to point to file in current working directory.')
# this may not be the best solution, but I can not figure out a better way to fix a broken link like this so renaming the link to point to the file in the current directory.
        nh.target = os.path.basename(targetFile) + ':' + targetGroup
      else:
        debug('[VsHdf5.getExternalLinkHandle] Could not find external link target file: ' + os.path.basename(nh.target) + ' in either ' + os.path.dirname(nh.target) + ' or in current directory: ' + os.getcwd() + '.')
# finally dereference the link.
      try:
        debug('[VsHdf5.getExternalLinkHandle] Dereferencing link.')
        tp = nh.__call__()
        debug('[VsHdf5.getExternalLinkHandle] Success.')
      except:
        debug('[VsHdf5.getExternalLinkHandle] Could not dereference link. Target object may not exist in target file.')
        tp = None
    return tp

# Convience class functions that use VsHdf5

# vars is tuple of required variable name and value
  def required(self, vars, fn):
    for var in vars:
      if var[1] is None:
        print(f'[VsHdf5.{fn}]: No {var[0]} has been specified, but it is required.')
        print('[VsHdf5.{fn}]: Minimal usage: {fn}(' + ', '.join([s[0]+'='+s[0].upper() for s in vars])+')')
        sys.exit(11)
    return True

# returns an empty VsHdf5 History object
  def getEmptyHistory(self, name=None):
      return History(name=name)

# returns the VsHdf5 field object, and the attributes, but not the dataset
  def getHistory(self, fileName=None, historyName=None, name=None, location='/'):
    if self.required([('fileName', fileName), \
                      ('historyName', historyName)], 'getHistory'):
      h = History(name=name)
      d, a = h.readHistory(fileName, historyName, location=location)
      #return d, a
      return h, a

  def writeHistory(self, fileName=None, historyName=None, data=None, meshName=None, overwrite=False, location='/'):
    if self.required([('fileName', fileName), \
                      ('data', data), \
                      ('meshName', meshName), \
                      ('historyName', historyName)], 'writeHistory'):
    #if meshName == None:
    #  debug('[writeHistory]: No mesh was specified. History data MUST specify a valid mesh (typically 1D time mesh) on which the data is defined.')
    #  debug(usage)
    #  return False
      h = History(name=historyName)
      h.assignDataset(data)
      #meshName = mesh.name
      h.writeHistory(fileName, historyName=historyName, meshName=meshName, location=location, overwrite=overwrite)

# returns an empty VsHdf5 Field object
  def getEmptyField(self, name=None):
      return Field(name=name)

# returns the VsHdf5 field object, and the attributes, but not the dataset
  def getField(self, fileName=None, fieldName=None, name=None, location='/'):
    if self.required([('fileName', fileName), \
                      ('fieldName', fieldName)], 'getField'):
      f = Field(name=name)
      d, a = f.readField(fileName, fieldName=fieldName, location=location)
      #return d, a
      return f, a

  def writeField(self,
                 fileName=None,
                 data=None,
                 fieldName=None,
                 meshName=None,
                 limitsName=None,
                 timeGroupName=None,
                 offset='nodal',
                 dumpTime=0.0,
                 location='/',
                 indexOrder='compMinorC',
                 overwrite=False):
    if self.required([('fileName', fileName), \
                      ('data', data), \
                      ('meshName', meshName), \
                      ('limitsName', limitsName), \
                      ('timeGroupName', timeGroupName)], 'writeField'):
      f = Field()
      f.assignDataset(data)
      f.writeField(fileName,
                   fieldName=fieldName,
                   dumpTime=dumpTime,
                   offset=offset,
                   mesh=meshName,
                   limits=limitsName,
                   timeGroup=timeGroupName,
                   location=location,
                   indexOrder=indexOrder,
                   overwrite=overwrite)

# returns an empty VsHdf5 Limits object
  def getEmptyLimits(self, name=None):
      return Limits(name=name)

# returns the VsHdf5 limits object, and the name of the limits object
  def getLimits(self, fileName=None, name=None):
    if self.required([('fileName', fileName)], 'getLimits'):
      l = Limits(name=name)
      l.readLimits(fileName)
      return l, l.name

# Write a limits group to a file
  def writeLimits(self, fileName=None, limitsName=None, location='/', overwrite=False):
    if self.required([('fileName', fileName)], 'writeLimits'):
      l = Limits(name=limitsName)
      l.writeLimits(fileName, location=location, limitsName=limitsName, overwrite=overwrite)

# returns an empty VsHdf5 TimeGroup object
  def getEmptyTimeGroup(self, name=None):
      return TimeGroup(name=name)

# returns the VsHdf5 limits object, and the name of the limits object
  def getTimeGroup(self, fileName=None, name=None):
    if self.required([('fileName', fileName)], 'getTimeGroup'):
      l = TimeGroup(name=name)
      l.readTimeGroup(fileName)
      return l, l.name

# Write a time group to a file
  def writeTimeGroup(self, fileName=None, timeGroupName=None, dumpTime=None, dumpStep=0, location='/', overwrite=False):
    if self.required([('fileName', fileName), \
                      ('dumpTime', dumpTime)], 'writeTimeGroup'):
      t = TimeGroup()
      t.writeTimeGroup(fileName, timeGroupName=timeGroupName, dumpTime=dumpTime, dumpStep=dumpStep, location=location, overwrite=overwrite)

# returns an empty VsHdf5 Mesh object
  def getEmptyMesh(self, name=None, kind='uniformCartesian'):
    if kind == 'uniformCartesian':
      return UniformCartesianMesh(name=name)
    if kind == 'structured':
      return StructuredMesh(name=name)
    if kind == 'unstructured':
      return UnstructuredMesh(name=name)
    if kind == 'rectilinear':
      return RectilinearMesh(name=name)
    else:
      return Mesh(name=name)

# returns the VsHdf5 mesh object, and the name of the mesh object
  def getMesh(self, fileName=None, name=None):
    if self.required([('fileName', fileName)], 'getMesh'):
      m = Mesh(name=name)
      m.readMesh(fileName)
      return m, m.name

# Write a fully compliant mesh to a file
  def writeMesh(self, fileName=None, mesh=None, overwrite=False):
    if self.required([('fileName', fileName), \
                      ('mesh', mesh)], 'writeMesh'):
      mesh.writeMesh(fileName, meshName=mesh.name, overwrite=overwrite)

# returns an empty VsHdf5 RunInfo object
  def getEmptyRunInfo(self, name=None):
      return RunInfo(name=name)

# returns the VsHdf5 runInfo object, and the name of the runInfo object
  def getRunInfo(self, fileName=None, name=None):
    if self.required([('fileName', fileName)], 'getRunInfo'):
      r = RunInfo(name=name)
      r.readRunInfo(fileName)
      return r, r.name

# Write a runInfo group to a file
  def writeRunInfo(self, fileName=None, runInfo=None, overwrite=False):
    if self.required([('fileName', fileName), \
                      ('runInfo', runInfo)], 'writeRunInfo'):
      runInfo.writeRunInfo(fileName, overwrite=overwrite)

# returns an empty VsHdf5 Group object
  def getEmptyGroup(self, name=None):
      return Group(name=name)

# returns a VsHdf5 group object, and the name of the group object, e.g. derivedVars
  def getGroup(self, fileName=None, groupName=None, name=None):
    if self.required([('fileName', fileName), \
                      ('groupName', groupName)], 'getGroup'):
      g = Group(name=name)
      g.readGroup(fileName, groupName)
      return g, g.name

# returns an empty VsHdf5 Dataset object
  def getEmptyDataset(self, name=None):
      return Dataset(name=name)

# returns a VsHdf5 Dataset object, and the name of the Dataset object
  def getDataset(self, fileName=None, datasetName=None, name=None):
    if self.required([('fileName', fileName), \
                      ('datasetName', datasetName)], 'getDataset'):
      d = Dataset(name=name)
      d.readDataset(fileName, datasetName)
      return d, d.name

# returns a VsHdf5 Particles object, and the name of the Particles object
  def getParticles(self, fileName=None, particlesName=None, name=None):
    if self.required([('fileName', fileName), \
                      ('particlesName', particlesName)], 'getParticles'):
      p = Particles(name=name)
      d, a = p.readParticles(fileName, particlesName)
      return p, a

# returns a parsed VsHdf5 file
  def getVsFile(self, fileName=None, silent=False, noData=False):
    if self.required([('fileName', fileName)], 'getVsFile'):
      f = VsFileReader(fileName=fileName, silent=silent, noData=noData)
      return f

# Write a Particles dataset to a file
#  def writeParticles(self, fileName=None, runInfo=None, overwrite=False):
#    if self.required([('fileName', fileName), \
#                      ('particlesName', particlesName)], 'writeParticles'):
#      runInfo.writeRunInfo(fileName, overwrite=overwrite)

class VsBase:
  """ Base class containing useful methods to be used by other classes. Higher-level classes should inherit from this class."""
##
# Get a list of all nodes in a file. Does not return an iterator.
#
# @parameter fileName Name of the file to get the node pathnames from.
# @return pathNameList List of path names of all nodes in the file.
#
  def getNodePathList(self, fileName):
    pathNameList = []
    try:
      debug('[getNodePathList] Trying to open file: ' + fileName)
      self.vsw.open_file(fileName) # in read only mode
      debug('[getNodePathList] success.')
    except:
      debug('[getNodePathList] Could open file: ' + str(fileName))
    if self.vsw.fh:
      try:
        debug('[getNodePathList] Trying to get list of nodes in file: ' + str(self.vsw.fh.filename))
        for nh in self.vsw.fh.walk_nodes('/'):
          #print(nh._v_pathname)
          pathNameList.append((nh._v_pathname).replace('//','/'))
        debug('[getNodePathList] success.')
      except:
        debug('[getNodePathList] Could not get list of nodes in file: ' + str(self.vsw.fh.filename))
    return pathNameList

##
# Get a handle to a node by pathname. Returns None if node does not exist.
#
# @param pathname qualified pathname to the node
# @return nh handle to the node if it exists, None otherwise
#
  def getNodeHandle(self, pathname):
    nh = None
    try:
      debug('[VsBase.getNodeHandle()] Trying to get the handle to node: ' + pathname)
      nh = self.vsw.fh.get_node(pathname)
      debug('[VsBase.getNodeHandle()] success.')
    except:
      debug('[VsBase.getNodeHandle()] There is no such node named: ' + pathname + '.')

# external link will be None if nh is not an external link or it can not be dereferenced
    tp = self.vsw.getExternalLinkHandle(nh)
    if tp != None: return tp
    else: return nh

## Remove a node.
#
# @param pathname qualified pathname to the node
# @return nh handle to the node if it exists, zero otherwise
#
#def remove_node(self, pathname):
#  try:
#    debug('[VsBase.remove_node()] Trying to remove node: ' + pathname)
#    self.vsw.fh.remove_node(pathname)
#    debug('[VsBase.remove_node()] success.')
#  except:
#    debug('[VsBase.remove_node()] Could not remove node: ' + pathname)

## Get an attribute value by name from the attribute list
#
# @param attributeName name of the attribute
# @return attributeValue the value to be returned, or None if attribute is not in the list
#
  def attribute(self, attributeName):
    attributeValue = self.vsw.attribute(self.attributeList, attributeName)
    return attributeValue

## Assign an attribute and its value to the internal list of attributes
#
# @param name attribute name
# @param value attribute value
#
  def assignAttribute(self, name, value):
    if value is None:
      debug('[VsBase.assignAttribute()] Not assigning attribute ' + name + ' to None. Use removeAttribute() if this is what you really want to do.')
    else:
      self.vsw.assignAttribute(self.attributeList, name, value)

## Remove an attribute from the internal list of attributes
#
# @param name attribute name to be removed
#
  def removeAttribute(self, name):
    self.vsw.removeAttribute(self.attributeList, name)

## Check to see if a required object exists or has otherwise been set
#
# @param passedName name of the object as passed in or None
# @param internalName name of the object in the internal list of attributes, or None
# @param globalObject name of an externally defined object of the correct vsType
#
  def requires(self, passedName, internalName, globalObject):
    debug('[requires] checking to see if required object name has been defined or exists otherwise.')
    debug('passedName: ' + str(passedName))
    debug('internalName: ' + str(self.attribute(internalName)))
    debug('globalObject: ' + str(globalObject))
    if passedName is None:
      if self.attribute(internalName) is None:
        try:
          lenObjName = len(globalObject)
          debug('[requires] The object: ' + str(self.name) + ' has an attribute that associates it the the object named: ' + str(globalObject))
          self.assignAttribute(internalName, globalObject)
        except:
          print(f'[requires] The object: {self.name} requires that an object of type: {internalName} be defined.', file=sys.stderr)
          print('Please create or copy one.', file=sys.stderr)
          return None
      else:
        debug('[requires] The object: ' + str(self.name) + ' has an attribute that associates it the the object named: ' + str(self.attribute(internalName)))
    else:
      self.assignAttribute(internalName, passedName)
      debug('[requires] The object: ' + str(self.name) + ' has an attribute that associates it the the object named: ' + str(passedName))
    return True

## Check to see if an optional attribute value is given, use a default otherwise
#
# @param passedValue value of the attribute to use if provided
# @param internalName name of the attribute in the internal list of attributes to set
# @param defaultValue the default value of the attribute to use of no attribute passed
#
  def default(self, passedValue, internalName, defaultValue):
    debug('[default] checking to see if optional attribute has been provided or if default value should be used.')
    if not passedValue:
      if not self.attribute(internalName):
        self.assignAttribute(internalName, defaultValue)
        debug('[default] Set attribute: ' + internalName + ' to default value: ' + str(defaultValue))
      else:
        debug('[default] Attribute: ' + internalName + ' already exists. Not overwriting with default value.')
    else:
        self.assignAttribute(internalName, passedValue)
        debug('[default] Set attribute: ' + internalName + ' to value: ' + str(passedValue))

# Specific, often-used attributes get their own named access methods

## Get the type attribute
#
# @return The value of vsType, or None if that attribute is not defined
#
  def getType(self):
    return self.vsw.attribute(self.attributeList, 'vsType')

## Get the kind attribute
#
# @return The value of vsKind, or None if that attribute is not defined
#
  def getKind(self):
    return self.vsw.attribute(self.attributeList, 'vsKind')

## Get the lower bounds attribute
#
# @return The value of vsLowerBounds, or None if that attribute is not defined
#
  def getLowerBounds(self):
    vsKind: str = self.getKind()
    lb = None
    if vsKind == 'uniform' or vsKind == 'Cartesian':
      lb = self.vsw.attribute(self.attributeList, 'vsLowerBounds')
# For rectilinear, there is no vsLowerBounds attribute
    elif vsKind == 'rectilinear':
      lb0 = self.axis0.dataset[0]
      lb1 = self.axis1.dataset[0] if len(self.axis1.dataset) != 0 else None
      lb2 = self.axis2.dataset[0] if len(self.axis2.dataset) != 0 else None
# Will convert to nan if None
      lb = numpy.array([lb0, lb1, lb2], dtype='double')
      lb = lb[~numpy.isnan(lb)]
    else:
      debug(f'[getLowerBounds] getLowerBounds() is not implemented for vsKind={vsKind}')
    return lb

## Get the upper bounds attribute
#
# @return The value of vsUpperBounds, or None if that attribute is not defined
#
  def getUpperBounds(self):
    vsKind: str = self.getKind()
    ub = None
    if vsKind == 'uniform' or vsKind == 'Cartesian':
      ub = self.vsw.attribute(self.attributeList, 'vsUpperBounds')
    elif vsKind == 'rectilinear':
      ub0 = self.axis0.dataset[-1]
      ub1 = self.axis1.dataset[-1] if len(self.axis1.dataset) != 0 else None
      ub2 = self.axis2.dataset[-1] if len(self.axis2.dataset) != 0 else None
# Will convert to nan if None
      ub = numpy.array([ub0, ub1, ub2], dtype='double')
      ub = ub[~numpy.isnan(ub)]
    else:
      debug(f'[getUpperBounds] getUpperBounds() is not implemented for vsKind={vsKind}')
    return ub

## Get the number of cells attribute
#
# @return The value of vsNumCells, or None if that attribute is not defined
#
  def getNumCells(self):
    vsKind: str = self.getKind()
    nc = None
    if vsKind == 'uniform' or vsKind == 'Cartesian':
      nc = self.vsw.attribute(self.attributeList, 'vsNumCells')
    elif vsKind == 'rectilinear':
      nc0 = len(self.axis0.dataset)
      nc1 = len(self.axis1.dataset)
      nc2 = len(self.axis2.dataset)
# Will convert to nan if None
      if nc1 == 0:
        nc = numpy.array([nc0], dtype='int')
      elif nc2 == 0:
        nc = numpy.array([nc0, nc1], dtype='int') 
      else:
        nc = numpy.array([nc0, nc1, nc2], dtype='int')
    else:
      debug(f'[getNumCells] getNumCells() is not implemented for vsKind={vsKind}')
    return nc

## Get the starting cell attribute, usually [0,0,0], but not always
#
# @return The value of vsStartCell, or None if that attribute is not defined
#
  def getStartCell(self):
    return self.vsw.attribute(self.attributeList, 'vsStartCell')

## Get the centering attribute
#
# @return The value of vsCentering, or None if that attribute is not defined
#
  def getCentering(self):
    return self.vsw.attribute(self.attributeList, 'vsCentering')

## Get the dump time
#
# @return The value of the time attribute, or None if that attribute is not defined
#
  def getDumpTime(self):
    return self.vsw.attribute(self.attributeList, 'time')

## Write an external link to a file
#
# @param fileName name of the file in which to create the link
# @param name name of the link to create in fileName
# @param targetFileName name of the target file for the link
# @param targetObjectName name of the target group or dataset for the link
# @param location file location to which the link is written
#
#
  def writeExternalLink(self, fileName, name, targetFileName, targetObjectName, location='/'):
    if not isinstance(targetFileName, six.string_types):
      debug('[VsBase:writeExternalLink] Target file name: ' + str(targetFileName) + ' is not valid. Please specify a full or relative pathname. Not writing external link.')
      return
    if not isinstance(targetObjectName, six.string_types) or targetObjectName[0] != '/':
      debug('[VsBase:writeExternalLink] Target object name: ' + str(targetObjectName) + ' is not valid. Please specify a string representing the full Hdf5 path to the target dataset or group, starting with a "/". Not writing external link.')
      return
    target = targetFileName + ':' + targetObjectName

    try:
      #debug('[VsBase:writeExternalLink] Trying to create external link in file: ' + fileName + ' named: ' + name + ' pointing to target: ' + target)
      #print(location,name,target)
      self.vsw.writeExternalLink(fileName, name, target, location)
      debug('[VsBase:writeExternalLink] Success.')
    except:
      #debug('[VsBase:writeExternalLink] Could not create external link in file: ' + fileName + ' named: ' + name + ' pointing to target: ' + target)
      pass

## Quietly try to remove pytables-generated attributes
#
#  @param fileName the name of the file in which to remove the attributes
#
  def removePyTablesAttributes(self,fileName):
    try:
      self.vsw.open_file(fileName,'a') # in append mode since we are writing
      for n in self.vsw.fh.walk_nodes('/'):
        try:
          n._f_delattr('TITLE')
        except:
          pass
        try:
          n._f_delattr('VERSION')
        except:
          pass
        try:
          n._f_delattr('FLAVOR')
        except:
          pass
        try:
          n._f_delattr('CLASS')
        except:
          pass
        try:
          n._f_delattr('PYTABLES_FORMAT_VERSION')
        except:
          pass
      self.vsw.closeFile()
    except:
      pass

class VsDatasetBase(VsBase):
  """ Base class that defines an object that contains a dataset and attributes. Other higher-lever classes such as fields and particles should derive from this class."""

## constructor
#
# @param self object pointer
#
  def __init__(self, name, vsType=None, VsHdf5=VsHdf5()):
    self.name = name
    self.attributeList = []
    self.vsType = vsType;
    self.vsw = VsHdf5
    self.dataset = numpy.zeros(0)

## Overload operator to return slices of the underlying dataset
#
# @param key The slice to return from the dataset
#
  def __getitem__(self, key):
    return self.dataset[key]

## Return the length of the underlying dataset
#
# @param key The slice to return from the dataset
#
  def __len__(self):
    return len(self.dataset)

## Read a dataset. Assign the dataset and attributes internally.
#
# @param fileName name of the file that the dataset is in
# @param name name of the dataset
# @param location location of the dataset to be read. Default location is root group.
#
  def readDataset(self, fileName, name, location=None):
    if name is None:
      debug('[vsDatasetBase.readDataset()] Dataset name is "None". Nothing read from file.')
      return numpy.zeros(0), None
    if location is None:
      location = '/'
    location = location.replace('//','/')
    self.vsw.open_file(fileName) # in read only mode
    if self.vsw.fh:
      debug('[readDataset] Trying to read dataset: ' + str(name) + ' to location: ' + location + ' in file: ' + fileName)
      array, attributeList = self.vsw.readDataset(location, name)
      debug('[readDataset] success.')
      debug('[readDataset] Assigning internal dataset to array.')
      try:
        self.dataset = array
        debug('[readDataset] success.')
      except:
        debug('[readDataset] Could\'t assign dataset.')
        pass
      debug('[readDataset] Assigning internal attributes to read attributes, if any.')
      try:
        sattList = []
        for satt in self.attributeList:
          sattList.append(satt[0])
        for att in attributeList:
          if att[0] in sattList:
            self.vsw.removeAttribute(self.attributeList, att[0])
          self.vsw.assignAttribute(self.attributeList, att[0], att[1])
        debug('[readDataset] success.')
      except:
        debug('[readDataset] Couldn\'t assign attributes. Continuing.')
        pass
      self.vsw.closeFile()
    else:
      print(f'[readDataset] Couldn\'t open the file: {fileName}', file=sys.stderr)
      array = numpy.empty(0)
      attributeList = []
    return array, attributeList

## Read a dataset from a file and copy all of the attributes.
## Searches for the dataset by attribute/value pair.
#
# @param fileName name of the file that the group is to be copied from
# @param attributeName name of the attribute to search for
# @param attributeValue value of the attribute to check for
#
  def readDatasetByAttribute(self, fileName, attributeName, attributeValue):
    self.vsw.open_file(fileName) # in read only mode
    if self.vsw.fh is None:
      print(f'[readDatasetByAttribute] Couldn\'t open file: {fileName}', file=sys.stderr)
    else:
      gh = self.vsw.findObject(attributeName, attributeValue)
      if gh:
        debug('[readDatasetByAttribute] Found a dataset with attribute: ' + str(attributeName) + ' with value: ' + str(attributeValue))
        # set name of the object from the group just read
        datasetName = gh._v_name
        datasetPathName = gh._v_pathname
      else:
        debug('[readDatasetByAttribute] Could not find a dataset with attribute: ' + str(attributeName) + ' with value: ' + str(attributeValue))
      self.vsw.closeFile()
      self.readDataset(fileName, datasetPathName, location='/')

## Write a dataset to a file, with attributes attached
#
# @param fileName name of the file that the field is to be written to
# @param location where the dataset will be located in the file
# @param datasetName name of the dataset in the file
# @param dataset [optional] The numpy array to write. Default behavior is to write self.dataset
# @param extendable False if dataset to be written should be extendable, e.g. Histories
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeDataset(self,
                   fileName,
                   location,
                   datasetName,
                   dataset=None,
                   extendable=False,
                   indexOrder='compMinorC',
                   overwrite=False):
    pathname = location + datasetName
    pathname = pathname.replace('//','/')
    if dataset is None:
      dataset = self.dataset
    self.vsw.open_file(fileName,'a') # in append mode since we are writing
    if indexOrder == 'compMajorC':
      debug(f'[writeDataset] Transposing dataset: {datasetName} with shape: {dataset.shape} to "compMajorC" ordering.')
      try:
        _dataset = numpy.transpose(dataset, [-1]+list(range(dataset.ndim-1)))
        debug(f'[writeDataset] Success. New shape: {dataset.shape}')
        dataset = _dataset
        self.assignAttribute('vsIndexOrder', 'compMajorC')
      except:
        debug(f'[writeDataset] Could not transpose the dataset. Writing as "compMinorC".')
        self.assignAttribute('vsIndexOrder', 'compMinorC')
    if self.vsw.fh:
      debug(f'[writeDataset] Trying to write dataset: {datasetName} to file: {fileName}')
      self.vsw.writeDataset(location,
                            datasetName,
                            dataset,
                            extendable=extendable,
                            overwrite=overwrite)
      debug('[writeDataset] success.')
      debug('[writeDataset] Trying to write attributes to the dataset')
      for att in self.attributeList:
        self.vsw.writeAttribute(pathname, att[0], att[1])
      debug('[writeDataset] success.')
    else:
      print('[writeDataset] Could not get handle to file for writing. Dataset not written.', file=sys.stderr)
    self.vsw.closeFile()
    self.removePyTablesAttributes(fileName)

## Assign a dataset to an object, such as a field
#
# @param array numpy array to set internally
#
  def assignDataset(self, array):
    try:
      debug('[assignDataset] Trying to set dataset.')
      self.dataset = array
      debug('[assignDataset] success.')
    except:
      print('[assignDataset] Could not assign dataset to this object.', file=sys.stderr)

class VsGroupBase(VsBase):
  """ Base class that defines an object that contains a group and attributes. Other higher-lever classes that correspond to groups in Hdf5 such as meshes, timeGroups, and runInfo should derive from this class."""

## constructor
#
# @param self object pointer
#
  def __init__(self, name, vsType=None, VsHdf5=VsHdf5()):
    self.name = name
    self.attributeList = []
    self.vsType = vsType;
    self.vsw = VsHdf5

## Read a group from a file and copy all of the attributes
#
# @param fileName name of the file that the group is to be copied from
# @param location where the group is located in the file
# @param groupName name of the group in the file
#
  def readGroup(self, fileName, location, groupName):
    if location is None: location = '/'
    if groupName is None:
      debug('[VsGroupBase:readGroup] Group Name is None. Aborting mission.')
      return
    pathname = location + '/' + groupName
    pathname = pathname.replace('//','/')
    self.vsw.open_file(fileName) # in read only mode
    debug('[readGroup] Trying to read group: ' + pathname + ' in file: ' + fileName)
    nh = self.getNodeHandle(pathname)
    if nh != None:
# If it is an external link, read the group from the external file
#      gh = self.vsw.getExternalLinkHandle(nh)
#      if gh is None:
#        gh = self.vsw.openGroup(location, groupName)
      for name in nh._v_attrs._f_list('user'):
        attr = nh._v_attrs[name]
        if type(attr) is numpy.bytes_:  attr = attr.decode('UTF-8')
        self.assignAttribute(name, attr)
      debug('[readGroup] success.')
    else:
      debug('[readGroup] Could not read group: ' + pathname + ' in file: ' + fileName)
    self.vsw.closeFile()

## Read a group from a file and copy all of the attributes. Searches for the group by attribute/value pair.
#
# @param fileName name of the file that the group is to be copied from
# @param attributeName name of the attribute to search for
# @param attributeValue value of the attribute to check for
#
  def readGroupByAttribute(self, fileName, attributeName, attributeValue):
    self.vsw.open_file(fileName) # in read only mode
    if self.vsw.fh is None:
      debug('[readGroupByAttribute] Could not open file: ' + str(fileName) + '. Could be missing?')
    else:
      gh = self.vsw.findObject(attributeName, attributeValue)
    #  tp = self.vsw.getExternalLinkHandle(gh)
    #  if tp != None: gh = tp

      if gh:
        debug('[readGroupByAttribute] Found a group with attribute: ' + str(attributeName) + ' with value: ' + str(attributeValue))
        # set name of the object from the group just read
        self.name = gh._v_name
        for name in gh._v_attrs._f_list('user'):
          attr = gh._v_attrs[name]
          if type(attr) is numpy.bytes_:  attr = attr.decode('UTF-8')
          self.assignAttribute(name, attr)
      else:
        debug('[readGroupByAttribute] Could not find a group with attribute: ' + str(attributeName) + ' with value: ' + str(attributeValue))
    self.vsw.closeFile()

## Write a group group to a file
#
# @param fileName name of the file that the group is to be written to
# @param location where the group will be located in the file
# @param groupName name of the group in the file
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeGroup(self, fileName, location, groupName, overwrite=False):
    pathname = location + groupName
    pathname = pathname.replace('//','/')
    self.vsw.open_file(fileName,'a') # in append mode since we are writing
    if self.vsw.fh:
      if overwrite:
        try:
          debug('[writeGroup] Trying to delete group: ' + location + groupName)
          self.vsw.deleteGroup(groupName, location=location)
        except:
          pass
      gh = self.vsw.create_group(location, groupName)
      if gh:
        debug('[writeGroup] Trying to write group to a file')
        for att in self.attributeList:
          self.vsw.writeAttribute(pathname, att[0], att[1])
        debug('[writeGroup] success.')

      else:
        print(f'[writeGroup] Could not create new group: {groupName} to location: {location}. Group not written.', file=sys.stderr)
      self.vsw.closeFile()
      self.removePyTablesAttributes(fileName)
    else:
      print(f'[writeGroup] Could not open file: {fileName} for writing.  Group not written.', file=sys.stderr)

class Mesh(VsBase):
  r""" Class that defines a generic mesh object.  Group and Dataset meshes derived from this class.
  """

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
# @param location where the dataset is located in the file. Defaults to None.
# @param vsType The type of dataset. Should always be "mesh".
#
  def __init__(self, name=None, fileName=None, location=None, vsType='mesh', VsHdf5=VsHdf5()):
    self.name = name
    self.attributeList = []
    self.vsType = vsType;
    self.vsw = VsHdf5
    global meshName
    meshName = self.name
    self.assignAttribute('vsType', 'mesh')
    if fileName != None:
      self.readMesh(fileName, meshName=name, location=location)

## Read a mesh from a file and copy all of the attributes. Overloaded method.
#
# @param fileName name of the file that the mesh is to be copied from
# @param location where the mesh group is located in the file
# @param meshName name of the mesh in the file
#
  def readMesh(self, fileName, location=None, meshName=None):
    self.vsw.open_file(fileName) # in read only mode
    if self.vsw.fh:
      if meshName is None:
        debug('[Mesh.readMesh()] Determining which object is the mesh.')
        nh = self.vsw.findObject('vsType', 'mesh')
      else:
        if location is None: location = '/'
        debug('[Mesh.readMesh()] Trying to open mesh named: ' + str(meshName) + ' to location: ' + str(location) + '.')
        nh = self.vsw.getNodeHandle(location+meshName)
      if nh:
        debug('[Mesh.readMesh] Found a object named: ' + nh._v_name + ' with attribute: "vsType" with value: "mesh".')
# get the mesh kind
        vsKind = nh._v_attrs['vsKind']
        if type(vsKind) is numpy.bytes_:  vsKind = vsKind.decode('UTF-8')

# must close file before calling __init__
        self.vsw.closeFile()

        if vsKind is None:
          debug('[Mesh.readMesh] Could not determine the kind of mesh for mesh named: ' + str(nh._v_name))

# otherwise cast to the correct kind of mesh
        else:
          if vsKind == 'uniform':
            debug('[Mesh.readMesh] Casting to UniformCartesianMesh...')
            self.__class__ = UniformCartesianMesh
            self.__init__(fileName=fileName, name=meshName, location=location)
          elif vsKind == 'rectilinear':
            debug('[Mesh.readMesh] Casting to RectilinearMesh...')
            self.__class__ = RectilinearMesh
            self.__init__(fileName=fileName, name=meshName, location=location)
          elif vsKind == 'structured':
            debug('[Mesh.readMesh] Casting to StructuredMesh...')
            self.__class__ = StructuredMesh
            self.__init__(fileName=fileName, name=meshName, location=location)
          elif vsKind == 'unstructured':
            debug('[Mesh.readMesh] Casting to UnstructuredMesh...')
            self.__class__ = UnstructuredMesh
            self.__init__(fileName=fileName, name=meshName, location=location)
          else:
            debug('[Mesh.readMesh] Mesh kind: ' + str(vsKind) + ' is not currently implemented.')
      else:
        self.vsw.closeFile()
        debug('[Mesh.readMesh] Could not find a group with attribute: "vsType" with value: "mesh" in file ' + str(fileName) + '.')
    else:
        print(f'[Mesh.readMesh] Could not open file: {fileName}', file=sys.stderr)

class GroupMesh(Mesh, VsGroupBase):
  r""" Class that defines a mesh object that is a group in the Hdf5 instance. Has methods for reading/writing to/from a file. Group meshes contain attributes and possibly datasets (like rectilinear meshes), and some of the attributes may be arrays. Specific kinds of meshes that are groups should inherit from this class. Is a group in the Hdf5 instance. """

## constructor
#
# @param name The name of this object
# @param vsType The type of dataset. Defaults to "mesh".
#
  def __init__(self, name=None, vsType='mesh', VsHdf5=VsHdf5()):
# Call VsGroupBase constructor first
    VsGroupBase.__init__(self, name, vsType, VsHdf5)
    global meshName
    meshName = self.name
    self.assignAttribute('vsType', 'mesh')

## Read a mesh from a file and copy all of the attributes. Overloaded method.
#
# @param fileName name of the file that the mesh is to be copied from
# @param location where the mesh group is located in the file
# @param meshName name of the mesh in the file
#
  def readMesh(self, fileName, location=None, meshName=None):
    if location is None: location = '/'
    if meshName is None:
      debug('[GroupMesh.readMesh()] Reading Mesh group. Determining which group by attributes.')
      self.readGroupByAttribute(fileName, 'vsType', 'mesh')
    else:
      debug('[GroupMesh.readMesh()] Reading Mesh group: ' + location + str(meshName))
      self.readGroup(fileName, location, meshName)

## Write a mesh group to a file
#
# @param fileName name of the file that the mesh is to be written to
# @param location where the mesh group will be located in the file. Default is root group.
# @param meshName name of the mesh in the file. Default is object name.
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeMesh(self, fileName, location='/', meshName=None, overwrite=False):
    if meshName is None:
      meshName = self.name
# default
    if meshName is None:
      meshName = 'mesh'
    debug('[GroupMesh.writeMesh] Writing mesh group: ' + location + meshName)
    self.writeGroup(fileName, location, meshName, overwrite=overwrite)

class DatasetMesh(Mesh, VsDatasetBase):
  r""" Class that defines a mesh object that is a dataset in the Hdf5 instance. Has methods for reading/writing to/from a file. Dataset meshes are a dataset in the Hdf5 instance and contain attributes. Specific kinds of meshes that are datasets should inherit from this class, like structured meshes. Is a dataset in the Hdf5 instance. """

## constructor
#
# @param name The name of this object
# @param vsType The type of object. Should always be "mesh".
#
  def __init__(self, name=None, vsType='mesh', VsHdf5=VsHdf5()):
# Call VsDatasetBase constructor first
    VsDatasetBase.__init__(self, name, vsType, VsHdf5)
    global meshName
    meshName = self.name
    self.assignAttribute('vsType', 'mesh')

## Read a mesh from a file and copy all of the attributes. Overloaded method.
#
# @param fileName name of the file that the mesh is to be copied from
# @param location where the mesh group is located in the file
# @param meshName name of the mesh in the file
#
  def readMesh(self, fileName, location=None, meshName=None):
    if location is None: location = '/'
    if meshName is None:
      debug('[DatasetMesh.readMesh()] Reading Mesh dataset. Determining which dataset by attributes.')
    else:
      debug('[DatasetMesh.readMesh()] Reading Mesh dataset: ' + location + str(meshName))
      self.readDataset(fileName, meshName, location=location)

## Write a mesh dataset to a file
#
# @param fileName name of the file that the mesh is to be written to
# @param location where the mesh group will be located in the file. Default is root group.
# @param meshName name of the mesh in the file. Default is object name, then "mesh".
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeMesh(self, fileName, location='/', meshName=None, overwrite=False):
    if meshName is None:
      meshName = self.name
# default
    if meshName is None:
      meshName = 'mesh'
    debug('[DatasetMesh.writeMesh] Writing mesh dataset: ' + location + meshName)
    self.writeDataset(fileName, location, meshName, overwrite=overwrite)

class StructuredMesh(DatasetMesh):
  r""" Class that defines a structured mesh object, such as for specifying each vertex of a mesh, but with fixed connectivity. Is a specific type of mesh that is a dataset with dimensionality that is typically one greater than the spatial dimensionality of the mesh. For instance a 3-Dimensional Cartesian structured mesh would have dimensionality [Nx,Ny,Nz,3] where [:,:,:,0] is the X-coordinate, [:,:,:,1] is the Y-coordinate, etc.
Optional attributes are:
indexOrder: Data ordering. Default is "compMinorC". Other options are "compMinorF", "compMajorC", or "compMajorF".
limitsName: Name of a limits object associated with this mesh
temporalDimension: unsigned integer which axis is time
Derives from DatasetMesh class. Is a dataset in the Hdf5 instance. """

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
# @param location where the dataset is located in the file. Defaults to None.
# @param vsType The type of object. Should always be "mesh".
#
  def __init__(self, name=None, fileName=None, location=None, vsType='mesh', VsHdf5=VsHdf5()):
# Call DatasetMesh constructor first
    DatasetMesh.__init__(self, name, vsType, VsHdf5)
    global meshName
    meshName = self.name
    self.assignAttribute('vsType', 'mesh')
    self.assignAttribute('vsKind', 'structured')
    if fileName != None:
      self.readMesh(fileName, location=location, meshName=name)

## Read a mesh from a file and copy all of the attributes. Overloaded method.
##  Structured Meshes are a dataset instance in Hdf5, with attributes in the dataset.
#
# @param fileName name of the file that the mesh is to be copied from
# @param location where the mesh group is located in the file
# @param meshName name of the mesh in the file
#
  def readMesh(self, fileName, location=None, meshName=None):
    if location is None: location = '/'
    DatasetMesh.readMesh(self, fileName, location, meshName)
    if self.attribute('vsType') != 'mesh' or self.attribute('vsKind') != 'structured':
      print(f'[StructuredMesh.readMesh()] Mesh: {location}{meshName} is NOT a structured mesh.', end='')
      print(f' It is of kind: {self.attribute("vsKind")}. Please create the proper type of mesh.', file=sys.stderr)

## Write a structured mesh to a file
#
# @param fileName name of the file that the mesh is to be written to
# @param location where the mesh dataset will be located in the file. Default is root group.
# @param meshName name of the mesh in the file. Default is object name.
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeMesh(self, fileName, location='/', meshName=None, data=None, indexOrder=None, limitsName=None, temporalDimension=None, overwrite=False):
    if meshName is None:
      meshName = self.name
# default
    if meshName is None:
      meshName = 'mesh'
# axis variables are datasets
    if data is not None:
      self.assignDataset(data)
# overwrite existing attributes with passed, if they are passed
    self.assignAttribute('vsIndexOrder', indexOrder)
    self.assignAttribute('vsLimits', limitsName)
    self.assignAttribute('vsTemporalDimension', temporalDimension)

    em1 = '[StructuredMesh.writeMesh()] Structured Meshes require that the dataset: '
# validate that the dataset is there.
    if self.dataset is None:
      print(em1, file=sys.stderr)
      print(f'[StructuredMesh.writeMesh()] Dataset is None. Mesh not written: {location}{meshName}', file=sys.stderr)
    elif len(self.dataset) == 0:
      print(em1, file=sys.stderr)
      print(f'[StructuredMesh.writeMesh()] Length of dataset is zero. Mesh not written: {location}{meshName}', file=sys.stderr)
    else:
      debug('[StructuredMesh.writeMesh()] Writing structured mesh dataset: ' + location + str(meshName))
      self.writeDataset(fileName, location, meshName, overwrite=overwrite)

class UnstructuredMesh(GroupMesh, VsDatasetBase):
  r""" Class that defines an unstructured mesh object, such as for specifying each vertex of a mesh, and the connectivity. Is a specific type of mesh that is a group, that contains a dataset specifying the vertexes (points), and a dataset containing the connectivity information (e.g. polygons). The name of these datasets is specifed by attributes 'vsPoints' and [vsConnectivity] where vsConnectivity is either 'vsEdges', 'vsFaces', 'vsPolygons', or 'vsQuadrilaterals'. Only one of the connectivity datasets is required.
Optional attributes are:
indexOrder: Data ordering. Default is "compMinorC". Other options are "compMinorF", "compMajorC", or "compMajorF".
limitsName: Name of a limits object associated with this mesh
Derives from GroupMesh class. Is a group in the Hdf5 instance. """

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
# @param location where the dataset is located in the file. Defaults to None.
# @param vsType The type of object. Should always be "mesh".
#
  def __init__(self, name=None, fileName=None, location=None, vsType='mesh', VsHdf5=VsHdf5()):
# Call DatasetMesh constructor first
    GroupMesh.__init__(self, name, vsType, VsHdf5)
    global meshName
    meshName = self.name
    self.assignAttribute('vsType', 'mesh')
    self.assignAttribute('vsKind', 'unstructured')
    self.points = Dataset()
    self.edges = Dataset()
    self.faces = Dataset()
    self.polygons = Dataset()
    self.quads = Dataset()
    if fileName != None:
      self.readMesh(fileName, meshName=name, location=location)

## Read a mesh from a file and copy all of the attributes. Overloaded method.
#  Structured Meshes are a dataset instance in Hdf5, with attributes in the dataset.
#
# @param fileName name of the file that the mesh is to be copied from
# @param location where the mesh group is located in the file
# @param meshName name of the mesh in the file
#
  def readMesh(self, fileName, location=None, meshName=None):
    if location is None: location = '/'
    GroupMesh.readMesh(self, fileName, location, meshName)
    if self.attribute('vsType') == 'mesh' or self.attribute('vsKind') == 'unstructured':
      pointsData, self.pointsDataAttrs = VsDatasetBase.readDataset(self, fileName, self.attribute('vsPoints'), location=location+'/'+self.name,)
      self.points.assignDataset(pointsData)
      edgesData, self.edgesDataAttrs = VsDatasetBase.readDataset(self, fileName, self.attribute('vsEdges'), location=location+'/'+self.name,)
      self.edges.assignDataset(edgesData)
      facesData, self.facesDataAttrs = VsDatasetBase.readDataset(self, fileName, self.attribute('vsFaces'), location=location+'/'+self.name,)
      self.faces.assignDataset(facesData)
      polygonsData, self.polygonsDataAttrs = VsDatasetBase.readDataset(self, fileName, self.attribute('vsPolygons'), location=location+'/'+self.name,)
      self.polygons.assignDataset(polygonsData)
      quadsData, self.quadsDataAttrs = VsDatasetBase.readDataset(self, fileName, self.attribute('vsQuadrilaterals'), location=location+'/'+self.name,)
      self.quads.assignDataset(quadsData)
    else:
      print(f'[UnstructuredMesh.readMesh()] Mesh: {location}{meshName}is NOT an unstructured mesh. ', end='')
      print(f'It is of kind: {self.attribute("vsKind")}. Please create the proper type of mesh.', file=sys.stderr)

## Write an unstructured mesh group to a file
#
# @param fileName name of the file that the mesh is to be written to
# @param location where the mesh group will be located in the file. Default is root group.
# @param meshName name of the mesh in the file. Default is object name.
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeMesh(self, fileName, location='/', meshName=None, pointsData=None, edgesData=None, facesData=None, polygonsData=None, quadsData=None, pointsName=None, edgesName=None, facesName=None, polygonsName=None, quadsName=None, indexOrder=None, limitsName=None, overwrite=False):
    if meshName is None:
      meshName = self.name
# default
    if meshName is None:
      meshName = 'mesh'
# points, edges, faces, and polygons variables are datasets
    if pointsData is not None:
      self.points.assignDataset(pointsData)
    if edgesData is not None:
      self.edges.assignDataset(edgesData)
    if facesData is not None:
      self.faces.assignDataset(facesData)
    if polygonsData is not None:
      self.polygons.assignDataset(polygonsData)
    if quadsData is not None:
      self.quads.assignDataset(quadsData)
# overwrite existing attributes with passed, if they are passed
    self.assignAttribute('vsPoints', pointsName)
    self.assignAttribute('vsEdges', edgesName)
    self.assignAttribute('vsFaces', facesName)
    self.assignAttribute('vsPolygons', polygonsName)
    self.assignAttribute('vsQuadrilaterals', quadsName)
    self.assignAttribute('vsIndexOrder', indexOrder)
    self.assignAttribute('vsLimits', limitsName)

# validate that the required attributes are there and set defaults
    em1 = '[UnstructuredMesh.writeMesh()] Unstructured Meshes require that the dataset: '
    em2 = ' be defined. Please call this method with: mesh.writeMesh(fileName, ..., '
    em4 = '[UnstructuredMesh.writeMesh()] '

    if self.attribute('vsPoints') is None:
      self.assignAttribute('vsPoints', 'points')
      debug(em4 + ' Using the default value of "points" for the attribute vsPoints.')
      debug('To override this default, please call this method with: mesh.writeMesh(fileName, ..., pointsName=pointsName)')

    if self.attribute('vsIndexOrder') is None:
      self.assignAttribute('vsIndexOrder', 'compMinorC')
      debug(em4 + ' Using the default value of "compMinorC" for the attribute vsIndexOrder.')
      debug('To override this default, please call this method with: mesh.writeMesh(fileName, ..., indexOrder=indexOrder)')

# need one of edges, faces, polygons, or quadrilaterals
    if len(self.edges.dataset) == 0 and \
       len(self.faces.dataset) == 0 and \
       len(self.polygons.dataset) == 0 and \
       len(self.quads.dataset) == 0:
      debug(em1 + 'edges or faces or polygons or quads' + em2 + 'edgesData=edgesData of facesData=facesData or polygonsData=polygonsData or quadsData=quadsData)')
      debug('[UnstructuredMesh.writeMesh()] Mesh not written: ' + location + str(meshName))
# lines, triangles, tetrahedrals, pyramids, wedges, and hexahedrals not implemented here
    if len(self.edges.dataset) != 0 and self.attribute('vsEdges') is None:
      self.assignAttribute('vsEdges', 'edges')
      debug(em4 + ' Using the default value of "edges" for the attribute vsEdges.')
      debug('To override this default, please call this method with: mesh.writeMesh(fileName, ..., quadsName=quadsName)')

    if len(self.faces.dataset) != 0 and self.attribute('vsFaces') is None:
      self.assignAttribute('vsFaces', 'faces')
      debug(em4 + ' Using the default value of "faces" for the attribute vsFaces.')
      debug('To override this default, please call this method with: mesh.writeMesh(fileName, ..., quadsName=quadsName)')

    if len(self.polygons.dataset) != 0 and self.attribute('vsPolygons') is None:
      self.assignAttribute('vsPolygons', 'polygons')
      debug(em4 + ' Using the default value of "polygons" for the attribute vsPolygons.')
      debug('To override this default, please call this method with: mesh.writeMesh(fileName, ..., quadsName=quadsName)')

    if len(self.quads.dataset) != 0 and self.attribute('vsQuadrilaterals') is None:
      self.assignAttribute('vsQuadrilaterals', 'cells')
      debug(em4 + ' Using the default value of "cells" for the attribute vsQuadrilaterals.')
      debug('To override this default, please call this method with: mesh.writeMesh(fileName, ..., quadsName=quadsName)')

# datasets
    if len(self.points.dataset) == 0:
      debug(em1 + 'points' + em2 + 'pointsData=pointsData)', file=sys.stderr)
      debug('[UnstructuredMesh.writeMesh()] Mesh not written: ' + location + str(meshName), file=sys.stderr)
    if pointsName is None and self.attribute('vsPoints') is None:
      self.assignAttribute('vsPoints', 'points')
      debug(em4 + ' Using the default value of "points" for the attribute pointsName.')
      debug('To override this default, please call this method with: mesh.writeMesh(fileName, ..., pointsName=pointsName)')
    debug('[UnstructuredMesh.writeMesh()] Writing unstructured mesh group: ' + location + str(meshName))
# writeGroup creates the group and writes attributes
    GroupMesh.writeMesh(self, fileName, location=location, meshName=meshName, overwrite=overwrite)
# now write the datasets
    self.points.writeDataset(fileName, location+meshName+'/', self.attribute('vsPoints'), overwrite=overwrite)
    if self.attribute('vsEdges') != None:
      self.edges.writeDataset(fileName, location+meshName+'/', self.attribute('vsEdges'), overwrite=overwrite)
    if self.attribute('vsFaces') != None:
      self.faces.writeDataset(fileName, location+meshName+'/', self.attribute('vsFaces'), overwrite=overwrite)
    if self.attribute('vsPolygons') != None:
      self.polygons.writeDataset(fileName, location+meshName+'/', self.attribute('vsPolygons'), overwrite=overwrite)
    if self.attribute('vsQuadrilaterals') != None:
      self.quads.writeDataset(fileName, location+meshName+'/', self.attribute('vsQuadrilaterals'), overwrite=overwrite)

class UniformCartesianMesh(GroupMesh):
  r""" Class that defines a uniform Cartesian mesh object. Is a specific type of mesh with required attributes for lower and upper bounds, number of cells, and the starting cell indexes. Derives from GroupMesh class. Is a group in the Hdf5 instance. """

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
# @param location where the dataset is located in the file. Defaults to None.
# @param vsType The type of dataset. Defaults to "mesh".
#
  def __init__(self, name=None, fileName=None, location=None, vsType='mesh', VsHdf5=VsHdf5()):
# Call Mesh constructor first
    GroupMesh.__init__(self, name, vsType, VsHdf5)
    global meshName
    meshName = self.name
    self.assignAttribute('vsType', 'mesh')
    self.assignAttribute('vsKind', 'uniform')
    if fileName != None:
      self.readMesh(fileName, meshName=name, location=location)
# validate that is is indeed a uniform Cartesian mesh
    if self.attribute('vsType') != 'mesh' or self.attribute('vsKind') != 'uniform':
      print(f'[UniformCartesianMesh.writeMesh()] Mesh: {location}{meshName} is NOT a uniform Cartesian mesh. ', end='')
      print(f'It is of kind: {self.attribute("vsKind")}. Please create the proper type of mesh.', file=sys.stderr)

## Write a uniform Cartesian mesh group to a file
#
# @param fileName name of the file that the mesh is to be written to
# @param location where the mesh group will be located in the file. Default is root group.
# @param meshName name of the mesh in the file. Default is object name.
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeMesh(self, fileName, location='/', meshName=None, lowerBounds=None, upperBounds=None, numCells=None, startCell=None, overwrite=False):
    if meshName is None:
      meshName = self.name
# default
    if meshName is None:
      meshName = 'mesh'
# overwrite existing attributes with passed values, if they are passed.
# If they are None, will not be overridden.
    self.assignAttribute('vsLowerBounds', lowerBounds)
    self.assignAttribute('vsUpperBounds', upperBounds)
    self.assignAttribute('vsNumCells', numCells)
    self.assignAttribute('vsStartCell', startCell)

# validate that the required attributes are there
    em1 = '[UniformCartesianMesh.writeMesh()] Uniform Cartesian Meshes require that the attribute: '
    em2 = ' be defined. Please call this method with: mesh.writeMesh(fileName, ..., '
    if startCell is None and self.getStartCell() is None:
      self.assignAttribute('vsStartCell', numpy.zeros(3,dtype='int'))
      print(em1 + 'startCell' + ' be defined. Using the default value of [0, 0, 0].')
      print('To override this default, please call this method with: mesh.writeMesh(fileName, ..., startCell=startCell).')
    debug('[UniformCartesianMesh.writeMesh()] Writing uniform Cartesian mesh group: ' + location + str(meshName))
    GroupMesh.writeMesh(self, fileName, location=location, meshName=meshName, overwrite=overwrite)

class RectilinearMesh(GroupMesh, VsDatasetBase):
  r""" Class that defines a rectilinear mesh object, such as in cylindrical coordinates. Is a specific type of mesh with required dataset attributes describing the values of the axes, with one 1-Dimensional dataset per axis. Optional attributes are:
axis0Name, axis1Name, axis2Name: the name of the axes (default = "axis0", "axis1", "axis2")
limitsName: Name of a limits object associated with this mesh
temporalDimension: unsigned integer which axis is time
Derives from GroupMesh class. Is a group in the Hdf5 instance. """

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
# @param location where the dataset is located in the file. Defaults to None.
# @param vsType The type of dataset. Defaults to "mesh".
#
  def __init__(self, name=None, fileName=None, location=None, vsType='mesh', VsHdf5=VsHdf5()):
# Call GroupMesh constructor first
    GroupMesh.__init__(self, name, vsType, VsHdf5)
    global meshName
    meshName = self.name
    self.assignAttribute('vsType', 'mesh')
    self.assignAttribute('vsKind', 'rectilinear')
    self.axis0 = Dataset()
    self.axis1 = Dataset()
    self.axis2 = Dataset()
    if fileName != None:
      self.readMesh(fileName, meshName=name, location=location)

## Read a mesh from a file and copy all of the attributes. Overloaded method.
## Rectilinear Meshes are a group instance in Hdf5, with attributes and datasets
#
# @param fileName name of the file that the mesh is to be copied from
# @param location where the mesh group is located in the file
# @param meshName name of the mesh in the file
#
  def readMesh(self, fileName, location=None, meshName=None):
    if location is None: location = '/'
    GroupMesh.readMesh(self, fileName, location, meshName)
# validate that this is indeed a rectilinear mesh
    if self.attribute('vsType') == 'mesh' and self.attribute('vsKind') == 'rectilinear':
# for now only cylindrical z, r, phi is supported. This will need to be generalized for USim, eg.
# readDataset will return empty numpy array if the dataset does not exist, and None for attributes
# mesh attributes will have the names of the datasets, in order
      axis0data, self.axis0Attrs = VsDatasetBase.readDataset(self, fileName, self.attribute('vsAxis0'), location='/'+self.name,)
      self.axis0.assignDataset(axis0data)
      axis1data, self.axis1Attrs = VsDatasetBase.readDataset(self, fileName, self.attribute('vsAxis1'), location='/'+self.name,)
      self.axis1.assignDataset(axis1data)
      axis2data, self.axis2Attrs = VsDatasetBase.readDataset(self, fileName, self.attribute('vsAxis2'), location='/'+self.name,)
      self.axis2.assignDataset(axis2data)
    else:
      print(f'[RectilinearMesh.readMesh()] Mesh: {location}{meshName} is NOT a rectilinear mesh. ', end='')
      print(f'It is of kind: {self.attribute("vsKind")}. Please create the proper type of mesh.', file=sys.stderr)

## Write a rectilinear mesh group to a file
#
# @param fileName name of the file that the mesh is to be written to
# @param location where the mesh group will be located in the file. Default is root group.
# @param meshName name of the mesh in the file. Default is object name.
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeMesh(self, fileName, location='/', meshName=None, axis0data=None, axis1data=None, axis2data=None, axis0Name=None, axis1Name=None, axis2Name=None, coordinateType=None, transformedMeshName=None, limitsName=None, temporalDimension=None, overwrite=False):
    if meshName is None:
      meshName = self.name
# default
    if meshName is None:
      meshName = 'mesh'
# axis variables are datasets
    if axis0data != None:
      self.axis0.assignDataset(axis0data)
    if axis1data != None:
      self.axis1.assignDataset(axis1data)
    if axis2data != None:
      self.axis2.assignDataset(axis2data)
# overwrite existing attributes with passed, if they are passed
    self.assignAttribute('vsAxis0', axis0Name)
    self.assignAttribute('vsAxis1', axis1Name)
    self.assignAttribute('vsAxis2', axis2Name)
    self.assignAttribute('vsLimits', limitsName)
    self.assignAttribute('vsTransform', coordinateType)
    self.assignAttribute('vsTransformedMesh', transformedMeshName)
    self.assignAttribute('vsTemporalDimension', temporalDimension)

# validate that the required attributes are there
    em1 = '[RectilinearMesh.writeMesh()] Rectilinear Meshes require that the dataset: '
    em2 = ' be defined. Please call this method with: mesh.writeMesh(fileName, ..., '
    em4 = '[RectilinearMesh.writeMesh()] '
    if len(self.axis0.dataset) == 0:
      print(em1 + 'axis0' + em2 + 'axis0=axis0)', file=sys.stderr)
      print(f'[RectilinearMesh.writeMesh()] Mesh not written: {location}{meshName}', file=sys.stderr)
    else:
      if axis0Name is None and self.attribute('vsAxis0') is None:
        self.assignAttribute('vsAxis0', 'axis0')
        debug(em4 + ' Using the default value of "axis0" for the attribute axis0Name.')
        debug('To override this default, please call this method with: mesh.writeMesh(fileName, ..., axis0Name=axis0Name)')
      if axis1Name is None and len(self.axis1.dataset) != 0 and self.attribute('vsAxis1') is None:
        self.assignAttribute('vsAxis1', 'axis1')
        debug(em4 + ' Using the default value of "axis1" for the attribute axis1Name.')
        debug('To override this default, please call this method with: mesh.writeMesh(fileName, ..., axis1Name=axis1Name)')
      if axis2Name is None and len(self.axis2.dataset) != 0 and self.attribute('vsAxis2') is None:
        self.assignAttribute('vsAxis2', 'axis2')
        debug(em4 + ' Using the default value of "axis2" for the attribute axis2Name.')
        debug('To override this default, please call this method with: mesh.writeMesh(fileName, ..., axis2Name=axis2Name)')
      debug('[RectilinearMesh.writeMesh()] Writing rectilinear mesh group: ' + location + str(meshName))
# writeGroup creates the group and writes attributes
      GroupMesh.writeMesh(self,fileName, location=location, meshName=meshName, overwrite=overwrite)
# now write the datasets
      if len(self.axis0.dataset) != 0:
        self.axis0.writeDataset(fileName, location+meshName+'/', self.attribute('vsAxis0'), overwrite=overwrite)
      if len(self.axis1.dataset) != 0:
        self.axis1.writeDataset(fileName, location+meshName+'/', self.attribute('vsAxis1'), overwrite=overwrite)
      if len(self.axis2.dataset) != 0:
        self.axis2.writeDataset(fileName, location+meshName+'/', self.attribute('vsAxis2'), overwrite=overwrite)

class Limits(VsGroupBase):
  r""" Class that defines a limits object. Has methods for reading/writing to/from a file. Limits contain only attributes, although some of the attributes may be arrays. Is a group in the Hdf5 instance. """

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
# @param location where the dataset is located in the file. Defaults to None.
# @param vsType The type of dataset. Defaults to "limits".
#
  def __init__(self, name=None, fileName=None, location=None, vsType='limits', VsHdf5=VsHdf5()):
# Call VsGroupBase constructor first
    VsGroupBase.__init__(self, name, vsType, VsHdf5)
    global limitsName
    limitsName = self.name
    self.assignAttribute('vsType', 'limits')
    if fileName != None:
      self.readLimits(fileName, limitsName=name, location=location)

## Read a limits group from a file and copy all of the attributes. Overloaded method.
#
# @param fileName name of the file that the limits is to be copied from
# @param location where the limits group is located in the file. Defaults to root group.
# @param limitsName name of the limits in the file
#
  def readLimits(self, fileName, location=None, limitsName=None):
    if location is None:
      debug('[readLimits] Reading limits group. Determining which group by attributes.')
      self.readGroupByAttribute(fileName, 'vsType', 'limits')
    else:
      debug('[readLimits] Reading limits group: ' + location + str(limitsName))
      self.readGroup(fileName, location, limitsName)

## Write a limits group to a file
#
# @param fileName name of the file that the limits is to be written to
# @param location where the limits group will be located in the file. Default is root group.
# @param limitsName name of the limits in the file. Default is object name.
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeLimits(self, fileName, location='/', limitsName=None, overwrite=False):
    if limitsName is None:
      limitsName = self.name
    debug('[writeLimits] Writing limits group: ' + location + limitsName)
    self.writeGroup(fileName, location, limitsName, overwrite=overwrite)

class Field(VsDatasetBase):
  r""" Class that defines a field object. Has methods for reading/writing to/from a file. Fields contain a dataset and have attributes attached to that dataset. Not a group. """

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
# @param location where the dataset is located in the file. Defaults to None
# @param vsType The type of dataset. Defaults to "variable".
#
  def __init__(self, name=None, fileName=None, location=None, vsType='variable', VsHdf5=VsHdf5()):
# Call VsDatasetBase constructor first
    VsDatasetBase.__init__(self, name, vsType, VsHdf5)
    global fieldName
    fieldName = self.name
    self.fileName = None
    self.assignAttribute('vsType', 'variable')
    if fileName != None:
      self.readField(fileName, fieldName=name, location=location)
    self.mesh = None
    self.limitsGroup = None
    self.timeGroupTime = None

##
# Read a field dataset. Wrapper over VsDatasetBase.readDataset()
# Sets internal dataset and attributes to the particles object.
#
# @param fileName Name of the file that the dataset is in
# @param fieldName Name of the dataset
# @param location Location of the dataset to be read. Default is None.
#
  def readField(self, fileName, fieldName, location=None):
# only set the fileName if reading from a file!
    self.fileName = fileName
    array, attrs = self.readDataset(fileName, fieldName, location=location)
    return array, attrs

## Write a field object to a file, including dataset and attributes. Check for needed attributes.
#  Will assign vsMesh, vsLimits, and vsTimeGroup attributes in the following order:
#  1. If a value is passed to this method, use it.
#  2. If a value is already stored in the list of attributes, use it.
#  3. If there is a mesh, limits, or timeGroup object that exists, use it.
#  4. If the first 3 cases fail, do not write the field because there isn't the required metadata.
#
# @param fileName name of the file that the field is to be written to
# @param location [optional] where the dataset will be located in the file. Defaults to root group.
# @param fieldName [optional] name of the field in the file. Defaults to self.name.
# @param dumpTime [optional] time of the dump. Defaults to 0.
# @param offset [optional] the type of centering. Defaults to 'nodal'.
# @param mesh [optional] name of the mesh this field is defined upon
# @param limits [optional] name of the limits group for this field
# @param timeGroup [optional] name of the time group for this field
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeField(self,
                 fileName,
                 location='/',
                 fieldName=None,
                 dumpTime=None,
                 offset=None,
                 mesh=None,
                 limits=None,
                 timeGroup=None,
                 indexOrder='compMinorC',
                 overwrite=False):

    if fieldName is None:
      fieldName = self.name

    shouldWriteDataset = True
    # required attributes for fields
    if not self.requires(mesh, 'vsMesh', meshName):
      msg = f'[writeField] Field: {fieldName} not written to file: {fileName}'
      shouldWriteDataset = False

    if not self.requires(limits, 'vsLimits', limitsName):
      msg = f'[writeField] Field: {fieldName} not written to file: {fileName}'
      shouldWriteDataset = False

    if not self.requires(timeGroup, 'vsTimeGroup', timeGroupName):
      msg = f'[writeField] Field: {fieldName} not written to file: {fileName}'
      shouldWriteDataset = False

    # default values
    self.default(offset, 'vsCentering', 'nodal')
    self.default(dumpTime, 'time', 0.0)

    if shouldWriteDataset:
      self.writeDataset(fileName,
                        location,
                        fieldName,
                        dataset=self.dataset,
                        indexOrder=indexOrder,
                        overwrite=overwrite)
# note. should actually check that this was successful by using a try/except block here
      debug('[writeField] Field: ' + fieldName + ' successfully written to file: ' + fileName)
    else:
      print(msg, file=sys.stderr)

##
# Set an array as the dataset to a field object
# Sets internal dataset to the field object, but no attributes
#
# @param array array to set as the internal dataset
#
  def assignDataset(self, array):
    VsDatasetBase.assignDataset(self, array)

## Validate attributes for dataset objects in addition to base class completion
#
  def complete(self):

# find limits group and assign it. This is not an attribute of the base class
    limitsGroupName = self.attribute('vsLimits')
    if limitsGroupName is None:
      debug('[Field.complete()] This dataset does not have a limits group attribute!')
    else:
      debug('[Field.complete()] Setting limits group to: ' + limitsGroupName)
      try:
        self.limitsGroup = Limits(fileName=self.fileName, name='/'+limitsGroupName)
        debug('[Field.complete()] Success.')
      except:
        debug('[Field.complete()] Unable to set limits group to: ' + limitsGroupName + ' in field: ' + self.name)

# find mesh and assign it. This is not an attribute of the base class
    meshGroupName = self.attribute('vsMesh')
    if meshGroupName is None:
      debug('[Field.complete()] This dataset does not have a mesh attribute!')
    else:
      debug('[Field.complete()] Setting mesh to: ' + meshGroupName)
      vsKind = None
      try:
# find the kind of mesh
        mesh = UniformCartesianMesh(fileName=self.fileName)
        vsKind = mesh.getKind()
        debug('[Field.complete()] Determined the kind of mesh is: ' + vsKind)
        if vsKind is None:
          debug('[Field.complete()] Could not determine the kind of mesh.')
        else:
          if vsKind == 'uniform':
            self.mesh = UniformCartesianMesh(fileName=self.fileName)
            debug('[Field.complete()] Set Uniform Cartesian mesh: ' + meshGroupName)
          elif vsKind == 'rectilinear':
            self.mesh = RectilinearMesh(fileName=self.fileName)
            debug('[Field.complete()] Set rectilinear mesh: ' + meshGroupName)
          elif vsKind == 'structured':
            self.mesh = StructuredMesh(fileName=self.fileName)
            debug('[Field.complete()] Set structured mesh: ' + meshGroupName)
          elif vsKind == 'unstructured':
            self.mesh = UnstructuredMesh(fileName=self.fileName)
            debug('[Field.complete()] Set unstructured mesh: ' + meshGroupName)
          else:
            debug('[Field.complete()] The mesh kind: ' + ' is not supported.')
            self.mesh = None
          debug('[Field.complete()] Success.')
      except:
        debug('[Field.complete()] Unable to set mesh to: ' + meshGroupName + ' in field: ' + self.name)

# centering is optional and defaults to "nodal"
    if self.getCentering() is None:
      debug('[Field.complete()] Centering is "None". Setting to default "nodal".')
      self.assignAttribute('vsCentering', 'nodal')
    else:
      debug('[Field.complete()] Centering is ' + self.getCentering())

# get time data
    timeGroupName = self.attribute('vsTimeGroup')
    if timeGroupName is None:
      debug('[Field.complete()] This dataset does not have a time group attribute!')
    else:
      tg = TimeGroup(fileName=self.fileName)
      self.timeGroupTime = tg.attribute('vsTime')
      if self.timeGroupTime is None:
        debug('[Field.complete()] Could not get the simulation time')
      else:
        debug('[Field.complete()] Simulation time found: ' + str(self.timeGroupTime))
      del tg

class TimeGroup(VsGroupBase):
  r""" Class that defines a time group object. Has methods for reading/writing to/from a file. Time groups contain only attributes. Is a group in the Hdf5 instance."""

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
# @param location where the dataset is located in the file. Defaults to None
# @param vsType The type of dataset. Defaults to "time".
#
  def __init__(self, name=None, fileName=None, location=None, vsType='time', VsHdf5=VsHdf5()):
# Call VsGroupBase constructor first
    VsGroupBase.__init__(self, name, vsType, VsHdf5)
    global timeGroupName
    timeGroupName = self.name
    self.assignAttribute('vsType', 'time')
    if fileName != None:
      self.readTimeGroup(fileName, timeGroupName=name, location=location)

## Read a time group from a file and copy all of the attributes. Overloaded method.
#
# @param fileName name of the file that the time is to be copied from
# @param location where the time group is located in the file
# @param timeGroupName name of the time in the file
#
  def readTimeGroup(self, fileName, location=None, timeGroupName=None):
    if location is None:
      debug('[readTimeGroup] Reading time group. Determining which group by attributes.')
      self.readGroupByAttribute(fileName, 'vsType', 'time')
    else:
      debug('[readTimeGroup] Reading time group: ' + location + str(timeGroupName))
      self.readGroup(fileName, location, timeGroupName)

## Write a time group to a file
#
# @param fileName name of the file that the time is to be written to
# @param location where the time group will be located in the file. Default is root group.
# @param timeGroupName name of the time in the file. Default is object name.
# @param dumpTime Real value of dump time.
# @param dumpStep Optional integer value indicating simulation step for the dump time.
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeTimeGroup(self, fileName, location='/', timeGroupName=None, dumpTime=None, dumpStep=None, overwrite=False):
    if timeGroupName is None:
      timeGroupName = self.name

# assign attributes if they are passed
    self.assignAttribute('vsStep', dumpStep)
    self.assignAttribute('vsTime', dumpTime)

# validate that the dump time is there, since it is required
    if self.attribute('vsTime') is None:
      print('[TimeGroup.writeTimeGroup()] Dump time attribute is "None". This is required. ', end='')
      print(f'Time Group: {timeGroupName} not written to file: {fileName}', file=sys.stderr)
    else:
      debug('[TimeGroup.writeTimeGroup()] Writing time group: ' + location + str(timeGroupName) + ' to file: ' + fileName)
    self.writeGroup(fileName, location, timeGroupName, overwrite=overwrite)

##### Convenience accessors for timegroup-specific attributes #####

## Get the dump time
#
# @return The value of the time attribute, or None if that attribute is not defined
#
  def getDumpTime(self):
    return self.attribute('vsTime')

## Get the dump step
#
# @return The value of the vsStep attribute, or None if that attribute is not defined
#
  def getDumpStep(self):
    return self.attribute('vsStep')

class RunInfo(VsGroupBase):
  r""" Class that defines a runInfo object. Has methods for reading/writing to/from a file. RunInfo groups contain only attributes related to software versions, build information, and information about the simulation run. Is a group in the Hdf5 instance. """

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
# @param location where the dataset is located in the file. Defaults to None.
# @param vsType The type of dataset. Defaults to "runInfo".
#
  def __init__(self, name=None, fileName=None, location=None, vsType='runInfo', VsHdf5=VsHdf5()):
# Call VsGroupBase constructor first
    VsGroupBase.__init__(self, name, vsType, VsHdf5)
    global runInfoName
    runInfoName = self.name
    self.assignAttribute('vsType', 'runInfo')
    if fileName != None:
      self.readRunInfo(fileName, runInfoName=name, location=location)

## Read a runInfo group from a file and copy all of the attributes. Overloaded method.
#
# @param fileName name of the file that the runInfo group is to be copied from
# @param location where the runInfo group is located in the file. Defaults to None.
# @param runInfoName name of the runInfo group in the file
#
  def readRunInfo(self, fileName, location=None, runInfoName=None):
    if location is None:
      debug('[readRunInfo] Reading runInfo group. Determining which group by attributes.')
      self.readGroupByAttribute(fileName, 'vsType', 'runInfo')
    else:
      debug('[readRunInfo] Reading runInfo group: ' + location + str(runInfoName))
      self.readGroup(fileName, location, runInfoName)

## Write a runInfo group to a file
#
# @param fileName name of the file that the runInfo is to be written to
# @param location where the runInfo group will be located in the file. Default is root group.
# @param runInfoName name of the runInfo in the file. Default is object name.
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeRunInfo(self, fileName, location='/', runInfoName=None, overwrite=False):
    if runInfoName is None:
      runInfoName = self.name
    debug('[writeRunInfo] Writing runInfo group: ' + location + runInfoName)
    self.writeGroup(fileName, location, runInfoName, overwrite=overwrite)

class Particles(VsDatasetBase):
  r""" Class that defines a particles object. Has methods for reading/writing to/from a file. Particles contain a dataset and have attributes attached to that dataset. Not a group. """

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
# @param location where the dataset is located in the file, defaults to root group
# @param vsType The type of dataset. Defaults to variableWithMesh
#
  def __init__(self, name=None, fileName=None, location='/', vsType='variableWithMesh', VsHdf5=VsHdf5()):
# Call VsDatasetBase constructor first
    VsDatasetBase.__init__(self, name, vsType, VsHdf5)
    global particlesName
    particlesName = self.name
    self.fileName = None
    self.assignAttribute('vsType', 'variableWithMesh')
    if fileName != None:
      self.readParticles(fileName, name, location=location)
    self.limitsGroup = None
    self.timeGroupTime = None

##
# Read a particles dataset. Wrapper over VsDatasetBase.readDataset().
# Sets internal dataset and attributes to the particles object.
#
# @param fileName name of the file that the dataset is in
# @param name name of the dataset
# @param location location of the dataset to be read. Default is root group.
#
  def readParticles(self, fileName, name, location='/'):
# only set the fileName if reading from a file!
    self.fileName = fileName
    array, attrs = self.readDataset(fileName, name, location=location)
    return array, attrs

## Write a particles object to a file, including dataset and attributes.
#  Check for needed attributes.
#  Will assign vsLimits, and vsTimeGroup attributes in the following order:
#  1. If a value is passed to this method, use it.
#  2. If a value is already stored in the list of attributes, use it.
#  3. If there is a limits, or timeGroup object that exists, use it.
#  4. If the first 3 cases fail, do not write the field because there isn't the required metadata.
#  required attributes in addition: charge, mass, numPtclsInMacro
#  default attributes: numSpatialDims = 3 (required)
#  default attributes: vsNumSpatialDims = 3 (required) ?
#  default attributes: time = 0.0 (dump time)
#
# @param fileName name of the file that the field is to be written to
# @param location [optional] where the dataset will be located in the file. Defaults to root group.
# @param particlesName [optional] name of the field in the file. Defaults to self.name.
# @param dumpTime [optional] time of the dump. Defaults to 0.
# @param charge The charge of the particles
# @param mass The mass of the particles
# @param numPtclsInMacro The number of physical particles in one simulation macroparticle
# @param numSpatialDims The number of spatial dimensions (default = 3)
# @param limits [optional] name of the limits group for this field
# @param timeGroup [optional] name of the time group for this field
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeParticles(self, fileName, location='/', particlesName=None, dumpTime=None, charge=None, mass=None, numPtclsInMacro=None, numSpatialDims=None, vsNumSpatialDims=None, limits=None, timeGroup=None, overwrite=False):

    if particlesName is None:
      particlesName = self.name

    shouldWriteDataset = True
    # required attributes for particles
    if not self.requires(charge, 'charge', charge):
     msg = f'[writeParticles] Particles: {particlesName} requires an attribute called \'charge\'.\n'
     msg = msg + f'[writeParticles] Particles: {particlesName} not written to file: {fileName}'
     shouldWriteDataset = False

    if not self.requires(mass, 'mass', mass):
     msg = '[writeParticles] Particles: {particlesName} requires an attribute called \'mass\'.\n'
     msg = '[writeParticles] Particles: {particlesName} not written to file: {fileName}'
     shouldWriteDataset = False

    if not self.requires(numPtclsInMacro, 'numPtclsInMacro', numPtclsInMacro):
     msg = '[writeParticles] Particles: {particlesName} requires an attribute called \'numPtclsInMacro\'.\n'
     msg = '[writeParticles] Particles: {particlesName} not written to file: {fileName}'
     shouldWriteDataset = False

    if not self.requires(limits, 'vsLimits', limitsName):
     msg = '[writeParticles] Particles: {particlesName} not written to file: {fileName}'
     shouldWriteDataset = False

    if not self.requires(timeGroup, 'vsTimeGroup', timeGroupName):
     msg = '[writeParticles] Particles: {particlesName} not written to file: {fileName}'
     shouldWriteDataset = False

    # default values
    self.default(numSpatialDims, 'numSpatialDims', 3)
    self.default(vsNumSpatialDims, 'vsNumSpatialDims', 3)
    self.default(dumpTime, 'time', 0.0)

    if shouldWriteDataset:
      self.writeDataset(fileName,
                        location,
                        particlesName,
                        overwrite=overwrite)
      debug('[writeParticles] Particles: ' + particlesName + ' successfully written to file: ' + fileName)
    else:
      print(msg, file=sys.stderr)

## Validate attributes for dataset objects in addition to base class completion
#
  def complete(self):

# find limits group and assign it. This is not an attribute of the base class
    limitsGroupName = self.attribute('vsLimits')
    if limitsGroupName is None:
      debug('[Particles.complete()] This dataset does not have a limits group attribute!')
    else:
      debug('[Particles.complete()] Setting limits group to: ' + limitsGroupName)
      try:
        self.limitsGroup = Limits(fileName=self.fileName, name=limitsGroupName)
        debug('[Particles.complete()] Success.')
      except:
        debug('[Particles.complete()] Unable to set limits group to: ' + limitsGroupName + ' in field: ' + self.name)

# get time data
    timeGroupName = self.attribute('vsTimeGroup')
    if timeGroupName is None:
      debug('[Field.complete()] This dataset does not have a time group attribute!')
    else:
      tg = TimeGroup(fileName=self.fileName)
      self.timeGroupTime = tg.attribute('vsTime')
      if self.timeGroupTime is None:
        debug('[Field.complete()] Could not get the simulation time')
      else:
        debug('[Field.complete()] Simulation time found: ' + str(self.timeGroupTime))
      del tg

# Convenience accessors for particle-specific attributes
## Get the charge of the particles
#
# @return The value of charge attribute, or None if that attribute is not defined
#
  def getCharge(self):
    return self.attribute('charge')

## Get the mass of the particles
#
# @return The value of mass attribute, or None if that attribute is not defined
#
  def getMass(self):
    return self.attribute('mass')

## Get the number of physical particles per simulation particle
#
# @return The value of the numPtclsInMacro attribute, or None if that attribute is not defined
#
  def getNumPtclsInMacro(self):
    return self.attribute('numPtclsInMacro')

## Get the number of spatial dimensions
#
# @return The value of the vsNumSpatialDims attribute, or None if that attribute is not defined
#
  def getNumSpatialDims(self):
    return self.attribute('vsNumSpatialDims')

class History(VsDatasetBase):
  r""" Class that defines a history object. Has methods for reading/writing to/from a file. histories contain a dataset and have attributes attached to that dataset. Not a group. """

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
# @param location where the dataset is located in the file, defaults to root group
# @param vsType The type of dataset.
#
  def __init__(self, name=None, fileName=None, location='/', vsType='variable', VsHdf5=VsHdf5()):
# Call VsDatasetBase constructor first
    VsDatasetBase.__init__(self, name, vsType, VsHdf5)
    global historyName
    historyName = self.name
    self.assignAttribute('vsType', 'variable')
    if fileName != None:
      self.readHistory(fileName, name, location=location)

##
# Read a history dataset. Wrapper over VsDatasetBase.readDataset()
# Sets internal dataset and attributes to the history object.
#
# @param fileName name of the file that the dataset is in
# @param name name of the history dataset
# @param location location of the dataset to be read. Default is root group.
#
  def readHistory(self, fileName, name, location='/'):
    array, attrs = self.readDataset(fileName, name, location=location)
    return array, attrs

## Write a history object to a file, including dataset and attributes. Check for needed attributes.
#
#  Will assign vsMesh attribute in the following order:
#  1. If a value is passed to this method, use it.
#  2. If a value is already stored in the list of attributes, use it.
#  3. If there is a mesh object that exists, use it.
#  4. If the first 3 cases fail, do not write the dataset because there isn't the required metadata.
#  For histories, only vsMesh attribute is required. There are often additional attributes.
#
# @param fileName name of the file that the history is to be written to
# @param location [optional] where the dataset will be located in the file. Defaults to root group.
# @param historyName [optional] name of the history in the file. Defaults to self.name.
# @param meshName [optional] name of the mesh this history is defined upon. Usually a time mesh.
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeHistory(self, fileName, location='/', historyName=None, meshName=None, overwrite=False):

    if historyName is None:
      historyName = self.name

    shouldWriteDataset = True
    # required attributes for histories
    if not self.requires(meshName, 'vsMesh', meshName):
     msg = f'[writeHistory] History: {historyName} not written to file: {fileName}'
     shouldWriteDataset = False

    if shouldWriteDataset:
      self.writeDataset(fileName,
                        location,
                        historyName,
                        extendable=True,
                        overwrite=overwrite)
      debug(f'[writeHistory] History: {historyName} successfully written to file: {fileName}')
    else:
      print(msg, file=sys.stderr)

class Group(VsGroupBase):
  r""" Class that defines a generic group object. Has methods for reading/writing to/from a file. Groups contain only attributes. Generic groups are typically not VizSchema compliant, in that they do not define a 'vsType' attribute, but they may be. This is mostly just a wrapper around the VsGroupBase base class, because that class should not be instantiated directly. Is a group in the Hdf5 instance. """

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
# @param location where the dataset is located in the file, defaults to root group
# @param vsType The type of dataset.
#
  def __init__(self, name=None, fileName=None, location=None, vsType=None, VsHdf5=VsHdf5()):
# Call VsGroupBase constructor first
    VsGroupBase.__init__(self, name, vsType, VsHdf5)
    if fileName != None:
      self.readGroup(fileName, name, location=location)

## Read a group from a file and copy all of the attributes.
#
# @param fileName name of the file that the group is to be copied from
# @param groupName name of the group in the file
# @param location where the group is located in the file, defaults to root group
#
  def readGroup(self, fileName, groupName, location='/'):
    if location is None:
      location = '/'
    debug(('[readGroup] Reading group: ' + location + '/' + groupName).replace('//','/'))
    VsGroupBase.readGroup(self, fileName, location, groupName)

## Write a generic group to a file.
#
# @param fileName name of the file that the group is to be written to
# @param location where the group will be located in the file. Default is root group.
# @param groupName name of the group in the file. Default is object name.
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeGroup(self, fileName, location='/', groupName=None, overwrite=False):
    if groupName is None:
      groupName = self.name
    debug('[writeGroup] Writing group: ' + location + groupName)
    VsGroupBase.writeGroup(self, fileName, location, groupName, overwrite=overwrite)

class Dataset(VsDatasetBase):
  r""" Class that defines a generic dataset object. Has methods for reading/writing to/from a file. Datasets may contain attributes. Generic datasets are not neccesarily VizSchema compliant, in that they do not define a 'vsType' attribute, but they may be. This is mostly just a wrapper around the VsDatasetBase base class, because that class should not be instantiated directly, but also contains method for adding attributes to the dataset. Is a dataset in the Hdf5 instance. """

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
# @param location where the dataset is located in the file, defaults to root group
# @param vsType The type of dataset.
#
  def __init__(self, name=None, fileName=None, location='/', vsType=None, VsHdf5=VsHdf5()):
# Call VsDatasetBase constructor first
    VsDatasetBase.__init__(self, name, vsType, VsHdf5)
    if fileName != None:
      self.readDataset(fileName, name, location=location)

## Read a dataset from a file and copy all of the attributes.
#
# @param fileName name of the file that the dataset is to be copied from
# @param datasetName name of the dataset in the file
# @param location where the dataset is located in the file, defaults to root group
#
  def readDataset(self, fileName, datasetName, location='/'):
    debug('[readDataset] Reading dataset: ' + location + datasetName)
    array, attrs = VsDatasetBase.readDataset(self, fileName, datasetName, location=location)
    return array, attrs

## Write a generic dataset to a file.
#
# @param fileName name of the file that the dataset is to be written to
# @param location where the dataset will be located in the file. Default is root group.
# @param datasetName name of the dataset in the file. Default is object name.
# @param extendable False if dataset to be written should be extendable, e.g. Histories
# @param overwrite True if dataset should be overwritten if it exists
#
  def writeDataset(self,
                   fileName,
                   location='/',
                   datasetName=None,
                   extendable=False,
                   indexOrder='compMinorC',
                   overwrite=False):
    if datasetName is None:
      datasetName = self.name
    debug('[writeDataset] Writing dataset: ' + str(location) + str(datasetName))
    VsDatasetBase.writeDataset(self,
                               fileName,
                               location,
                               datasetName,
                               extendable=extendable,
                               indexOrder=indexOrder,
                               overwrite=overwrite)

class VsFileReader(VsBase):
  r""" Class that parses an entire dump file, reading in all VizSchema objects. TODO: include validation of Vs objects here."""

## constructor
#
# @param name The name of this object
# @param fileName The filename from which to read VS objects
#
  def __init__(self, name=None, fileName=None, VsHdf5=VsHdf5(), silent=False, noData=False):
    self.objectDict = {}
    self.vsw = VsHdf5
    self.silent = silent
    if fileName != None:
      self.parseFile(fileName, noData=noData)

## Parse an entire file, extracting all the Vs objects
#
# @param fileName The filename from which to read VS objects
# @return a dictionary with object name and pointer to that object, as read from the file
#
  def parseFile(self, fileName, noData=False):
    oStdout = sys.stdout
    oStderr = sys.stderr
    if self.silent is True:
      sys.stdout = nullDev()
      sys.stderr = nullDev()
    nodePathList = self.getNodePathList(fileName)
    for nodePath in nodePathList:
      nh = self.getNodeHandle(nodePath)
      #objectPathName = nh._v_pathname
      objectName = nh._v_name
      location = nh._v_parent._v_pathname + '/'
      location = location.replace('//','/')
      vsType = None
      try:
        vsType = nh._v_attrs['vsType']
        if type(vsType) is numpy.bytes_:  vsType = vsType.decode('UTF-8')
      except:
        pass
      vsKind = None
      try:
        vsKind = nh._v_attrs['vsKind']
        if type(vsKind) is numpy.bytes_:  vsKind = vsKind.decode('UTF-8')
      except:
        pass
      self.vsType = vsType

      if vsType == 'variable': # it is a field, requires a mesh
        field = Field(name=objectName)
        field.fileName = fileName
        try:
# In normal operation, read the data and put it in the objectDict dictionary
          if noData is False:
            field.readField(fileName, objectName, location=location)
# Otherwise, just add an empty field, e.g. when scanning dump files to get the type.
          self.objectDict[objectName] = field
          print(f'[VsFileReader.parseFile()] Successfully read in field named: {objectName}')
          print(f'[VsFileReader.parseFile()] Note that the field: {objectName} requires a mesh named: {field.attribute("vsMesh")}')
        except:
          print(f'[VsFileReader.parseFile()] Unable to read in field named: {objectName} in file: {fileName}', file=sys.stderr)

      if vsType == 'variableWithMesh': # it is particles
        particles = Particles(name=objectName)
        try:
          if noData is False:
            particles.readParticles(fileName, objectName, location=location)
          self.objectDict[objectName] = particles
          print(f'[VsFileReader.parseFile()] Successfully read in particles named: {objectName} from file: {fileName}')
        except:
          print(f'[VsFileReader.parseFile()] Unable to read in particles named: {objectName} in file: {fileName}', file=sys.stderr)

      if vsType == 'mesh': # it is a mesh
        mesh = Mesh(fileName=fileName, name=objectName, location=location)
        if mesh.getKind() != None:
          print(f'[VsFileReader.parseFile()] Successfully read in mesh named: {objectName} of kind: {mesh.getKind()} from file: {fileName}')
          self.objectDict[objectName] = mesh
        else:
          print(f'[VsFileReader.parseFile()] Unable to read in mesh named: {objectName} in file: {fileName}', file=sys.stderr)

      if vsType == 'runInfo': # it is a runInfo group
        runInfo = RunInfo(name=objectName)
        try:
          runInfo.readRunInfo(fileName, location='/', runInfoName=objectName)
          self.objectDict[objectName] = runInfo
          print(f'[VsFileReader.parseFile()] Successfully read in runInfo group named: {objectName} from file: {fileName}')
          debug('The data file: ' + fileName + ' was generated by the software package: ' + str(runInfo.attribute('vsSoftware')))
        except:
          print('[VsFileReader.parseFile()] Unable to read in runInfo group named: {objectName} in file: {fileName}', file=sys.stderr)

      if vsType == 'time': # it is a time group
        time = TimeGroup(name=objectName)
        try:
          time.readTimeGroup(fileName, location='/', timeGroupName=objectName)
          self.objectDict[objectName] = time
          print(f'[VsFileReader.parseFile()] Successfully read in time group named: {objectName} from file: {fileName}')
        except:
          print(f'[VsFileReader.parseFile()] Unable to read in time group named: {objectName} in file: {fileName}', file=sys.stderr)

      if vsType == 'limits': # it is a limits group
# limits groups have different kinds. Should implement derived classes, although required attributes are the same for Cartesian and Cylindrical vsKinds.
        limits = Limits(name=objectName)
        try:
          limits.readLimits(fileName, location='/', limitsName=objectName)
          self.objectDict[objectName] = limits
          print(f'[VsFileReader.parseFile()] Successfully read in limits group named: {objectName}')
        except:
          print(f'[VsFileReader.parseFile()] Unable to read in limits group named: ', end='')
          print(f'{objectName} of kind: {vsKind} in file: {fileName}', file=sys.stderr)

      if vsType == 'vsVars': # it is a derived variables group
        derivedVariablesGroup = Group(name=objectName)
        try:
          derivedVariablesGroup.readGroup(fileName, groupName=objectName)
          self.objectDict[objectName] = derivedVariablesGroup
          print('[VsFileReader.parseFile()] Successfully read in derived variables group named: ', end='')
          print(f'{objectName} from file: {fileName}')
        except:
          print('[VsFileReader.parseFile()] Unable to read in derived variables group named: ', end='')
          print(f'{objectName} in file: {fileName}', file=sys.stderr)

    self.vsw.closeFile()
    if self.silent is True:
      sys.stdout = oStdout
      sys.stderr = oStderr
    return self.objectDict

