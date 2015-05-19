import os
from pkg_resources import resource_filename
from .base import LibraryFunction, LibraryParameter, FreeParameter
from pppe.base import CLDataType, ModelFunction
from pppe.parameter_functions.proposals import GaussianProposal
from pppe.parameter_functions.transformations import ClampTransform, CosSqrTransform


__author__ = 'Robbert Harms'
__date__ = "2014-05-12"
__license__ = "LGPL v3"
__maintainer__ = "Robbert Harms"
__email__ = "robbert.harms@maastrichtuniversity.nl"


class EuclidianNormFunction(LibraryFunction):

    def __init__(self, memspace='private'):
        """A CL functions for calculating the Euclidian distance between n values.

        Args:
            memspace (str): The memory space of the double array (private, constant, global).
        """
        super(EuclidianNormFunction, self).__init__(
            'double',
            'euclidian_norm_' + memspace,
            (LibraryParameter(CLDataType.from_string('double*'), 'x'),
             LibraryParameter(CLDataType.from_string('int'), 'n')),
            resource_filename('pppe', 'data/opencl/euclidian_norm.ph'),
            resource_filename('pppe', 'data/opencl/euclidian_norm.pcl'),
            {'MEMSPACE': memspace},
            ())


class LMMin(LibraryFunction):

    def __init__(self, nmr_parameters, patience=250):
        """The Levenberg Marquardt function.

        Args:
            nmr_parameters (int): The number of parameters we are going to optimize, this is compiled into the code.
            patience (int): The patience before stopping the iterations.
        """
        euclid = EuclidianNormFunction(memspace='private')
        super(LMMin, self).__init__(
            'void',
            'lmmin',
            (LibraryParameter(CLDataType.from_string('double*'), 'x'),
             LibraryParameter(CLDataType.from_string('void*'), 'data')),
            resource_filename('pppe', 'data/opencl/lmmin.h'),
            resource_filename('pppe', 'data/opencl/lmmin.pcl'),
            {'EUCLIDIAN_FUNC': euclid.cl_function_name, 'NMR_PARAMS': nmr_parameters, 'PATIENCE': patience},
            (euclid,))


class NMSimplexFunc(LibraryFunction):

    def __init__(self, nmr_parameters, patience=250):
        """The Nelder-Mead simplex function.

        Args:
            nmr_parameters (int): The number of parameters we are going to optimize, this is compiled into the code.
            patience (int): The patience before stopping the iterations.
        """
        super(NMSimplexFunc, self).__init__(
            'void',
            'nmsimplex',
            (LibraryParameter(CLDataType.from_string('double*'), 'x'),
             LibraryParameter(CLDataType.from_string('void*'), 'data')),
            resource_filename('pppe', 'data/opencl/nmsimplex.h'),
            resource_filename('pppe', 'data/opencl/nmsimplex.pcl'),
            {'NMR_PARAMS': nmr_parameters, 'PATIENCE': patience},
            ())


class PowellFunc(LibraryFunction):

    def __init__(self, nmr_parameters, patience=150):
        """The Powell function.

        Args:
            nmr_parameters (int): The number of parameters we are going to optimize, this is compiled into the code.
            patience (int): The patience before stopping the iterations.
        """
        super(PowellFunc, self).__init__(
            'void',
            'powell',
            (LibraryParameter(CLDataType.from_string('double*'), 'x'),
             LibraryParameter(CLDataType.from_string('void*'), 'data')),
            resource_filename('pppe', 'data/opencl/powell.h'),
            resource_filename('pppe', 'data/opencl/powell.pcl'),
            {'NMR_PARAMS': nmr_parameters, 'PATIENCE': patience},
            ())


class SpreadWeights(LibraryFunction):

    def __init__(self, memspace='private'):
        """A function for spreading n-1 weights to n weights ensuring the sum equals 1.

        Args:
            memspace (str): The memory space of the double array (private, constant, global).
        """
        super(SpreadWeights, self).__init__(
            'void',
            'spread_weights_' + memspace,
            (LibraryParameter(CLDataType.from_string('double*'), 'x'),
             LibraryParameter(CLDataType.from_string('int'), 'n')),
            resource_filename('pppe', 'data/opencl/spread_weights.ph'),
            resource_filename('pppe', 'data/opencl/spread_weights.pcl'),
            {'MEMSPACE': memspace},
            ())


class KahanSummation(LibraryFunction):

    def __init__(self, memspace='private'):
        """A function for summing an array of doubles without to much loss of precision.

        Args:
            memspace (str): The memory space of the double array (private, constant, global).
        """
        super(KahanSummation, self).__init__(
            'void',
            'kahan_summation_' + memspace,
            (LibraryParameter(CLDataType.from_string('double*'), 'l'),
             LibraryParameter(CLDataType.from_string('int'), 'n')),
            resource_filename('pppe', 'data/opencl/kahan_summation.ph'),
            resource_filename('pppe', 'data/opencl/kahan_summation.pcl'),
            {'MEMSPACE': memspace},
            ())


class FirstLegendreTerm(LibraryFunction):

    def __init__(self):
        """A function for finding the first legendre term. (see the CL code for more details)
        """
        super(FirstLegendreTerm, self).__init__(
            'double',
            'getFirstLegendreTerm',
            (LibraryParameter(CLDataType.from_string('double'), 'x'),
             LibraryParameter(CLDataType.from_string('int'), 'n')),
            resource_filename('pppe', 'data/opencl/firstLegendreTerm.h'),
            resource_filename('pppe', 'data/opencl/firstLegendreTerm.cl'),
            {},
            ())


class RanluxCL(LibraryFunction):

    def __init__(self):
        """A function for generating random numbers. (see the CL code for more details)
        """
        super(RanluxCL, self).__init__(
            'float4',
            'ranluxcl',
            (LibraryParameter(CLDataType.from_string('ranluxcl_state_t*'), 'ranluxclstate'), ),
            resource_filename('pppe', 'data/opencl/ranluxcl.h'),
            resource_filename('pppe', 'data/opencl/ranluxcl.cl'),
            {},
            ())


class MCMCStretch(LibraryFunction):

    def __init__(self):
        """The MCMC stretch sampler definition. (see the CL code for more details)
        """
        super(MCMCStretch, self).__init__(
            'void',
            'mcmc_stretch',
            (LibraryParameter(CLDataType.from_string('float*'), 'X_moving'),
             LibraryParameter(CLDataType.from_string('float*'), 'log_prob_moving'),
             LibraryParameter(CLDataType.from_string('float*'), 'X_fixed'),
             LibraryParameter(CLDataType.from_string('float4*'), 'ranluxcltab'),
             LibraryParameter(CLDataType.from_string('long*'), 'accepted'),
             LibraryParameter(CLDataType.from_string('void*'), 'data'),
             LibraryParameter(CLDataType.from_string('float'), 'beta')),
            resource_filename('pppe', 'data/opencl/mcmc_stretch.h'),
            resource_filename('pppe', 'data/opencl/mcmc_stretch.cl'),
            {},
            ())


class CerfImWOfX(LibraryFunction):

    def __init__(self):
        """Calculate the cerf. (see the CL code for more details)
        """
        super(CerfImWOfX, self).__init__(
            'double',
            'im_w_of_x',
            (LibraryParameter(CLDataType.from_string('double'), 'x'), ),
            resource_filename('pppe', 'data/opencl/cerf/im_w_of_x.h'),
            resource_filename('pppe', 'data/opencl/cerf/im_w_of_x.cl'),
            {},
            ())


class CerfDawson(LibraryFunction):

    def __init__(self):
        """Evaluate dawson integral. (see the CL code for more details)
        """
        super(CerfDawson, self).__init__(
            'double',
            'dawson',
            (LibraryParameter(CLDataType.from_string('double'), 'x'), ),
            resource_filename('pppe', 'data/opencl/cerf/dawson.h'),
            resource_filename('pppe', 'data/opencl/cerf/dawson.cl'),
            {},
            (CerfImWOfX(),))


class CerfErfi(LibraryFunction):

    def __init__(self):
        """Calculate erfi. (see the CL code for more details)
        """
        super(CerfErfi, self).__init__(
            'double',
            'erfi',
            (LibraryParameter(CLDataType.from_string('double'), 'x'), ),
            resource_filename('pppe', 'data/opencl/cerf/erfi.h'),
            resource_filename('pppe', 'data/opencl/cerf/erfi.cl'),
            {},
            (CerfImWOfX(),))


class Scalar(ModelFunction):

    def __init__(self, name='Scalar', value=0.0, lower_bound=0.0, upper_bound=float('inf')):
        """A Scalar model function to be used during optimization.

        Args:
            name (str): The name of the model
            value (number or ndarray): The initial value for the single free parameter of this function.
            lower_bound (number or ndarray): The initial lower bound for the single free parameter of this function.
            upper_bound (number or ndarray): The initial upper bound for the single free parameter of this function.
        """
        super(Scalar, self).__init__(
            name,
            'cmScalar',
            (FreeParameter(CLDataType.from_string('double'), 's', False, value, lower_bound, upper_bound,
                           parameter_transform=ClampTransform(),
                           sampling_proposal=GaussianProposal(1.0)),))

    def get_cl_header(self):
        """See base class for details"""
        path = resource_filename('pppe', 'data/opencl/modelFunctions/Scalar.h')
        return self._get_cl_dependency_headers() + "\n" + open(os.path.abspath(path), 'r').read()

    def get_cl_code(self):
        """See base class for details"""
        path = resource_filename('pppe', 'data/opencl/modelFunctions/Scalar.cl')
        return self._get_cl_dependency_code() + "\n" + open(os.path.abspath(path), 'r').read()


class Weight(Scalar):

    def __init__(self, name='Weight', value=0.5, lower_bound=0.0, upper_bound=1.0):
        """Implements Scalar model function to add the semantics of representing a Weight.

        Some of the code checks for type Weight, be sure to use this model function if you want to represent a Weight.

        A weight is meant to be a model fraction.

        Args:
            name (str): The name of the model
            value (number or ndarray): The initial value for the single free parameter of this function.
            lower_bound (number or ndarray): The initial lower bound for the single free parameter of this function.
            upper_bound (number or ndarray): The initial upper bound for the single free parameter of this function.
        """
        super(Weight, self).__init__(name=name, value=value, lower_bound=lower_bound, upper_bound=upper_bound)
        self.parameter_list[0].name = 'w'
        self.parameter_list[0].parameter_transform = CosSqrTransform()
        self.parameter_list[0].sampling_proposal = GaussianProposal(0.00001)