from .cl_environments import CLEnvironmentFactory
from .load_balance_strategies import PreferGPU

__author__ = 'Robbert Harms'
__date__ = "2015-07-22"
__maintainer__ = "Robbert Harms"
__email__ = "robbert.harms@maastrichtuniversity.nl"


"""The default cl_environment and load balancer to use. They can be overwritten at run time.

The problem this solves is the following. During optimization we run user defined scripts in the Model definition (
for example during the post optimization function). If a user accelerates the calculations using OpenCL it needs to know
the device preferences we have.

It is a matter of reducing message passing, if we want to run all calculations one one specific device we need some way
of telling the user scripts which devices it should use. This would either involve a lot of message passing or a global
variable.

We require that all CL routines are instantiated with the CL environment and the load balancer to use. If they are not
known from the context defaults can be obtained from this module.

"""
runtime_config = {
    'cl_environments': CLEnvironmentFactory.all_devices(),
    'load_balancer': PreferGPU(),
}