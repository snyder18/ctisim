#!/usr/bin/env python
"""example2.py

This script is a worked example of creating a simulated flat field ITL CCD image.
Proportional loss from CTI occuring at each pixel transfer is simulated.

To run this script, write

    python example2.py <template_file> <cti> <signal> --output_dir <output_dir>

where <template_file> is the path to an existing ITL CCD image, <cti> is the 
desired value for CTI, and <signal> is the desired flat field signal.  An 
optional argument, <output_dir>, can be provided for a path to a desired directory
to output the resulting files.
   
A template file is necessary to capture all of the image metadata contained 
in true LSST image FITs files.  An example ITL image file is proved:
     
    ITL_image_example.fits

The new class usages demonstrated are:
    * ImageSimulator(shape, num_serial_prescan, num_serial_overscan, 
                     num_parallel_overscan, readout_amplifiers, serial_registers)

The ImageSimulator class serves as a broader class to hold the necessary
objects and attributes for each of the 16 segments in an LSST CCD.  Within
the class, SegmentSimulator objects are constructed and used to simulate
the serial readout for each segment individually.  
"""
import argparse
from astropy.io import fits
from os.path import join

from ctisim import ITL_AMP_GEOM
from ctisim import BaseOutputAmplifier, ImageSimulator

def main(template_file, cti, signal, output_dir='./output'):

    # Each segment needs its own ReadoutAmplifier and SerialRegister object.
    # For this example they will all be the same.
    output_amplifiers = {amp : BaseOutputAmplifier(1.0, noise=6.5) for amp in range(1, 17)}
    cti = {amp : cti for amp in range(1, 17)}

    # Create an ImageSimulator object given amplifier geometry dictionary and
    # dictionaries containing the ReadoutAmplifier and SerialRegister objects.
    print("Simulating flat field image with signal: {0:.1f} electrons".format(signal))
    imagesim = ImageSimulator.from_amp_geom(ITL_AMP_GEOM, output_amplifiers, cti=cti)
    imagesim.flatfield_exp(signal)
    
    # Simulate the serial readout.
    # For a simulate image this always generates an output file.
    print("Simulating readout with CTI: {0:.1E}".format(cti))
    outfile = join(output_dir, 'example_image.fits')
    imarr_results = imagesim.image_readout(template_file, 
                                           outfile=join(output_dir, 'example2_image.fits'))    
    print("Output file: {0}".format(outfile))
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Simulate an LSST flat field image.')
    parser.add_argument('template_file', type=str, 
                        help='Path to existing ITL CCD FITs file.')
    parser.add_argument('cti', type=float, help='Proportional loss from CTI.')
    parser.add_argument('signal', type=float, help='Flat field illumination signal [e-]')
    parser.add_argument('--output_dir', '-o', type=str, default='./output',
                        help='Directory for output files.')
    args = parser.parse_args()

    template_file = args.template_file
    cti = args.cti
    signal = args.signal
    output_dir = args.output_dir

    main(template_file, cti, signal, output_dir=output_dir)
