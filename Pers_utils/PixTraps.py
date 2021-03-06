import numpy as np
from Pers_utils.Ramp import Ramp
from Pers_utils.MyExceptions import CustExc1M3V
import copy
from numba import jit

class PixTraps(object):

    '''
    Class to describe the ensemble of traps for a pixel
    in the persistence model

    :t_trp:
        Trapping times in sec

    :t_rel:
        Release times in sec

    :cmin:
        Number of counts in the diode
        that are necessary to expose
        each trap to free charge (i.e. if counts < cmin[i]
        the i-th trap cannot be filled)

    '''

    def __init__(self, t_trp, t_rel, cmin):
        self.t_trp = t_trp
        self.t_rel = t_rel
        self.cmin  = cmin

        if ( ( self.t_trp.shape[0] == self.t_rel.shape[0] == self.cmin.shape[0]) == False):
            raise CustExc1M3V('Trapping times, release times and min counts numpy.ndarrays must be of the same shape instead they are resp.',
                              self.t_trp.shape, self.t_rel.shape, self.cmin.shape)
        else:
            self.ntraps = self.t_trp.shape[0]

        '''
        Initialise the traps to empty
        '''
        self.states   = np.zeros(self.ntraps,dtype=np.bool_)
        self.occ_prob = np.zeros(self.ntraps,dtype=np.float_)

        '''
        Convenience variables for the diff. equations
        '''
        self.a = (self.t_trp + self.t_rel)/(self.t_trp*self.t_rel)
        self.b = self.t_rel/(self.t_trp + self.t_rel)

    def set_new_states(self,ts,te,counts):
        '''
        Method to see whether the state changes within an interval
        with the diode at a certain total counts level

        :ts:
            starting time

        :te:
            ending time

        :counts:
            total counts in the diode at ts<t<te
        '''

        '''
        Determine which equation to apply. 
        '''

        above_cut   = self.cmin <= counts
        below_cut_1 = (self.cmin > counts) & (self.states == True)
        below_cut_0 = (self.cmin > counts) & (self.states == False)


        '''
        If the counts are above cmin
        '''
        exp1      = np.exp(self.a[above_cut]*(ts-te))
        self.occ_prob[above_cut] = self.states[above_cut].astype(np.float_) * exp1 + self.b[above_cut]*(1-exp1)
        
        exp2      = np.exp( (ts-te) / self.t_rel[below_cut_1] )
        self.occ_prob[below_cut_1] = exp2

        self.occ_prob[below_cut_0] = 0.


        '''
        Draw uniform random numbers and decide whether each trap is occupied or not
        '''

        check = np.random.random_sample(size=self.ntraps)
        self.states = np.array( check < self.occ_prob ,dtype=np.bool_)
        
    def end_ramp_occ(self,rmp):
        '''
        Method that computes the occupation of each trap in the pixel
        at the end of the rmp Ramp.  If a trap is filled at that
        time, then it will produce an electron with exponentially
        decaying probability. If it is empty it won't.

        :rmp:
            rmp is a Ramp object that describes the previous history
            of the pixel (in raw counts) up to the time
            when we start measuring persistence.
        '''

        ntimes = len(rmp.rtime)
        self.totfill = np.zeros((ntimes-1),dtype=np.float_)
        for i in range(ntimes-1):
            self.set_new_states(rmp.rtime[i],rmp.rtime[i+1],rmp.rcts[i])
            self.totfill[i] = np.sum(self.states)

    def reset(self):
        '''
        Method to reset the occupancy of all traps to 0
        '''

        self.states[:]   = 0. 
        self.occ_prob[:] = 0.


    def get_acc_charge(self,t_after):
        '''
        Method to measure the accumulated charge at times t_after
        after the end of the ramp. It assumes the diode
        is no longer being exposed to light
        '''

        charge = np.zeros(len(t_after))

        filled  = (self.states == True)
        usest   = copy.deepcopy(self.states[filled])
        usert   = copy.deepcopy(self.t_rel[filled])

        for i in range(len(t_after)):
            exp       = np.exp( -1*(t_after[i]) / usert )
            check     = np.random.random_sample(size=len(exp))
            idis      = check > exp 
            ikeep     = check < exp
            
            charge[i] = charge[i-1] + np.sum(idis)
            usest     = usest[ikeep]
            usert     = usert[ikeep]

        return charge
