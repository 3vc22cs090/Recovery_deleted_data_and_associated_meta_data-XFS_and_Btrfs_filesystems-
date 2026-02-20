# recovery_utils.py
import subprocess
import shlex
import tempfile
from pathlib import Path
from typing import Optional

def run_command(cmd: str, timeout: int = 30) -> dict:
    try:
        completed = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=timeout)
        return {
            'rc': completed.returncode,
            'stdout': completed.stdout,
            'stderr': completed.stderr
        }
    except Exception as e:
        return {'rc': -1, 'stdout': '', 'stderr': str(e)}

def attempt_xfs_recover(device: str, filename_pattern: str, outdir: Optional[str] = None) -> dict:
    outdir = outdir or tempfile.mkdtemp(prefix='xfs_recover_')
    suggested_cmd = f"xfs_undelete -d {device} -o {outdir} -p {shlex.quote(filename_pattern)}"
    return {
        'suggested_cmd': suggested_cmd,
        'outdir': outdir,
        'note': 'Run the suggested command as root on the host where the block device is available. This wrapper did not execute it.'
    }

def attempt_btrfs_restore(device: str, subvol: Optional[str], filename_pattern: str, outdir: Optional[str] = None) -> dict:
    outdir = outdir or tempfile.mkdtemp(prefix='btrfs_recover_')
    suggested_cmd = f"btrfs restore -v {shlex.quote(device)} {outdir}"
    return {
        'suggested_cmd': suggested_cmd,
        'outdir': outdir,
        'note': 'Inspect recovered files in outdir; search for filename pattern. Run as root on the host.'
    }
