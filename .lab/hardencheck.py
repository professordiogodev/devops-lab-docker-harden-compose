#!/usr/bin/env python3
import json, os, re, socket, subprocess, sys, time, urllib.request
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
passed = failed = 0
F = ["-f", "compose.hardened.yaml"]


def check(desc, ok, hint=""):
    global passed, failed
    if ok:
        passed += 1; print("PASS  " + desc, flush=True)
    else:
        failed += 1; print("FAIL  " + desc + (("   -> " + hint) if hint else ""), flush=True)


def finish():
    print()
    print(("ALL CHECKS PASSED (%d/%d)" % (passed, passed)) if failed == 0 else ("%d check(s) failed, %d passed" % (failed, passed)))
    sys.exit(1 if failed else 0)


def sh(*a, timeout=240):
    r = subprocess.run(a, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def dc(*a):
    return sh("docker", "compose", *F, *a)


raw = open("compose.hardened.yaml").read()
code = "\n".join(l for l in raw.split("\n") if not l.lstrip().startswith("#"))
print("== The file ==")
check("compose.hardened.yaml is written", "services:" in code, "see the TODO comments")
if "services:" not in code:
    finish()
check("no privileged mode, no Docker socket, no bind mount of the source", "privileged: true" not in code and "docker.sock" not in code and not re.search(r"-\s*\./?:", code))
check("no :latest tag and no untagged image", not re.search(r"image:\s*\S+:latest", code) and not re.search(r"image:\s*[a-z/-]+\s*$", code, re.M))
check("no password written in the file (they come from .env and secrets/)", not re.search(r"postgres(ql)?://[^:@\s]+:[^@\s$]+@", code) and not re.search(r"POSTGRES_PASSWORD:\s*\S", code) and "pollie123" not in code)
rc, out, err = dc("config", "--format", "json")
check("the file is valid Compose", rc == 0, err[-300:])
if rc != 0:
    finish()
cfg = json.loads(out)
S = cfg["services"]
check("four services: api, worker, db, redis", {"api", "worker", "db", "redis"} <= set(S))
check("the backend network is internal (no route to the internet)", cfg.get("networks", {}).get("backend", {}).get("internal") is True)
nets = {n: set((S[n].get("networks") or {}).keys()) or {"default"} for n in S}
check("db, redis and worker are ONLY on the backend network; api is on frontend and backend",
      nets.get("db") == {"backend"} and nets.get("redis") == {"backend"} and nets.get("worker") == {"backend"} and nets.get("api") == {"frontend", "backend"}, str(nets))

print("== Start it ==")
dc("down", "-v")
rc, out, err = dc("up", "-d", "--wait", "--wait-timeout", "150")
check("the stack starts and every health check passes (docker compose up --wait)", rc == 0, (out + err)[-400:])
if rc != 0:
    print(dc("ps", "-a")[1][-600:])
    finish()


def inspect(svc):
    cid = dc("ps", "-q", svc)[1].strip().split("\n")[0]
    return json.loads(sh("docker", "inspect", cid)[1])[0], cid


print("== Inspect the running containers ==")
for svc in ("api", "worker"):
    i, cid = inspect(svc)
    hc, cf = i["HostConfig"], i["Config"]
    check("%s: non-root numeric user, read-only filesystem, no privileges" % svc,
          re.fullmatch(r"[1-9]\d*(:\d+)?", cf.get("User", "") or "") is not None and hc["ReadonlyRootfs"] and not hc["Privileged"])
    check("%s: all capabilities dropped and no-new-privileges" % svc,
          "ALL" in (hc.get("CapDrop") or []) and any("no-new-privileges" in s for s in (hc.get("SecurityOpt") or [])))
    check("%s: memory limit (<= 512 MB), PID limit and CPU limit" % svc,
          0 < hc["Memory"] <= 512 * 1024 * 1024 and (hc.get("PidsLimit") or 0) > 0 and (hc.get("NanoCpus") or hc.get("CpuQuota") or 0) > 0)
    check("%s: no host mounts (no socket, no source tree)" % svc, not [m for m in i["Mounts"] if m["Type"] == "bind"])
i, _ = inspect("api")
pb = i["HostConfig"]["PortBindings"] or {}
hosts = {b["HostIp"] for v in pb.values() for b in v}
check("api: port 8000 is published on 127.0.0.1 ONLY", hosts == {"127.0.0.1"}, str(pb))
for svc in ("db", "redis"):
    i, _ = inspect(svc)
    check("%s: no published ports, no-new-privileges, a memory limit" % svc,
          not (i["HostConfig"]["PortBindings"] or {}) and any("no-new-privileges" in s for s in (i["HostConfig"].get("SecurityOpt") or [])) and i["HostConfig"]["Memory"] > 0)
i, _ = inspect("db")
envs = i["Config"]["Env"]
check("db: the password comes from a file (POSTGRES_PASSWORD_FILE), not from the environment",
      any(e.startswith("POSTGRES_PASSWORD_FILE=") for e in envs) and not any(e.startswith("POSTGRES_PASSWORD=") for e in envs))
i, _ = inspect("redis")
cmdline = " ".join((i["Config"].get("Cmd") or []) + [i.get("Path", "")] + (i.get("Args") or []))
check("redis: read-only filesystem, all capabilities dropped, started with a password",
      i["HostConfig"]["ReadonlyRootfs"] and "ALL" in (i["HostConfig"].get("CapDrop") or []) and "requirepass" in cmdline)

print("== Attack it ==")


def ex(svc, *cmd):
    return dc("exec", "-T", svc, *cmd)


check("api: cannot write to its filesystem (touch /x fails) but can use /tmp", ex("api", "touch", "/x")[0] != 0 and ex("api", "touch", "/tmp/ok")[0] == 0)
check("api: runs as a non-root user (id -u)", ex("api", "id", "-u")[1].strip() not in ("0", ""))
check("api: has no capabilities (CapEff is zero)", re.search(r"CapEff:\s*0+\s", ex("api", "cat", "/proc/self/status")[1] + " ") is not None)
check("api: the Docker socket is not there", ex("api", "ls", "/var/run/docker.sock")[0] != 0)
py = "import socket,sys; s=socket.socket(); s.settimeout(3); s.connect((sys.argv[1], int(sys.argv[2]))); print('open')"
check("api can reach the database and Redis on the backend network",
      ex("api", "python", "-c", py, "db", "5432")[0] == 0 and ex("api", "python", "-c", py, "redis", "6379")[0] == 0)
check("worker has NO route to the internet (internal network)", ex("worker", "python", "-c", py, "1.1.1.1", "443")[0] != 0)


def host_open(p):
    try:
        socket.create_connection(("127.0.0.1", p), timeout=2).close()
        return True
    except OSError:
        return False


check("from the host, 5432 (database) and 6379 (redis) are closed", not host_open(5432) and not host_open(6379))


def get(path):
    try:
        return urllib.request.urlopen("http://127.0.0.1:8000" + path, timeout=5).status
    except Exception as e:
        return getattr(e, "code", 0)


ok = False
for _ in range(20):
    ok = get("/healthz") == 200
    if ok:
        break
    time.sleep(3)
check("from the host, http://127.0.0.1:8000/healthz answers 200", ok)
check("and /readyz answers 200 (the API reaches PostgreSQL and Redis with the secrets)", get("/readyz") == 200, dc("logs", "--tail", "8", "api")[1][-300:])
dc("down", "-v")
finish()
