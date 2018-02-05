# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from . import core, geom, io
from .data import Data, Window, WindowPicker

import numpy as np
import math
from scipy import signal
import matplotlib.pyplot as plt
from matplotlib import gridspec
from matplotlib.collections import LineCollection


class Pair(Data):
    """
    The Pair: work with 2-component data.
        
    Usage: Pair(**kwargs)     => create Pair of synthetic data
           Pair(x,y) => creates Pair from two traces stored in numpy arrays x and y.
    
    Keyword Arguments:
        - delta = 1. (sample interval) [default] | float
        # - t0 = 0. (start time) DEVELOPMENT
    
    Naming Keyword Arguments:
        - name = 'untitled' (should be unique identifier) | string
        - cmplabels = ['cmp1','cmp2'] | list of strings
        # - units = 's' (for labelling) | string
    
    Geometry Keyword Arguments (if in doubt don't use):
        # - geom = 'geo' (N,E) / 'ray' (SV,SH) / 'cart' (X,Y)
        # - cmpvecs = np.eye(2)
        # - rcvloc = (lat,lon,r) / (x,y,z)
        # - srcloc =  (lat,lon,r) / (x,y,z)
        # - rayloc =  rcvloc # arbirary point specified by user
        # - rayvec = [0,0,1] # wave plane normal

    Methods:
        # display
            - plot() # plot traces and partice motion
            - ppm() # plot particle motion
            - ptr() # plot waveform trace
        # splitting
            - split(fast,lag)
            - unsplit(fast,lag)
        # useful
            - t()           # time
            - data()        # both x and y in one array
            - chop()        # windowed data
            - rotateto()
        # windowing
            - set_window(start,end,Tukey=None)         
        # io
            - copy()
            - save()
        # window picker
            - plot(pick=True)
    """
    def __init__(self,*args,**kwargs):
        
        # if no args make synthetic
        if len(args) == 0:
            x, y = core.synth(**kwargs)
        # otherwise read in data
        elif len(args) == 2:
            if not (isinstance(args[0],np.ndarray) & isinstance(args[1],np.ndarray)):
                raise TypeError('expecting numpy arrays')
            x, y = args[0], args[1]
        else:
            raise Exception('Unexpected number of arguments')
        
        # Initialise Data
        self.Data = Data.__init__(self, x, y, *args, **kwargs)



    # METHODS
      
    def split(self, fast, lag):
        """
        Applies splitting operator.
        
        .. warning:: shortens trace length by *lag*.
        """
        # convert time shift to nsamples -- must be even
        samps = core.time2samps(lag, self.delta, mode='even')
        # find appropriate rotation angle
        origangs = self.cmpangs()
        self.rotateto(0)
        # apply splitting
        self.x, self.y = core.split(self.x, self.y, fast, samps)
        self.rotateto(origangs[0])
           
    def unsplit(self, fast, lag):
        """
        Reverses splitting operator.
        
        .. warning:: shortens trace length by *lag*.
        """
        # convert time shift to nsamples -- must be even
        samps = core.time2samps(lag, self.delta, mode='even')
        # find appropriate rotation angle
        origangs=self.cmpangs()
        self.rotateto(0)
        # apply splitting
        self.x, self.y = core.unsplit(self.x, self.y, fast, samps)
        self.rotateto(origangs[0])
       
    def rotateto(self, degrees):
        """
        Rotate traces so that cmp1 lines up with *degrees*
        """
        # find appropriate rotation matrix
        ang = math.radians(degrees)
        cang = math.cos(ang)
        sang = math.sin(ang)
        # define the new cmpvecs
        backoff = self.cmpvecs
        self.cmpvecs = np.array([[ cang,-sang],
                                 [ sang, cang]])
        rot = np.dot(self.cmpvecs.T, backoff)
        # rotate data
        xy = np.dot(rot, self.data())
        self.x, self.y = xy[0], xy[1]
        # reset label
        self.set_labels()



            
    # def set_pol(self,*args):
    #     if len(args) == 0:
    #         self.pol = self.get_pol()
    #     elif len(args) == 1:
    #         self.pol = float(args[0])
    #     else:
    #         raise Exception('Unexpected number of arguments')
    #     return
    
    # Utility 
    
  


    # def get_pol(self):
    #     """Return principal component orientation"""
    #     # rotate to zero
    #     rot = self.cmpvecs.T
    #     data = self.chop().data()
    #     xy = np.dot(rot,data)
    #     _,eigvecs = core.eigcov(xy)
    #     x,y = eigvecs[:,0]
    #     pol = np.rad2deg(np.arctan2(y,x))
    #     return pol
        
    def eigen(self, window=None):
        self.eigvals, self.eigvecs = core.eigcov(self.data())
        
    def power(self):
        return self.x**2, self.y**2
        
    # def snrRH(self):
    #     data = self.copy()
    #     data.rotateto(data.pol())
    #     return core.snrRH(data.chop().data())

    def cmpangs(self):
        cmp1 = self.cmpvecs[:, 0]
        cmp2 = self.cmpvecs[:, 1]
        def getang(c) : return np.rad2deg(np.arctan2(c[1], c[0]))
        return getang(cmp1), getang(cmp2)          
    
    # def chop(self):
    #     """
    #     Chop data to window
    #     """
    #     chop = self.copy()
    #     chop.x, chop.y = core.chop(chop.x, chop.y, window=chop.window)
    #     chop.window.offset = 0
    #     return chop

    
    def splitting_intensity(self, **kwargs):
        """
        Calculate the splitting intensity as defined by Chevrot (2000).
        """
        copy = self.copy()
        copy.rotateto(copy.pol)
        copy.x = np.gradient(copy.x)
        copy.chop()
        rdiff, trans = copy.x, copy.y
        s = -2 * np.trapz(trans * rdiff) / np.trapz(rdiff**2)
        return s

        
    # Plotting
              
    def plot(self, **kwargs):
        """
        Plot trace data and particle motion
        """

        fig = plt.figure(figsize=(12, 3))     
        gs = gridspec.GridSpec(1, 2, width_ratios=[3, 1]) 
        
        # trace
        ax0 = plt.subplot(gs[0])
        self._ptr(ax0, **kwargs)
        
        # particle  motion
        ax1 = plt.subplot(gs[1])
        self._ppm( ax1, **kwargs)   
        
        # optional pick window
        if 'pick' in kwargs and kwargs['pick'] == True:
            windowpicker = WindowPicker(self, fig, ax0)
            windowpicker.connect()
                                 
        # show
        plt.tight_layout()
        plt.show()
        
    def ppm(self, **kwargs):
        """Plot particle motion"""
        fig, ax = plt.subplots()
        self._ppm(ax, **kwargs)
        plt.show()
        
    def ptr(self, **kwargs):
        """Plot trace data"""
        fig, ax = plt.subplots()
        self._ptr(ax, **kwargs)
        plt.show()

    def _ptr( self, ax, **kwargs):
        """Plot trace data on *ax* matplotlib axis object.
        """    
        # plot data
        t = self.t()
        
        # set labels
        if 'cmplabels' not in kwargs: kwargs['cmplabels'] = self.cmplabels
        ax.plot( t, self.x, label=kwargs['cmplabels'][0])
        ax.plot( t, self.y, label=kwargs['cmplabels'][1])
        ax.legend(framealpha=0.5)
    
        # set limits
        lim = np.abs(self.data()).max() * 1.1
        if 'ylim' not in kwargs: kwargs['ylim'] = [-lim, lim]
        ax.set_ylim(kwargs['ylim'])
        if 'xlim' in kwargs: ax.set_xlim(kwargs['xlim'])
    
        # set axis label
        if 'units' not in kwargs: kwargs['units'] = 's'            
        ax.set_xlabel('Time (' + kwargs['units'] +')')

        # plot window markers
        if self.window.width < self._nsamps():
            w1 = ax.axvline(self.wbeg(), linewidth=1, color='k')
            w2 = ax.axvline(self.wend(), linewidth=1, color='k')    
        
        # plot additional markers
        if 'marker' in kwargs:
            print('here')
            if type(kwargs['marker']) is not list: kwargs['marker'] = [ kwargs['marker'] ]
            [ ax.axvline(float(mark), linewidth=1, color='b') for mark in kwargs['marker'] ]
            
        return

    def _ppm(self, ax, **kwargs):
        """Plot particle motion on *ax* matplotlib axis object.
        """
        
        data = self.chop()
        data.rotateto(0)
        x, y = data.x, data.y
        t = data.t()
                
        # plot data
        # ax.plot(self.chop().y,self.chop().x)
        
        # multi-colored
        norm = plt.Normalize(t.min(), t.max())
        points = np.array([y, x]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        lc = LineCollection(segments, cmap='plasma', norm=norm, alpha=0.7)
        lc.set_array(t)
        lc.set_linewidth(2)
        line = ax.add_collection(lc)
        # plt.colorbar(line)
    
        # set limit
        lim = np.abs(self.data()).max() * 1.1
        if 'lims' not in kwargs: kwargs['lims'] = [-lim, lim] 
        ax.set_aspect('equal')
        ax.set_xlim(kwargs['lims'])
        ax.set_ylim(kwargs['lims'])
    
        # set labels
        if 'cmplabels' not in kwargs: kwargs['cmplabels'] = data.cmplabels
        ax.set_xlabel(kwargs['cmplabels'][1])
        ax.set_ylabel(kwargs['cmplabels'][0])
        
        # turn off tick annotation
        ax.axes.xaxis.set_ticklabels([])
        ax.axes.yaxis.set_ticklabels([])
        return
        
    # def grid_eigen(self, **kwargs):
    #     """Grid search for splitting parameters using the transverse energy minimisation
    #        eigenvalue method (Silver and Chan, 1991)"""
    #     # MAKE MEASUREMENT
    #     stuff = np.asarray(self._gridsearch(core.eigvalcov, **kwargs))
    #     lam1, lam2 = stuff[:,:,1].T, stuff[:,:,0].T
    #     return lam1, lam2
    #
    # def grid_trans(self, **kwargs):
    #     """Grid search for splitting parameters using the transverse energy minimisation
    #        user-specified polarisation method (Silver and Chan, 1998)"""
    #
    #     if 'pol' not in kwargs:
    #         raise Exception('pol must be specified')
    #
    #     # MAKE MEASUREMENT
    #     stuff = np.asarray(self._gridsearch(core.transenergy, **kwargs))
    #     enrgy1, enrgy2 = stuff[:,:,1].T, stuff[:,:,0].T
    #     return enrgy1, enrgy2
    #
    # def grid_xcorr(self, **kwargs):
    #     """Grid search for splitting parameters using the cross correlation method (Ando, 1980)"""
    #     # MAKE MEASUREMENT
    #     stuff = np.asarray(self._gridsearch(core.transenergy, **kwargs))
    #     xc = stuff[:,:,0].T
    #     return xc
    #
    # def eigenM(self, **kwargs):
    #
    #     # setup dictionary to hold measurement
    #     self.eigenM = {}
    #
    #     # get degs, lags and slags
    #     self.eigenM['degs'], self.eigenM['lags'], _ = self._get_degs_lags_slags(self, **kwargs)
    #     # source and receiver corrections
    #
    #
    #     # make measurement
    #     self.eigenM['lam1'], self.eigenM['lam2'] = self.grid_eigen(self, **kwargs)
    #
    #     # get useful info
    #     maxidx = core.max_idx(lam1/lam2)
    #     fast = DEGS[maxloc]
    #     tlag  = LAGS[maxloc]
    #
    #     # estimate error
    #     core.ftest(self.lam2, self.ndf(), alpha=0.05)
    #
    #     # Populate dictionary object
    #     self.eigenM = {'lags': lags, 'degs': degs,
    #                    'rcvcorr': kwargs['rcvcorr'], 'srccorr': kwargs['srccorr'],
    #                    'lam1': lam1, 'lam2': lam2, 'maxidx': maxidx,
    #                    'fast': fast, 'tlag': tlag, 'dfast': dfast, 'dtlag': dtlag
    #                    }

    def data_corr(self, fast, lag, **kwargs):
        # copy data     
        data_corr = self.copy()
        # rcv side correction     
        if kwargs['rcvcorr'] is not None:
            data_corr.unsplit(*kwargs['rcvcorr'])    
        # target layer correction
        data_corr.unsplit(fast, lag)  
        # src side correction
        if kwargs['srccorr'] is not None:
            data_corr.unsplit(*kwargs['srccorr'])
        return data_corr
                
    # Common methods    
    
    # def _gridsearch(self, func, **kwargs):
    #
    #     """
    #     Grid search for splitting parameters applied to data using the function defined in func
    #     rcvcorr = receiver correction parameters in tuple (fast,lag)
    #     srccorr = source correction parameters in tuple (fast,lag)
    #     """
    #
    #     # get degs, lags and slags
    #     degs, _, slags = self._get_degs_lags_slags(self, **kwargs)
    #
    #     # receiver correction
    #     rcvcorr = None
    #     if ('rcvcorr' in kwargs):
    #         if not isinstance(kwargs['rcvcorr'],tuple): raise TypeError('rcvcorr must be tuple')
    #         if len(kwargs['rcvcorr']) != 2: raise Exception('rcvcorr must be length 2')
    #         # convert time shift to nsamples -- must be even
    #         deg, lag = kwargs['rcvcorr']
    #         samps = core.time2samps(lag, self.delta, 'even')
    #         rcvcorr = (deg, samps)
    #
    #     # source correction
    #     srccorr = None
    #     if ('srccorr' in kwargs):
    #         if not isinstance(kwargs['srccorr'],tuple): raise TypeError('srccorr must be tuple')
    #         if len(kwargs['srccorr']) != 2: raise Exception('srccorr must be length 2')
    #         # convert time shift to nsamples -- must be even
    #         deg, lag = kwargs['srccorr']
    #         samps = core.time2samps(lag, self.delta, 'even')
    #         srccorr = (deg, samps)
    #
    #     # avoid using "dots" in loops for performance
    #     rotate = core.rotate
    #     lag = core.lag
    #     chop = core.chop
    #     unsplit = core.unsplit
    #
    #     # ensure trace1 at zero angle
    #     copy = self.copy()
    #     copy.rotateto(0)
    #     x, y = copy.x, copy.y
    #
    #     # pre-apply receiver correction
    #     if 'rcvcorr' in kwargs:
    #         rcvphi, rcvlag = rcvcorr
    #         x, y = unsplit(x, y, rcvphi, rcvlag)
    #
    #     ######################
    #     # inner loop function
    #     ######################
    #
    #     # source correction
    #
    #     if 'srccorr' in kwargs:
    #         srcphi, srclag = srccorr
    #         def srccorr(x, y, ang):
    #             x, y = unsplit(x, y, srcphi-ang, srclag)
    #             return x, y
    #     else:
    #         def srccorr(x, y, ang):
    #             return x, y
    #
    #     # rotate to polaristation (needed for tranverse min)
    #     if 'pol' in kwargs:
    #         pol = kwargs['pol']
    #         def rotpol(x, y, ang):
    #             # rotate to pol
    #             x, y = rotate(x, y, pol-ang)
    #             return x, y
    #     else:
    #         def rotpol(x, y, ang):
    #             return x, y
    #
    #     # actual inner loop function
    #     def process(x, y, ang, shift):
    #         # remove shift
    #         x, y = lag(x, y, -shift)
    #         x, y = srccorr(x, y, ang)
    #         x, y = chop(x, y, window=self.window)
    #         x, y = rotpol(x, y, ang)
    #         return func(x, y)
    #
    #     # Do the grid search
    #     prerot = [ (rotate(x, y, ang), ang) for ang in degs ]
    #
    #     out = [ [ process(data[0], data[1], ang, shift) for shift in slags ]
    #             for (data, ang) in prerot  ]
    #
    #     return out
      
        
            
        
    # Special
    
    def __eq__(self, other) :
        # check same class
        if self.__class__ != other.__class__: return False
        # check same keys
        if set(self.__dict__) != set(other.__dict__): return False
        # check same values
        for key in self.__dict__.keys():
            if not np.all( self.__dict__[key] == other.__dict__[key]): return False
        # if reached here then the same
        return True

