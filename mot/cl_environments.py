import pyopencl as cl
from six import string_types
from .utils import device_supports_double, device_type_from_string

__author__ = 'Robbert Harms'
__date__ = "2014-11-14"
__license__ = "LGPL v3"
__maintainer__ = "Robbert Harms"
__email__ = "robbert.harms@maastrichtuniversity.nl"


class CLEnvironment(object):

    def __init__(self, platform, device, context=None, compile_flags=()):
        """Storage unit for an OpenCL environment.

        Args:
            platform (pyopencl platform): An PyOpenCL platform.
            device (pyopencl device): An PyOpenCL device
            context (pyopencl context): An PyOpenCL context
            compile_flags (list of str): A list of strings with compile flags (see the OpenCL specifications)

        Attributes:
            compile_flags (list of str): A list of strings with compile flags (see the OpenCL specifications)
        """
        self._platform = platform
        self._device = device
        self._context = context
        self.compile_flags = compile_flags

        if not self._context:
            self._context = cl.Context([self._device])

    def get_new_queue(self):
        """Create and return a new command queue

        Returns:
            CommandQueue: A command queue from PyOpenCL
        """
        return cl.CommandQueue(self._context, device=self._device)

    def get_read_only_cl_mem_flags(self):
        """Get the read only memory flags for this environment.

        Returns:
            int: CL integer representing the memory flags to use.
        """
        if self.is_gpu:
            return cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR
        else:
            return cl.mem_flags.READ_ONLY | cl.mem_flags.USE_HOST_PTR

    def get_read_write_cl_mem_flags(self):
        """Get the read write memory flags for this environment.

        Returns:
            int: CL integer representing the memory flags to use.
        """
        if self.is_gpu:
            return cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR
        else:
            return cl.mem_flags.READ_WRITE | cl.mem_flags.USE_HOST_PTR

    def get_write_only_cl_mem_flags(self):
        """Get the write only memory flags for this environment.

        Returns:
            int: CL integer representing the memory flags to use.
        """
        if self.is_gpu:
            return cl.mem_flags.WRITE_ONLY | cl.mem_flags.COPY_HOST_PTR
        else:
            return cl.mem_flags.WRITE_ONLY | cl.mem_flags.USE_HOST_PTR

    @property
    def supports_double(self):
        """Check if the device listed by this environment supports double

        Returns:
            boolean: True if the device supports double, false otherwise.
        """
        return device_supports_double(self.device)

    @property
    def platform(self):
        """Get the platform associated with this environment.

        Returns:
            pyopencl platform: The platform associated with this environment.
        """
        return self._platform

    @property
    def device(self):
        """Get the device associated with this environment.

        Returns:
            pyopencl device: The device associated with this environment.
        """
        return self._device

    @property
    def context(self):
        """Get the context associated with this environment.

        Returns:
            pyopencl context: The context associated with this environment.
        """
        return self._context

    @property
    def is_gpu(self):
        """Check if the device associated with this environment is a GPU.

        Returns:
            boolean: True if the device is an GPU, false otherwise.
        """
        return self._device.get_info(cl.device_info.TYPE) == cl.device_type.GPU

    @property
    def is_cpu(self):
        """Check if the device associated with this environment is a CPU.

        Returns:
            boolean: True if the device is an CPU, false otherwise.
        """
        return self._device.get_info(cl.device_info.TYPE) == cl.device_type.CPU

    @property
    def device_type(self):
        """Get the device type of the device in this environment.

        Returns:
            the device type of this device.
        """
        return self._device.get_info(cl.device_info.TYPE)

    def __str__(self):
        s = 'GPU' if self.is_gpu else 'CPU'
        s += ' - ' + self.device.name + ' (' + self.platform.name + ')'
        return s

    def __repr__(self):
        s = 75*"=" + "\n"
        s += repr(self._platform) + "\n"
        s += 75*"=" + "\n"
        s += self._print_info(self._platform, cl.platform_info)

        s += 75*"-" + "\n"
        s += repr(self._device) + "\n"
        s += 75*"-" + "\n"
        s += self._print_info(self._device, cl.device_info)

        return s

    def _print_info(self, obj, info_cls):
        s = ''

        def format_title(title_str):
            title_str = title_str.lower()
            title_str = title_str.replace('_', ' ')
            return title_str

        for info_name in sorted(dir(info_cls)):
            if not info_name.startswith("_") and info_name != "to_string":
                info = getattr(info_cls, info_name)

                try:
                    info_value = obj.get_info(info)
                except cl.LogicError:
                    info_value = "<error>"

                if info_cls == cl.device_info and info_name == "PARTITION_TYPES_EXT" and isinstance(info_value, list):
                    prop_value = [cl.device_partition_property_ext.to_string(v, "<unknown device "
                                                                                "partition property %d>")
                                  for v in info_value]

                    s += ("%s: %s" % (format_title(info_name), prop_value)) + "\n"
                else:
                    try:
                        s += ("%s: %s" % (format_title(info_name), info_value)) + "\n"
                    except cl.LogicError:
                        s += ("%s: <error>" % info_name) + "\n"
        s += "\n"
        return s


class CLEnvironmentFactory(object):

    @staticmethod
    def single_device(cl_device_type=cl.device_type.GPU, platform=None, compile_flags=(),
                      fallback_to_any_device_type=False):
        """Get a list containing a single device environment, for a device of the given type on the given platform.

        This will only fetch devices that support double (possibly only double with a pragma
        defined, but still, it should support double).

        Args:
            cl_device_type (cl.device_type.* or string): The type of the device we want,
                can be a opencl device type or a string matching 'GPU', 'CPU' or 'ALL'.
            platform (opencl platform): The opencl platform to select the devices from
            compile_flags (list of str): A tuple with compile flags to use for this device / context.
            fallback_to_any_device_type (boolean): If True, try to fallback to any possible device in the system.

        Returns:
            list of CLEnvironment: List with one element, the CL runtime environment requested.
        """
        if isinstance(cl_device_type, string_types):
            cl_device_type = device_type_from_string(cl_device_type)

        if platform is None:
            platform = cl.get_platforms()[0]

        devices = platform.get_devices(device_type=cl_device_type)
        if not devices:
            if fallback_to_any_device_type:
                devices = platform.get_devices()
            else:
                raise ValueError('No devices of the specified type ({}) found.'.format(
                    cl.device_type.to_string(cl_device_type)))

        for dev in devices:
            if device_supports_double(dev):
                try:
                    env = CLEnvironment(platform, dev, compile_flags=compile_flags)
                    return [env]
                except cl.RuntimeError:
                    pass

        raise ValueError('No suitable OpenCL device found.')

    @staticmethod
    def all_devices(cl_device_type=None, platform=None, compile_flags=()):
        """Get multiple device environments, optionally only of the indicated type.

        This will only fetch devices that support double (possibly only devices
        with a pragma defined, but still it should support double).

        Args:
            cl_device_type (cl.device_type.* or string): The type of the device we want,
                can be a opencl device type or a string matching 'GPU' or 'CPU'.
            platform (opencl platform): The opencl platform to select the devices from
            compile_flags (list of str): A tuple with compile flags to use for this device / context.

        Returns:
            list of CLEnvironment: List with one element, the CL runtime environment requested.
        """
        if isinstance(cl_device_type, string_types):
            cl_device_type = device_type_from_string(cl_device_type)

        runtime_list = []

        if platform is None:
            platforms = cl.get_platforms()
        else:
            platforms = [platform]

        for platform in platforms:
            if cl_device_type:
                devices = platform.get_devices(device_type=cl_device_type)
            else:
                devices = platform.get_devices()

            for device in devices:
                if device_supports_double(device):
                    try:
                        env = CLEnvironment(platform, device, compile_flags=compile_flags)
                        runtime_list.append(env)
                    except cl.RuntimeError:
                        pass

        return runtime_list
