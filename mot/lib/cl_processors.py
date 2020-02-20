__author__ = 'Robbert Harms'
__date__ = '2020-01-25'
__maintainer__ = 'Robbert Harms'
__email__ = 'robbert@xkls.nl'
__licence__ = 'LGPL v3'

import pyopencl as cl


class Processor:

    def process(self, is_blocking=False, wait_for=None):
        """Enqueue all compute kernels for this processor.

        This may enqueue multiple kernels to multiple devices.

        Args:
            wait_for (Dict[CLEnvironment: cl.Event]): mapping CLEnvironments to events we should wait
                on before enqueuing work. This will wait on all events sharing the same context.
            is_blocking (boolean): if the call to the processor is a blocking call or not

        Returns:
            Dict[CLEnvironment: cl.Event]: events generated by this processor
        """
        raise NotImplementedError()

    def flush(self):
        """Enqueues a flush operation to all the queues."""
        raise NotImplementedError()

    def finish(self):
        """Enqueues a finish operation to all the queues."""
        raise NotImplementedError()


class MultiDeviceProcessor(Processor):

    def __init__(self, kernels, kernel_data, cl_environments, load_balancer,
                 nmr_instances, use_local_reduction=False, local_size=None):
        """Create a processor for the given function and inputs.

        Args:
            kernels (dict): for each CL environment the kernel to use
            kernel_data (dict): the input data for the kernels
            cl_environments (List[mot.lib.cl_environments.CLEnvironment]): the list of CL environment to use
                for executing the kernel
            load_balancer (mot.lib.load_balancers.LoadBalancer): the load balancer to use
            nmr_instances (int): the number of parallel processes to run.
            use_local_reduction (boolean): set this to True if you want to use local memory reduction in
                 evaluating this function. If this is set to True we will multiply the global size
                 (given by the nmr_instances) by the work group sizes.
            local_size (int): can be used to specify the exact local size (workgroup size) the kernel must use.
        """
        self._subprocessors = []
        self._kernel_data = kernel_data
        self._cl_environments = cl_environments

        batches = load_balancer.get_division(cl_environments, nmr_instances)
        for ind, cl_environment in enumerate(cl_environments):
            kernel = kernels[cl_environment]

            if use_local_reduction:
                if local_size:
                    workgroup_size = local_size
                else:
                    workgroup_size = kernel.get_work_group_info(
                        cl.kernel_work_group_info.PREFERRED_WORK_GROUP_SIZE_MULTIPLE, cl_environment.device)
            else:
                workgroup_size = 1

            batch_start, batch_end = batches[ind]
            if batch_end - batch_start > 0:
                processor = ProcessBatch(kernel, kernel_data.values(), cl_environment, batches[ind], workgroup_size)
                self._subprocessors.append(processor)

    def process(self, is_blocking=False, wait_for=None):
        events = {}
        for worker in self._subprocessors:
            events.update(worker.process(wait_for=wait_for))
            worker.flush()
        return events

    def flush(self):
        for worker in self._subprocessors:
            worker.flush()

    def finish(self):
        for worker in self._subprocessors:
            worker.finish()


class ProcessBatch(Processor):

    def __init__(self, kernel, kernel_data, cl_environment, batch_range, workgroup_size):
        """Simple processor which can execute the provided (compiled) kernel with the provided data.

        Args:
            kernel: a pyopencl compiled kernel program
            kernel_data (List[mot.lib.utils.KernelData]): the kernel data to load as input to the kernel
            cl_environment (mot.lib.cl_environments.CLEnvironment): the CL environment to use for executing the kernel
            batch_range (Tuple[int, int]): the batch start and batch end of the instances to process by this device.
            workgroup_size (int): the local size (workgroup size) the kernel must use
        """
        self._kernel = kernel
        self._kernel_data = kernel_data
        self._cl_environment = cl_environment
        self._batch_range = batch_range
        self._kernel.set_scalar_arg_dtypes(self._flatten_list([d.get_scalar_arg_dtypes() for d in self._kernel_data]))
        self._workgroup_size = workgroup_size

    def process(self, is_blocking=False, wait_for=None):
        kernel_inputs = []
        loading_events = []
        for data in self._kernel_data:
            inputs = data.get_kernel_inputs(self._cl_environment, self._workgroup_size,
                                            batch_range=self._batch_range, is_blocking=False, wait_for=wait_for)
            for kernel_input, event in inputs:
                kernel_inputs.append(kernel_input)
                if event is not None:
                    loading_events.append(event)

        nmr_instances = self._batch_range[1] - self._batch_range[0]

        event = self._kernel(
            self._cl_environment.queue,
            (int(nmr_instances * self._workgroup_size),),
            (int(self._workgroup_size),),
            *kernel_inputs,
            wait_for=loading_events)

        if is_blocking:
            event.wait()

        return {self._cl_environment: event}

    def flush(self):
        self._cl_environment.queue.flush()

    def finish(self):
        self._cl_environment.queue.finish()

    def _flatten_list(self, l):
        return_l = []
        for e in l:
            return_l.extend(e)
        return return_l
