# LAB | Docker: The Compose File the Pentester Loved

## The situation

Before Pollie goes public, the security team asked an external pentester to look at it. Twenty minutes later they sent a polite report. With one `docker exec` into the API container they were **root**, they could read the **Docker socket** (which means root on the host), the database was **open on the internet** with the password `pollie123`, Redis had **no password at all**, the secrets were in plain environment variables visible with `docker inspect`, and one container with a memory leak could take the whole machine down.

None of it was a bug in Pollie. It was all in one file, `compose.insecure.yaml`. You will rewrite it so that every one of those attacks fails, and you will prove each fix the only honest way: by running the attack yourself, before and after.

> **Your mission**
> - Read `compose.insecure.yaml` like an attacker and attack it
> - Write `compose.hardened.yaml`: least privilege, no secrets in the file, no exposed data stores, limits, health checks, an internal network
> - Run the same attacks against your stack and watch them fail
> - Tear down and prove it

**Time:** 105-120 min | **Cost:** free | **You need:** Docker with Compose v2, git, curl, Python 3 and a terminal. On Windows use WSL.

---

## Part 0 - Set the scene

Fork this repository, clone your fork and run `./setup.sh`. It clones Pollie, generates **random** passwords into `secrets/` and `.env` (git ignores both) and builds the production image `pollie:1` from the provided `Dockerfile`. Read the `Dockerfile` (it is the multi-stage, non-root image from the earlier lab) and then read `compose.insecure.yaml`. Count the problems. There are at least twelve.

---

## Part 1 - Attack the insecure stack

```bash
docker compose -f compose.insecure.yaml up -d
```

Then be the attacker, from a second terminal:

```bash
docker compose -f compose.insecure.yaml exec api id
docker compose -f compose.insecure.yaml exec api ls -l /var/run/docker.sock
docker compose -f compose.insecure.yaml exec api touch /anything && echo "the filesystem is writable"
docker compose -f compose.insecure.yaml exec api cat /proc/self/status | grep Cap
nc -zv 127.0.0.1 5432; nc -zv 127.0.0.1 6379
docker inspect $(docker compose -f compose.insecure.yaml ps -q db) --format '{{json .Config.Env}}'
```

Write down what each one gives you. For the socket, think about this: with `/var/run/docker.sock` inside a container, anything in it can ask the Docker daemon (which runs as root on the host) to start a new container with `/` of the host mounted. Try it with the Docker CLI if you want to see it (`docker run -v /:/host alpine ls /host` from inside a container that has the docker CLI and the socket). Then `docker compose -f compose.insecure.yaml down -v`.

> **Think** The container is "isolated". Which of the problems you found break that isolation, and which are about what a compromised process can do *inside* it? Sort them into two columns.

---

## Part 2 - Write the hardened stack

`compose.hardened.yaml` has the whole specification in its comments. The ideas behind each line:

| Control | Compose | What it stops |
|---------|---------|---------------|
| Non-root user | `user: "10001"` | a bug or a stolen shell starts with a powerless user |
| Read-only root filesystem | `read_only: true` + `tmpfs: [/tmp]` | malware cannot write itself to disk |
| No capabilities | `cap_drop: [ALL]` | no raw sockets, no mounting, no chown of others' files |
| No privilege gain | `security_opt: [no-new-privileges:true]` | setuid binaries cannot raise the user |
| Resource limits | `mem_limit`, `pids_limit`, `cpus` | a leak or a fork bomb cannot take the host |
| No host access | no `privileged`, no socket, no source bind mount | escaping to the host |
| Secrets as files | Compose `secrets:` and `*_FILE` | passwords visible in `docker inspect` and process lists |
| Minimal exposure | no `ports` for data stores; the API on `127.0.0.1` only | the database on the internet |
| Network segmentation | an `internal: true` backend network | a compromised worker phoning home |
| Health checks | `healthcheck:` | `docker compose up --wait` and restarts that mean something |
| Pinned images | `postgres:16`, `redis:7-alpine`, `pollie:1` | the surprise of `latest` |

Use a YAML anchor (`x-app: &app`) for what the API and the worker share. The API and the worker settings (database URL, Redis URL) come from `.env`; the database password also comes from `secrets/db_password.txt` through `POSTGRES_PASSWORD_FILE`.

```bash
docker compose -f compose.hardened.yaml config        # read what Compose will really run
docker compose -f compose.hardened.yaml up -d --wait
docker compose -f compose.hardened.yaml ps
```

> **Predict** Your API container now has a read-only root filesystem. Uvicorn, Python and Pollie all want to write somewhere at start-up (temporary files, `__pycache__`). What happens if you forget the `tmpfs` for `/tmp`? And why does the `internal: true` network still let the API reach the database but stop the worker from reaching `1.1.1.1`?

---

## Part 3 - Run the attacks again

Repeat Part 1 against `compose.hardened.yaml` (replace the file name). Every attack must fail or give a harmless answer:

- `id` shows a number that is not 0; `touch /x` fails; `touch /tmp/x` works;
- `CapEff` is all zeros; the socket does not exist;
- ports 5432 and 6379 are closed from the host; 8000 answers on `127.0.0.1` only;
- `docker inspect` of the database shows no password, only `POSTGRES_PASSWORD_FILE`;
- from the worker, an outbound connection to the internet fails.

> **Think** An `internal: true` network cannot reach the internet, in either direction. What stops working in a real deployment that needed this? (Think: a worker calling a payment provider, pulling an image, sending e-mail.) What is the usual answer: an egress proxy, a separate "egress" network for that single service, a firewall rule?

---

## Part 4 - Prove it

```bash
./verify.sh
```

It reads your file, starts your stack, inspects the running containers (user, read-only, capabilities, limits, mounts, ports, networks), and attacks them for you. Fix what is red and run it again until it ends with **ALL CHECKS PASSED**.

> **Stuck?** `up --wait` fails with `has no healthcheck configured`: every service needs one, the worker's health port is 9100. The API restarts in a loop with a permission error: the read-only filesystem needs a `tmpfs` for `/tmp`. `redis` is unhealthy: the password file path inside the container is `/run/secrets/redis_password`; the health check must use it. The API says `readyz` 503: the passwords in `.env` and `secrets/` must match (rerun `./setup.sh` after `./teardown.sh`). In YAML a `$` inside a Compose command must be written `$$`.

---

## Level up (optional)

- Run `trivy image pollie:1` and `docker scout cves pollie:1`. Which findings could you remove by changing the base image?
- Add a custom `seccomp` profile or `--security-opt apparmor`. What would you have to know about Pollie to write one?
- Run the whole stack with `userns-remap` or rootless Docker. What does the host see now when the container "is root"?
- Write a one-page threat model: what is the worst thing an attacker with code execution in the API can do now, and what is the next control you would add?

<!-- teardown:start (generated by labs.py, do not edit) -->
## Tear down (mandatory)

Resources left behind cost money, keep doors open and pollute the next lab. Removing what you created is part of the job, so it is part of the submission: **you must prove it is gone**.

Do this **last**, after you have pasted your `verify` output into `SUBMISSION.md` (once you tear down, the lab can no longer be verified).

1. Run `./teardown.sh`. It removes the containers, networks, volumes and images of the lab, the generated secrets and the cloned Pollie source.

Then run the proof:

```bash
./verify-teardown.sh
```

It prints a list of checks and must end with **TEARDOWN VERIFIED**. If it reports leftovers, remove them and run it again. Paste the full output in your submission.
<!-- teardown:end -->

<!-- submission:start (generated by labs.py, do not edit) -->
## Submission

Answer the questions in `SUBMISSION.md` in **your fork** (paste output in code blocks where asked), push, then submit the **URL of your fork**.

**Files to commit**

- `compose.hardened.yaml`: the hardened stack
- `notes.md` with the attacks you tried (optional)

**Questions to answer**

1. Paste the output of your attacks against `compose.insecure.yaml` (what you could read, write or reach) and against your hardened stack (what now fails). Which attack surprised you most?
2. Why is mounting `/var/run/docker.sock` into a container equal to giving it root on the host? Show the one command that proves it.
3. Explain `read_only: true` with a `tmpfs` for `/tmp`, `cap_drop: [ALL]`, and `no-new-privileges` in one sentence each. Which of them stops a process that already runs as root inside the container from becoming dangerous?
4. Memory, CPU and PID limits: what happens to a container that leaks memory or forks without end, with and without them? What does the kernel do when the limit is hit?
5. Where are the secrets now, and who can read them (`docker inspect`, `docker compose config`, `/proc/1/environ`, the image history)? What is the next step beyond files (Docker secrets, Vault, a cloud secret store)?
6. Draw the networks: which containers can reach which, and which can reach the internet? Why is `internal: true` on the backend network a strong control, and what does it break (hint: image pulls, outgoing calls)?
7. Paste the output of `./verify.sh`. It must end with **ALL CHECKS PASSED**.
8. **Tear down.** Paste the output of `./verify-teardown.sh`. It must end with **TEARDOWN VERIFIED**.
<!-- submission:end -->
