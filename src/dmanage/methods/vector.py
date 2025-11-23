import numpy as np
from scipy.spatial.transform import Rotation as R


def vrrotvec(a,b):
    """
    Determine the rotation vector from 2 vectors

    """
    if np.array_equal(a,b):
        axis = a
        angle = 0
    else:
        axis = np.cross(a,b)/np.linalg.norm(np.cross(a,b))
        angle = np.arccos(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)))
    r = R.from_rotvec(angle * axis).as_matrix()
    return r


def curl(array,dsteps=None):
    s = array.shape
    if type(dsteps) == type(None):
        dsteps = tuple([1]*(len(s)-1))
    elif type(dsteps) is list: tuple(dsteps)
    # keys = 'ABCDE'
    # dstepsDict = {}
    # for i,dstep in enumerate(dsteps):
    #     dstepsDict[keys[i]]=dstep

    #axis=tuple(np.arange(0,len(s)-1))
    grads = np.gradient(array,*dsteps,axis=tuple(np.arange(0,len(s)-1)))

    if len(s) == 4:
        curl = np.zeros(s)
        curl[:,:,:,0] = grads[1][:,:,:,2]-grads[2][:,:,:,1]
        curl[:,:,:,1] = grads[2][:,:,:,0]-grads[0][:,:,:,2]
        curl[:,:,:,2] = grads[0][:,:,:,1]-grads[1][:,:,:,0]

    if len(s) == 3:
        curl = np.zeros(s[:-1])
        curl = grads[0][:,:,1]-grads[1][:,:,0]
    return curl
