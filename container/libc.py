import ctypes
import ctypes.util
import os

libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
libc.mount.argtypes = (
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_ulong,
    ctypes.c_char_p,
)
MS_NOSUID = 2
MS_NODEV = 4
MS_NOEXEC = 8
MS_REC = 16384
MS_PRIVATE = 1 << 18


def mount(source, target, fs, mountflags, options=""):
    ret = libc.mount(
        source.encode(), target.encode(), fs.encode(), mountflags, options.encode()
    )
    if ret < 0:
        errno = ctypes.get_errno()
        raise OSError(
            errno,
            f"Error mounting {source} ({fs}) on {target} with options '{options}': {os.strerror(errno)}",
        )
