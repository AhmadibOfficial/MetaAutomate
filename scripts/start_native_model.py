#!/usr/bin/env python3
"""P2-055 owner-operated local llama.cpp model admission/launch.

No model download, remote provider, API key or automatic tool execution.
Requires an operator-installed GGUF, pinned llama-server and an isolated
unprivileged Linux network namespace with only loopback. Flags and hashes
are not independent deployment attestation; all checks must be reviewed.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import os
from pathlib import Path
import re
import stat


class AdmissionError(RuntimeError):
    pass


def file_digest(path: Path) -> str:
    digest=sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify(env: dict[str,str]|None=None, *, network_probe=None,
           unprivileged_probe=None) -> tuple[Path,Path,int]:
    cfg=os.environ if env is None else env
    required=('MAT_LOCAL_MODEL_ENABLED','MAT_LOCAL_MODEL_LICENSE_REVIEWED',
              'MAT_LOCAL_MODEL_POLICY_REVIEWED','MAT_LOCAL_MODEL_ISOLATION_APPROVED')
    if cfg.get('WORKSPACE_AUTH_MODE')!='oidc' or any(cfg.get(k)!='1' for k in required):
        raise AdmissionError('OIDC, model licence, policy and isolation approvals required')
    nonroot=(lambda:os.geteuid()!=0) if unprivileged_probe is None else unprivileged_probe
    if not nonroot():
        raise AdmissionError('llama.cpp must not run as root')
    model=Path(cfg.get('MAT_LOCAL_MODEL_CHECKPOINT_FILE') or '.')
    binary=Path(cfg.get('MAT_NATIVE_LLAMA_SERVER_BINARY') or '.')
    if not model.is_absolute() or not binary.is_absolute():
        raise AdmissionError('Absolute pinned binary and model file paths required')
    if model.is_symlink() or not model.is_file() or model.suffix.lower()!='.gguf':
        raise AdmissionError('Regular local GGUF checkpoint required')
    if binary.is_symlink() or not binary.is_file() or not os.access(binary,os.X_OK):
        raise AdmissionError('Executable local llama-server binary required')
    if model.stat().st_uid!=os.geteuid() and unprivileged_probe is None:
        raise AdmissionError('GGUF must belong to the model service owner')
    if stat.S_IMODE(model.stat().st_mode)&0o077:
        raise AdmissionError('Private GGUF must not be group/world readable')
    if not 64<=model.stat().st_size<=12_000_000_000:
        raise AdmissionError('Invalid model file size')
    model_hash=cfg.get('MAT_LOCAL_MODEL_CHECKPOINT_SHA256','')
    bin_hash=cfg.get('MAT_NATIVE_LLAMA_SERVER_SHA256','')
    if (not re.fullmatch('[a-f0-9]{64}',model_hash) or
        not re.fullmatch('[a-f0-9]{64}',bin_hash)):
        raise AdmissionError('Expected SHA-256 fingerprints required')
    if file_digest(model)!=model_hash or file_digest(binary)!=bin_hash:
        raise AdmissionError('Pinned model or executable hash mismatch')
    if cfg.get('MAT_LOCAL_MODEL_URL')!='http://127.0.0.1:11434/v1/chat/completions':
        raise AdmissionError('Pinned loopback model URL required')
    checker=(lambda:sorted(os.listdir('/sys/class/net'))==['lo']) if network_probe is None else network_probe
    if not checker():
        raise AdmissionError('Kernel-visible network namespace must contain only loopback')
    threads=cfg.get('MAT_NATIVE_MODEL_THREADS','2')
    if not threads.isdigit() or not 1<=int(threads)<=8:
        raise AdmissionError('Thread limit must be 1 to 8')
    return binary,model,int(threads)


def main(argv=None)->int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args(argv)
    try:
        binary,model,threads=verify()
    except (AdmissionError,OSError,ValueError) as exc:
        parser.exit(2,f'NO-GO: {exc}\n')
    if args.check_only:
        print('LOCAL_MODEL_ADMISSION_OK: file hashes, loopback and process policy checked')
        return 0
    os.umask(0o077)
    # No --tools, --agent, remote URL, network download or shell execution.
    os.execv(str(binary),[str(binary),'--model',str(model),
                           '--host','127.0.0.1','--port','11434',
                           '--ctx-size','2048','--threads',str(threads),
                           '--parallel','1'])
    return 2


if __name__=='__main__':
    raise SystemExit(main())
