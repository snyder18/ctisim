import argparse
import numpy as np
import os
from os.path import join
import pickle
import scipy.interpolate as interp
from astropy.io import fits
from lmfit import Minimizer, Parameters

from ctisim import ITL_AMP_GEOM, LinearTrap, SplineTrap
from ctisim.fitting import SimpleModel, SimulatedModel
from ctisim.utils import OverscanParameterResults

def main(raft_id, directory):

    sensor_names = ['S00', 'S01', 'S02',
                    'S10', 'S11', 'S12',
                    'S20', 'S21', 'S22']

    for sensor_name in sensor_names:
        sensor_id = '{0}_{1}'.format(raft_id, sensor_name)
        print("Starting sensor {0}".format(sensor_id))

        try:

            ####
            ##
            ## Fit Local Electronic Offset Effect
            ##
            ####

            ## Config variables
            start = 3
            stop = 13
            max_signal = 150000.
            error = 7.0/np.sqrt(2000.)

            ## Get existing overscan analysis results
            hdulist = fits.open(join(directory, raft_id, sensor_name,
                                     '{0}_overscan_results.fits'.format(sensor_id)))

            cti_results = {i : 0.0 for i in range(1, 17)}
            drift_scales = {i : 0.0 for i in range(1, 17)}
            decay_times = {i : 0.0 for i in range(1, 17)}

            ## CCD geometry info
            ncols = ITL_AMP_GEOM.nx + ITL_AMP_GEOM.prescan_width

            for amp in range(1, 17):

                ## Signals
                all_signals = hdulist[amp].data['FLATFIELD_SIGNAL']
                signals = all_signals[all_signals<max_signal]

                ## Data
                data = hdulist[amp].data['COLUMN_MEAN'][all_signals<max_signal, 
                                                        start:stop+1]

                params = Parameters()
                params.add('ctiexp', value=-6, min=-7, max=-5, vary=False)
                params.add('trapsize', value=0.0, min=0., max=10., vary=False)
                params.add('scaling', value=0.08, min=0, max=1.0, vary=False)
                params.add('emissiontime', value=0.4, min=0.1, max=1.0, vary=False)
                params.add('driftscale', value=0.00022, min=0., max=0.001)
                params.add('decaytime', value=2.4, min=0.1, max=4.0)

                model = SimpleModel()

                minner = Minimizer(model.difference, params, 
                                   fcn_args=(signals, data, error, ncols),
                                   fcn_kws={'start' : start, 'stop' : stop})
                result = minner.minimize()

                if result.success:

                    cti = 10**result.params['ctiexp']
                    drift_scale = result.params['driftscale']
                    decay_time = result.params['decaytime']
                    cti_results[amp] = cti
                    drift_scales[amp] = drift_scale.value
                    decay_times[amp] = decay_time.value

                else:
                    print("Electronics fitting failure: Amp{0}".format(amp))
                    cti = 10**result.params['ctiexp']
                    cti_results[amp] = cti
                    drift_scales[amp] = 0.0
                    decay_times[amp] = 2.4

            param_results = OverscanParameterResults(sensor_id, 
                                                     cti_results, 
                                                     drift_scales, 
                                                     decay_times)

            ####
            ##
            ## Fit Global CTI
            ##
            ####

            start = 1
            stop = 2
            max_signal = 10000.
            error = 7.0/np.sqrt(2000.)
            num_transfers = ITL_AMP_GEOM.nx + ITL_AMP_GEOM.prescan_width

            cti_results = {amp : 0.0 for amp in range(1, 17)}
            drift_scales = param_results.drift_scales
            decay_times = param_results.decay_times

            ncols = ITL_AMP_GEOM.nx + ITL_AMP_GEOM.prescan_width

            for amp in range(1, 17):

                ## Signals
                all_signals = hdulist[amp].data['FLATFIELD_SIGNAL']
                signals = all_signals[all_signals<max_signal]

                ## Data
                data = hdulist[amp].data['COLUMN_MEAN'][all_signals<max_signal, start:stop+1]

                ## CTI test
                lastpixel = signals
                overscan1 = data[:, 0]
                overscan2 = data[:, 1]
                test = (overscan1+overscan2)/(ncols*lastpixel)

                if np.median(test) > 5.E-6:

                    params = Parameters()
                    params.add('ctiexp', value=-6, min=-7, max=-5, vary=True)
                    params.add('trapsize', value=5.0, min=0., max=30., vary=True)
                    params.add('scaling', value=0.08, min=0, max=1.0, vary=True)
                    params.add('emissiontime', value=0.35, min=0.1, max=1.0, vary=True)
                    params.add('driftscale', value=drift_scales[amp], min=0., max=0.001, vary=False)
                    params.add('decaytime', value=decay_times[amp], min=0.1, max=4.0, vary=False)

                    model = SimulatedModel()
                    minner = Minimizer(model.difference, params, 
                                       fcn_args=(signals, data, error, num_transfers, ITL_AMP_GEOM),
                                       fcn_kws={'start' : start, 'stop' : stop, 'trap_type' : 'linear'})
                    result = minner.minimize()

                else:

                    params = Parameters()
                    params.add('ctiexp', value=-6, min=-7, max=-5, vary=True)
                    params.add('trapsize', value=0.0, min=0., max=10., vary=False)
                    params.add('scaling', value=0.08, min=0, max=1.0, vary=False)
                    params.add('emissiontime', value=0.35, min=0.1, max=1.0, vary=False)
                    params.add('driftscale', value=drift_scales[amp], min=0., max=0.001, vary=False)
                    params.add('decaytime', value=decay_times[amp], min=0.1, max=4.0, vary=False)

                    model = SimulatedModel()
                    minner = Minimizer(model.difference, params, 
                                       fcn_args=(signals, data, error, num_transfers, ITL_AMP_GEOM),
                                       fcn_kws={'start' : start, 'stop' : stop, 'trap_type' : 'linear'})
                    result = minner.minimize()

                cti_results[amp] = 10**result.params['ctiexp'].value

            param_results.cti_results = cti_results
            outfile = join(directory, raft_id, sensor_name,
                           '{0}_parameter_results.fits'.format(sensor_id))
            param_results.write_fits(outfile, overwrite=True)

            ####
            ##
            ## Determine Localized Trapping
            ##
            ####

            start = 1
            stop = 20
            max_signal = 150000.

            for amp in range(1, 17):

                ## Signals
                all_signals = hdulist[amp].data['FLATFIELD_SIGNAL']
                signals = all_signals[all_signals<max_signal]

                ## Data
                data = hdulist[amp].data['COLUMN_MEAN'][all_signals<max_signal, start:stop+1]

                ## Second model: model with electronics
                params = Parameters()
                params.add('ctiexp', value=np.log10(param_results.cti_results[amp]), 
                           min=-7, max=-4, vary=False)
                params.add('trapsize', value=0.0, min=0., max=10., vary=False)
                params.add('scaling', value=0.08, min=0, max=1.0, vary=False)
                params.add('emissiontime', value=0.35, min=0.1, max=1.0, vary=False)
                params.add('driftscale', value=param_results.drift_scales[amp], 
                           min=0., max=0.001, vary=False)
                params.add('decaytime', value=param_results.decay_times[amp], 
                           min=0.1, max=4.0, vary=False)
                model = SimpleModel.model_results(params,signals, num_transfers, 
                                                  start=start, stop=stop)

                res = np.sum((data-model)[:, :3], axis=1)
                new_signals = hdulist[amp].data['COLUMN_MEAN'][all_signals<max_signal, 0]
                rescale = param_results.drift_scales[amp]*new_signals
                new_signals = np.asarray(new_signals - rescale, dtype=np.float64)
                x = new_signals
                y = np.maximum(0, res)

                # Pad left with ramp
                y = np.pad(y, (10, 0), 'linear_ramp', end_values=(0, 0))
                x = np.pad(x, (10, 0), 'linear_ramp', end_values=(0, 0))

                # Pad right with constant
                y = np.pad(y, (1, 1), 'constant', constant_values=(0, y[-1]))
                x = np.pad(x, (1, 1), 'constant', constant_values=(-1, 200000.))

                f = interp.interp1d(x, y)
                spltrap = SplineTrap(f, 0.4, 1)
                pickle.dump(spltrap, open(join(directory, raft_id, sensor_name,
                                               '{0}_amp{1}_trap.pkl'.format(sensor_id, amp)), 'wb'))

            hdulist.close()

        except Exception as e:
            print("Error occurred for {0}!".format(sensor_id))
            print(e)
            continue

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('raft_id', type=str, 
                        help='Sensor identifier, e.g. R02_S02')
    parser.add_argument('directory', type=str, 
                        help='Directory holding sensor overscan FITs data subdirectories.')
    args = parser.parse_args()

    main(args.raft_id, args.directory)
