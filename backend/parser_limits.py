"""Resource containment for the document worker; not a complete OS sandbox."""
import sys


def contain():
    sys.dont_write_bytecode = True
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                        ('flags', wintypes.DWORD), ('min_working', ctypes.c_size_t), ('max_working', ctypes.c_size_t),
                        ('active', wintypes.DWORD), ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in ('reads','writes','other','read_bytes','write_bytes','other_bytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        job = kernel.CreateJobObjectW(None, None)
        limits = Extended()
        limits.basic.flags = 0x100 | 0x8 | 0x2  # process memory, active process count, user CPU time
        limits.basic.active = 1
        limits.basic.process_time = 12 * 10_000_000
        limits.process_memory = 512 * 1024**2
        if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
            raise RuntimeError('Could not apply parser resource limits. Use pasted text instead.')
        # Keep handle open for worker lifetime.
    else:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
        resource.setrlimit(resource.RLIMIT_CPU, (12, 12))

    def audit(event, args):
        if event.startswith(('socket.', 'subprocess.', 'os.exec', 'os.spawn')) or event == 'os.system':
            raise PermissionError('Document workers cannot use the network or launch programs')
        if event == 'open':
            mode = args[1] if len(args) > 1 else None
            if isinstance(mode, str) and any(c in mode for c in 'wax+'):
                raise PermissionError('Document workers cannot write files')
    sys.addaudithook(audit)
