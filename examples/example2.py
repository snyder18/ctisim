#!/usr/bin/env python
"""example2.py

This script is a worked example of creating a simulated flat field ITL CCD image.

To run this script, write

    python example2.py <template_file> <cti> <signal>

where <template_file> is the path to an existing ITL CCD image.  This is necessary
to capture all of the image metadata contained in the FITs files.  
"""
import argparse
from astropy.io import fits
from os.path import join

from ctisim import ITL_AMP_GEOM
from ctisim import ReadoutAmplifier, SerialRegister, ImageSimulator

def main(template_file, cti, signal, output_dir='./'):

    # Each segment needs it out ReadoutAmplifier and SerialRegister object.
    # For now they will all be the same.
    l = ITL_AMP_GEOM['ncols'] + ITL_AMP_GEOM['num_serial_prescan']
    readout_amplifiers = {amp : ReadoutAmplifier(6.5) for amp in range(1, 17)}
    serial_registers = {amp : SerialRegister(l, cti) for amp in range(1, 17)}

    # Create an ImageSimulator object given amplifier geometry dictionary and
    # dictionaries containing the ReadoutAmplifier and SerialRegister objects.
    imagesim = ImageSimulator.from_amp_geom(ITL_AMP_GEOM, readout_amplifiers,
                                            serial_registers)
    imagesim.flatfield_exp(signal)
    
    # Simulate the serial readout.
    # For a simulate image this always generates an output file.
    imarr_results = imagesim.serial_readout(template_file, 
                                            outfile=join(output_dir, 'example_image.fits'),
                                            overwrite=True)
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Simulate an LSST flat field image.')
    parser.add_argument('template_file', type=str, 
                        help='Path to existing ITL CCD FITs file.')
    parser.add_argument('cti', type=float,
                        help='Proportional loss from CTI.')
    parser.add_argument('signal', type=float, help='Flat field illumination signal [e-]')
    parser.add_argument('--output_dir', '-o', type=str, default='./',
                        help='Directory for output files.')
    args = parser.parse_args()

    template_file = args.template_file
    cti = args.cti
    signal = args.signal
    output_dir = args.output_dir

    main(template_file, cti, signal, output_dir=output_dir)

    
