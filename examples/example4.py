from ctisim import ImageSimulator, OutputAmplifier
from ctisim.utils import calculate_cti
import argparse
import numpy as np
from os.path import join

import time

def main(infile, bias_frame=None, output_dir='./'):

    output_amplifiers = {amp : OutputAmplifier(1.0, 6.5) for amp in range(1, 17)}
    cti_dict = {amp : 10**(np.random.normal(-5.8, scale=0.1, size=1))[0] for amp in range(1, 17)}
    
    image = ImageSimulator.image_from_fits(infile, output_amplifiers, cti_dict=cti_dict, 
                                           bias_frame=bias_frame)

    a = time.time()
    imarr_results = image.simulate_readout(infile, 
                                           outfile=join(output_dir, 'example_image.fits'),
                                           do_bias_drift=False)
    b = time.time()
    print(b-a)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Demonstrate simulated readout on existing images.')
    parser.add_argument('infile', type=str, help='Existing image to use.')
    parser.add_argument('--bias_frame', '-b', type=str, default=None,
                        help='Bias frame for bias correction.')
    parser.add_argument('--output_dir', '-o', type=str, default='./',
                        help='Directory for output files.')  
    args = parser.parse_args()

    infile = args.infile
    bias_frame = args.bias_frame
    output_dir = args.output_dir

    main(infile, bias_frame=bias_frame, output_dir=output_dir)
