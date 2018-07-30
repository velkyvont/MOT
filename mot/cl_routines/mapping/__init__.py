from mot.cl_function import SimpleCLFunction
from mot.kernel_data import KernelArray, KernelAllocatedArray, KernelScalar, KernelLocalMemory


__author__ = 'Robbert Harms'
__date__ = "2014-05-21"
__license__ = "LGPL v3"
__maintainer__ = "Robbert Harms"
__email__ = "robbert.harms@maastrichtuniversity.nl"


def compute_log_likelihood(model, parameters, cl_runtime_info=None):
    """Calculate and return the log likelihood of the given model for the given parameters.

    This calculates the log likelihoods for every problem in the model (typically after optimization),
    or a log likelihood for every sample of every model (typically after sampling). In the case of the first (after
    optimization), the parameters must be an (d, p) array for d problems and p parameters. In the case of the
    second (after sampling), you must provide this function with a matrix of shape (d, p, n) with d problems,
    p parameters and n samples.

    Args:
        model (AbstractModel): The model to calculate the full log likelihood for.
        parameters (ndarray): The parameters to use in the evaluation of the model. This is either an (d, p) matrix
            or (d, p, n) matrix with d problems, p parameters and n samples.
        cl_runtime_info (mot.cl_runtime_info.CLRuntimeInfo): the runtime information

    Returns:
        ndarray: per problem the log likelihood, or, per problem and per sample the log likelihood.
    """

    def get_cl_function():
        ll_func = model.get_log_likelihood_per_observation_function()
        nmr_params = parameters.shape[1]

        ll_tmp_func = SimpleCLFunction.from_string('''
            void _fill_log_likelihood_tmp(mot_data_struct* data,
                                          mot_float_type* x,
                                          local double* log_likelihood_tmp){

                ulong observation_ind;
                ulong local_id = get_local_id(0);
                log_likelihood_tmp[local_id] = 0;
                uint workgroup_size = get_local_size(0);
                uint elements_for_workitem = ceil(''' + str(model.get_nmr_observations()) + ''' 
                                                  / (mot_float_type)workgroup_size);

                if(workgroup_size * (elements_for_workitem - 1) + local_id 
                        >= ''' + str(model.get_nmr_observations()) + '''){
                    elements_for_workitem -= 1;
                }

                for(uint i = 0; i < elements_for_workitem; i++){
                    observation_ind = i * workgroup_size + local_id;

                    log_likelihood_tmp[local_id] += ''' + ll_func.get_cl_function_name() + '''(
                        data, x, observation_ind);
                }

                barrier(CLK_LOCAL_MEM_FENCE);
            }
        ''', dependencies=[ll_func])

        ll_sum_func = SimpleCLFunction.from_string('''
            double _sum_log_likelihood_tmp(local double* log_likelihood_tmp){
                double ll = 0;
                for(uint i = 0; i < get_local_size(0); i++){
                    ll += log_likelihood_tmp[i];
                }
                return ll;
            }
        ''')

        if len(parameters.shape) > 2:
            return SimpleCLFunction.from_string('''
                void compute(mot_data_struct* data){
                    mot_float_type x[''' + str(nmr_params) + '''];

                    for(uint sample_ind = 0; sample_ind < ''' + str(parameters.shape[2]) + '''; sample_ind++){
                        for(uint i = 0; i < ''' + str(nmr_params) + '''; i++){
                            x[i] = data->parameters[i *''' + str(parameters.shape[2]) + ''' + sample_ind];
                        }

                        _fill_log_likelihood_tmp(data, x, data->local_reduction_lls);
                        if(get_local_id(0) == 0){
                            data->log_likelihoods[sample_ind] = _sum_log_likelihood_tmp(data->local_reduction_lls);
                        }
                    }
                }
            ''', dependencies=[ll_tmp_func, ll_sum_func])

        return SimpleCLFunction.from_string('''
            void compute(mot_data_struct* data){
                mot_float_type x[''' + str(nmr_params) + '''];
                for(uint i = 0; i < ''' + str(nmr_params) + '''; i++){
                    x[i] = data->parameters[i];
                }

                _fill_log_likelihood_tmp(data, x, data->local_reduction_lls);
                if(get_local_id(0) == 0){
                    *(data->log_likelihoods) = _sum_log_likelihood_tmp(data->local_reduction_lls);
                }
            }
        ''', dependencies=[ll_tmp_func, ll_sum_func])

    all_kernel_data = dict(model.get_kernel_data())
    all_kernel_data['parameters'] = KernelArray(parameters)

    shape = parameters.shape
    if len(shape) > 2:
        all_kernel_data.update({
            'log_likelihoods': KernelAllocatedArray((shape[0], shape[2]), 'mot_float_type'),
            'nmr_params': KernelScalar(parameters.shape[1]),
            'nmr_samples': KernelScalar(parameters.shape[2]),
            'local_reduction_lls': KernelLocalMemory('double')
        })
    else:
        all_kernel_data.update({
            'log_likelihoods': KernelAllocatedArray((shape[0],), 'mot_float_type'),
            'local_reduction_lls': KernelLocalMemory('double')
        })

    get_cl_function().evaluate({'data': all_kernel_data}, nmr_instances=parameters.shape[0], use_local_reduction=True,
                               cl_runtime_info=cl_runtime_info)

    return all_kernel_data['log_likelihoods'].get_data()


def compute_objective_value(model, parameters, cl_runtime_info=None):
    """Calculate and return the objective function value of the given model for the given parameters.

    Args:
        model (AbstractModel): The model to calculate the objective function for
        parameters (ndarray): The parameters to use in the evaluation of the model, an (d, p) matrix
            with d problems and p parameters.
        cl_runtime_info (mot.cl_runtime_info.CLRuntimeInfo): the runtime information

    Returns:
        ndarray: vector matrix with per problem the objective function value
    """
    objective_func = model.get_objective_function()
    nmr_params = parameters.shape[1]

    cl_function = SimpleCLFunction.from_string('''
        void compute(mot_data_struct* data){
            mot_float_type x[''' + str(nmr_params) + '''];
            for(uint i = 0; i < ''' + str(nmr_params) + '''; i++){
                x[i] = data->parameters[i];
            }

            double objective = ''' + objective_func.get_cl_function_name() + '''(
                data, x, 0, 0, data->local_reduction_lls);

            if(get_local_id(0) == 0){
                *(data->objective_values) = objective;
            }
       }
   ''', dependencies=[objective_func])

    all_kernel_data = dict(model.get_kernel_data())
    all_kernel_data.update({
        'parameters': KernelArray(parameters),
        'objective_values': KernelAllocatedArray((parameters.shape[0],), 'mot_float_type'),
        'local_reduction_lls': KernelLocalMemory('double')
    })

    cl_function.evaluate({'data': all_kernel_data}, nmr_instances=parameters.shape[0],
                         use_local_reduction=True, cl_runtime_info=cl_runtime_info)

    return all_kernel_data['objective_values'].get_data()

