# Submission

Fork URL: <!-- paste the URL of your fork here -->

## Files to commit

- [ ] `compose.hardened.yaml`: the hardened stack
- [ ] `notes.md` with the attacks you tried (optional)

## Questions

Answer in your own words. Where a question asks for output, paste it in a code block.

### Q1. Paste the output of your attacks against `compose.insecure.yaml` (what you could read, write or reach) and against your hardened stack (what now fails). Which attack surprised you most?

**Your answer:**

<!-- replace this line with your answer -->

### Q2. Why is mounting `/var/run/docker.sock` into a container equal to giving it root on the host? Show the one command that proves it.

**Your answer:**

<!-- replace this line with your answer -->

### Q3. Explain `read_only: true` with a `tmpfs` for `/tmp`, `cap_drop: [ALL]`, and `no-new-privileges` in one sentence each. Which of them stops a process that already runs as root inside the container from becoming dangerous?

**Your answer:**

<!-- replace this line with your answer -->

### Q4. Memory, CPU and PID limits: what happens to a container that leaks memory or forks without end, with and without them? What does the kernel do when the limit is hit?

**Your answer:**

<!-- replace this line with your answer -->

### Q5. Where are the secrets now, and who can read them (`docker inspect`, `docker compose config`, `/proc/1/environ`, the image history)? What is the next step beyond files (Docker secrets, Vault, a cloud secret store)?

**Your answer:**

<!-- replace this line with your answer -->

### Q6. Draw the networks: which containers can reach which, and which can reach the internet? Why is `internal: true` on the backend network a strong control, and what does it break (hint: image pulls, outgoing calls)?

**Your answer:**

<!-- replace this line with your answer -->

### Q7. Paste the output of `./verify.sh`. It must end with **ALL CHECKS PASSED**.

**Your answer:**

<!-- replace this line with your answer -->

### Q8. **Tear down.** Paste the output of `./verify-teardown.sh`. It must end with **TEARDOWN VERIFIED**.

**Your answer:**

<!-- replace this line with your answer -->
