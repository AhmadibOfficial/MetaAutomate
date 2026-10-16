#!/usr/bin/env python3
"""P2-03y ephemeral Linux container confinement smoke test.

Must run only in an isolated disposable CI container: --network none,
--read-only, nonroot, no capabilities, no service secrets, no Docker socket.
Checks isolation properties, NOT a production deployed agent/workload.
"""
import os
import socket

assert hasattr(os,"geteuid") and os.geteuid()!=0,"Container must be nonroot"
assert not os.path.exists("/var/run/docker.sock"),"Docker control socket mounted"
assert not os.path.exists("/run/secrets"),"Secrets mounted"
assert not any(k for k in os.environ if any(p in k.upper() for p in
               ("TOKEN","API_KEY","PASSWORD","SECRET","CREDENTIAL"))), \
               "Potential credentials present"
assert os.path.exists("/proc/net/route"),"Linux network namespace unverified"
routes=open("/proc/net/route",encoding="ascii").read().splitlines()[1:]
assert all(len(fields:=line.split())<2 or fields[1]!="00000000"
           for line in routes), "Default network route present"
try:
    with open("/p2-03y-forbidden-write","w",encoding="ascii") as test:
        test.write("should not write")
    raise AssertionError("Container root filesystem unexpectedly writable")
except OSError:
    pass
with socket.socket() as test:
    test.settimeout(0.6)
    try:
        test.connect(("1.1.1.1",443))
        raise AssertionError("Sandbox unexpectedly reached an external IP")
    except (OSError,socket.timeout):
        pass

# No external task, model or confidential data ever handled here.
assert (12*5)==60
print("PASS: ephemeral CI worker is nonroot, no default route, no "
      "network connection, readonly root, no mounted container control socket")
print("SOURCE-ONLY: this does not verify live staging runtime or real agent isolation")
