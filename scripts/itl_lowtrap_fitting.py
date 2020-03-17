import argparse
import os
import numpy as np
import emcee
from os.path import join
from astropy.io import fits
import corner
import time

from ctisim.fitting import OverscanFitting, JointSimulatedModel
from ctisim.core import LinearTrap
from ctisim.utils import ITL_AMP_GEOM, E2V_AMP_GEOM, save_mcmc_results, OverscanParameterResults

RAFT_NAMES = ['R01', 'R02', 'R03', 
              'R10', 'R13', 'R14',
              'R20', 'R23', 'R24',
              'R31', 'R32', 'R33', 'R34',
              'R41', 'R42', 'R43']

CCD_NAMES = ['S00', 'S01', 'S02',
             'S10', 'S11', 'S12',
             'S20', 'S21', 'S22',]

def main(sensor_id, amp, nsteps, nwalkers, burnin=100, output_dir='./'):

    ## Config variables
    start = 1
    stop = 4
    ccd_type = 'itl'
    max_signal = 10000.
    read_noise = 7.0

    overscan_results_file = '/nfs/slac/g/ki/ki19/lsst/snyder18/LSST/Data/BOT/6790D_linearity/R20/S02/R20_S02_overscan_results.fits'
    hdulist = fits.open(overscan_results_file)

    ## CCD geometry info
    if ccd_type == 'itl':
        ncols = ITL_AMP_GEOM.nx + ITL_AMP_GEOM.prescan_width
    elif ccd_type == 'e2v':
        ncols = E2V_AMP_GEOM.nx + E2V_AMP_GEOM.prescan_width

    signals_all = hdulist[amp].data['FLATFIELD_SIGNAL']
    data_all = hdulist[amp].data['COLUMN_MEAN'][:, ncols+start-1:ncols+stop]
    indices = (signals_all < max_signal)
    signals = signals_all[indices]
    data = data_all[indices]   

    ## Get OutputAmplifier fit results
    parameter_results_file = '/nfs/slac/g/ki/ki19/lsst/snyder18/LSST/Data/BOT/6790D_linearity/R20/S02/R20_S02_parameter_results.fits'
    parameter_results = OverscanParameterResults.from_fits(parameter_results_file)
    output_amplifier = parameter_results.single_output_amplifier(amp, 1.0)

    ## MCMC Fit
    params0 = [-6.0, 3.5, 0.4, 0.08]
    constraints = [(-7, -5.3), (0., 10.), (0.01, 1.0), (0.001, 1.0)]
    overscan_fitting = OverscanFitting(params0, constraints, JointSimulatedModel, 
                                       start=start, stop=stop)

    scale = (0.4, 0.5, 0.05, 0.005)
    pos = overscan_fitting.initialize_walkers(scale, nwalkers)
    
    args = (signals, data, read_noise/np.sqrt(2000.), ITL_AMP_GEOM, LinearTrap, 
            output_amplifier)
    sampler = emcee.EnsembleSampler(nwalkers, len(params0), overscan_fitting.logprobability, 
                                    args=args)
    sampler.run_mcmc(pos, nsteps)

    outfile = join(output_dir, '{0}_Amp{1}_lowtrap_mcmc.fits'.format(sensor_id, amp))
    save_mcmc_results(sensor_id, amp, sampler.chain, outfile, LinearTrap)
    
    ctiexp = np.median(sampler.chain[:, burnin:, 0])
    parameter_results.cti_results[amp] = 10**ctiexp

    samples = sampler.chain.reshape((-1, 4))
    fig = corner.corner(samples)
    fig.savefig(join(output_dir, '{0}_Amp{1}_lowtrap_triangle.png'.format(sensor_id, amp)))

    parameter_results.write_fits(parameter_results_file, overwrite=True)

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('sensor_id', type=str, help='Sensor id (e.g. R20_S02)')
    parser.add_argument('amp', type=int, help='Amplifier number (1-16)')
    parser.add_argument('nwalkers', type=int,
                        help='Number of walkers (must be greater than 8).')
    parser.add_argument('nsteps', type=int,
                        help='Number of steps for each chain.')
    parser.add_argument('--burnin', '-b', type=int, default=100,
                        help='Number of burnin steps for each chain.')
    parser.add_argument('--output_dir', '-o', type=str,
                        default='./',
                        help='Output directory for analysis results.')
    args = parser.parse_args()

    main(args.sensor_id, args.amp, args.nsteps, args.nwalkers, 
         burnin = args.burnin,
         output_dir=args.output_dir)
