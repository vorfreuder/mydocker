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
MS_NOSUID = 2  # Ignore suid and sgid bits.
MS_NODEV = 4  # Disallow access to device special files.
MS_NOEXEC = 8  # Disallow program execution.
MS_REC = 16384
MS_PRIVATE = 1 << 18  # Change to private.
MS_BIND = 4096  # Bind directory at different place.
MS_STRICTATIME = 1 << 24  # Always perform atime updates.
MNT_DETACH = 2  # Just detach from the tree.


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


def umount(target, flags=None):
    ret = 0
    if flags is None:
        ret = libc.umount(target)
    else:
        ret = libc.umount2(target, flags)
    if ret < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, f"Error unmounting {target}: {os.strerror(errno)}")


libc.pivot_root.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
libc.pivot_root.restype = ctypes.c_int


def pivot_root(new_root, put_old):
    result = libc.pivot_root(new_root.encode(), put_old.encode())
    if result != 0:
        raise OSError("pivot_root failed")


base_path = os.path.dirname(__file__)
