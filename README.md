# n8n with Docker Compose and ngrok

A production-oriented reference for a small, single-host [n8n](https://n8n.io/) deployment, with PostgreSQL, persistent storage, isolated Code runners, and a free public HTTPS URL required for external webhooks through ngrok.

Use this repository as a starting point and adapt it to your own security, backup, and operational requirements.

## Requirements

- Docker Engine 28 or later and Docker Compose 2.20.2 or later (including Compose v5).
- Docker configured to start automatically: at sign-in with Docker Desktop, or at boot with Docker Engine on Linux.
- An ngrok account on the free plan.
- Optional: [just](https://github.com/casey/just) for running commands.

## Quick start

1. Copy the example environment file:

    ``` sh
    cp .env.example .env
    ```

2. Edit `.env` and replace every `CHANGE_ME` value. Use unique random values for all passwords, `N8N_ENCRYPTION_KEY`, and `N8N_RUNNERS_AUTH_TOKEN`.

    With `just` installed, generate a random password and copy it to the clipboard:

    ``` sh
    just pass
    ```

3. Set both timezone variables:

    ``` sh
    GENERIC_TIMEZONE="America/Los_Angeles"
    TZ="America/Los_Angeles"
    ```

4. Get your auth token and dev domain from the ngrok dashboard, then set the ngrok variables:

    ``` sh
    NGROK_AUTHTOKEN="CHANGE_ME"
    NGROK_PUBLIC_DOMAIN="CHANGE_ME"
    ```

5. Validate and start the stack:

    ``` sh
    docker compose config --quiet
    docker compose up -d
    ```

6. Open `http://localhost:5678` and create the n8n owner account. Use the ngrok URL for public webhooks and triggers rather than routine editor access.

    If Docker is running on another computer or a cloud VM, `localhost` on your computer refers to your computer, not the machine running n8n. See [How do I access n8n from another computer?](#7-how-do-i-access-the-n8n-editor-from-another-computer) below.

## Common commands

``` sh
docker compose ps          # Show service status
docker compose logs -f n8n # Follow n8n logs
docker compose down        # Stop the stack
```

## Key implementation details

This setup has four services, each with a specific job. These choices explain much of the configuration:

### Public webhooks through ngrok

ngrok gives external services a consistent public HTTPS address for production and test webhooks, forwarding requests to `n8n:5678` over the Compose network. The editor remains accessible through ngrok; the active Traffic Policy does not restrict the public endpoint to webhook routes.

### Editor access versus webhook access

`N8N_WEBHOOK_URL` tells n8n to generate public webhook and trigger URLs using your ngrok HTTPS domain. External services such as GitHub, Slack, and Telegram can therefore reach workflows through ngrok even when you open the n8n editor directly.

`N8N_EDITOR_BASE_URL` sets localhost as the instance address for generated editor links and frontend telemetry proxy URLs. Recipients of those links need local access or an SSH tunnel. Production and test webhook URLs continue to use ngrok. If you choose a different canonical editor address, update `N8N_EDITOR_BASE_URL` in the Compose file to match.

For routine administration, use a direct connection to the editor where practical. On the machine running Docker, open `http://localhost:5678`. This keeps the editor's frequent API requests from consuming ngrok's monthly HTTP request allowance. The n8n host port is bound to `127.0.0.1`, so it is not directly reachable from other computers by default.

For another computer on a LAN or a cloud VM, retain the localhost-only binding and forward the port over SSH. Run this on your computer, replacing `user@docker-host` with your SSH username and the Docker host's address:

```sh
ssh -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:5678:127.0.0.1:5678 user@docker-host
```

Keep the SSH connection open and browse `http://localhost:5678`. This requires SSH access to the Docker host and an available local port 5678. Use a browser that supports secure cookies on localhost; Safari may require HTTPS.

Changing the mapping to `5678:5678` publishes n8n on all host interfaces, potentially including public interfaces. It does not make plain HTTP access through a LAN IP compatible with n8n's default secure cookies. Direct LAN administration needs HTTPS and appropriate network access restrictions, or an explicit decision to weaken cookie security.

Use [Prompt 7](#7-how-do-i-access-the-n8n-editor-from-another-computer) for a walkthrough of these options and their security implications.

The ngrok container does not need the host's published port to reach n8n. It connects directly to `n8n:5678` over the private Compose network, while `N8N_WEBHOOK_URL` supplies the public HTTPS address that n8n uses for externally reachable webhooks.

n8n and ngrok's inspection interface bind their host ports to `127.0.0.1` (this machine only); PostgreSQL and the runner broker publish no host ports at all.

### Explicit configuration for each service

`.env` holds the values you configure, while `docker-compose.yaml` declares where each value is used. Compose reads `.env` to fill in those references; it does not automatically pass the whole file into every container. Each service receives only the values explicitly passed to it from `.env`, keeping unrelated secrets out. `${VARIABLE:?}` stops Compose when a required value is missing or empty, but does not detect a `CHANGE_ME` placeholder. Fixed internal addresses and settings stay in the Compose file.

### Separate execution for Code nodes

n8n coordinates workflows, while the external task runners execute Code node tasks in a separate container. The runner uses a minimal image, runs as a non-root user, has a read-only filesystem with temporary writable space, and has CPU, memory, and process limits. These controls limit what task code can access and consume; a failed task can still cause its workflow to fail.

### Security in several places

n8n uses a database account without PostgreSQL superuser privileges. The supplied settings restrict access to environment variables, disable community packages and the public REST API, and limit archive decompression. The ngrok policy filters selected unwanted traffic before it reaches n8n. Optional OAuth and rate-limiting rules are commented out; traffic filtering does not replace authentication.

### Persistence and predictable operation

Named volumes retain database and n8n data when containers are replaced. Health checks control startup order, restart policies help services come back after exits, log rotation limits log growth, and shutdown grace periods allow time to finish work. n8n and its runners share one version setting. Keeping the host and Docker running, testing updates, and maintaining recoverable backups remain part of operating the deployment.

## Operations and maintenance

Size the stack for your workflows and test changes before relying on it. The included limits are conservative starting points for a small personal instance, but workflows that process large files, run Python libraries, or execute in parallel may need different values. See n8n's guidance for [controlling concurrency](https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/control-concurrency/), [resolving memory issues](https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/fix-memory-issues/), and [monitoring n8n](https://docs.n8n.io/deploy/host-n8n/keep-n8n-running/monitor-n8n/).

Create a backup and maintenance process that you have tested before you need it. A recoverable backup includes the PostgreSQL data, the `n8n_data` volume, and a securely stored copy of `N8N_ENCRYPTION_KEY`. Review n8n's guidance on [updating a self-hosted instance](https://docs.n8n.io/deploy/host-n8n/keep-n8n-running/update-n8n/) and the PostgreSQL documentation on [backup and restore](https://www.postgresql.org/docs/current/backup.html).

- Keep `.env` private and store its secrets in a secrets manager. Ensure `N8N_ENCRYPTION_KEY` can be recovered separately from the host; losing or changing it makes stored credentials unreadable.
- PostgreSQL only applies initialization settings when its data volume is empty. Changing a database password in `.env` does not update an existing database user.
- Pin and test updates before applying them. Update `N8N_VERSION` only in `.env` so n8n and its task runner stay on the same version.
- Setting `PGDATA` keeps this Compose volume path consistent, but PostgreSQL major-version upgrades still require a planned migration.

## Use AI to explain how this code works

Open this repository using an AI coding assistant, or attach the repository files to a chat session. Use the `.env.example` file, not your private `.env` containing secrets.

Here are a few prompts to get you started. Each is written to pull a workshop-style walkthrough out of your assistant, paced in digestible chunks rather than dumped as one dry technical write-up. Each also stays grounded in this repository rather than turning into a general Docker tutorial.

### 1. How does a webhook from an external service reach my instance?

```text
Teach me this the way you'd walk a beginner through it in a workshop, not the way you'd write documentation. Start with the story of one webhook request landing on my n8n instance, and build up the technical detail as the story needs it rather than dumping it all up front. Along the way, work in the roles of ngrok, n8n, PostgreSQL, and the task runners, how ngrok forwards traffic to the n8n container and binds to the dev domain, and how the public domain, Compose service names, and localhost port bindings differ. Use an analogy for why tunneling through ngrok is safer than exposing the container directly to the internet. For anything ngrok-specific, check https://ngrok.com/llms.txt, since ngrok's mechanics and terminology have shifted and it corrects common stale assumptions. Assume I have no ngrok, networking, or Docker experience. Structure the explanation in digestible chunks with good pedagogical pacing, and use diagrams wherever they'd help.
```

### 2. Why are environment variables individually specified in the Docker Compose file?

```text
Teach me this like you're pairing with me at the keyboard, not writing a reference doc. Open .env.example and docker-compose.yaml with me and narrate what you see, using a database password, the public domain, and N8N_VERSION as the running examples you keep coming back to. Use an analogy to explain why each service only gets the environment variables it's explicitly handed, instead of the whole .env file. Walk me through Compose substitution versus container environment variables, and the :? required syntax, as things we discover together rather than a list of rules. Show me what actually happens, step by step, if a value is missing or still says CHANGE_ME. Assume I'm new to Docker Compose. Structure the explanation in digestible chunks with good pedagogical pacing, and use diagrams wherever they'd help.
```

### 3. Why use an external task runner?

```text
Teach me this like you're telling the story of what happens to a piece of code the moment I run a workflow, not listing runner specifications. Start with the difference between a Code node task and the workflow it belongs to, then follow one task into the runner: how it gets there, how n8n and the runner authenticate each other, and what it can and can't touch once it's running in that minimal, non-root, read-only environment with its own CPU, memory, and process limits. For each restriction, tell me what problem it's solving and what it costs. End with what happens to the task, and to the rest of the workflow, if the runner crashes or hits a limit. Ground the story in this repository. Structure the explanation in digestible chunks with good pedagogical pacing, and use diagrams wherever they'd help.
```

### 4. What makes this a production-oriented deployment?

```text
Teach me this like a senior engineer walking a newer one through why this isn't just a toy setup. Tell the story of what breaks first in a naive docker run version of n8n, and how each choice here, health checks, restart policies, log rotation, shutdown grace periods, the non-superuser database account, restricted environment variables, disabled community packages and the public REST API, the ngrok traffic policy, closes that gap. Explain why backups, tested updates, and a recoverable N8N_ENCRYPTION_KEY matter for something you intend to keep running for months, not just today. Ground it in this repository, and be honest about what a real production deployment would still need beyond what's here. Structure the explanation in digestible chunks with good pedagogical pacing, and use diagrams wherever they'd help.
```

### 5. How do I read this docker-compose.yaml if I've never seen one?

```text
Teach me how to read a Compose file using this one as our example, the way you'd teach someone their first Compose file rather than just this one. Go through it top to bottom and, for each new idea, services, networks, volumes, depends_on, healthcheck, explain the general concept first, then point to where it shows up here and why it's written that way. By the end, I should be able to open a Compose file I've never seen and have a rough idea what it's doing. Structure the explanation in digestible chunks with good pedagogical pacing, and use diagrams wherever they'd help.
```

### 6. What's the first thing to check if this won't start?

```text
Walk me through diagnosing this stack like you're debugging it live with me, narrating your reasoning rather than handing me a checklist. Start from a few realistic failure stories: a container that won't come up, a webhook that never arrives, an ngrok domain that won't connect, and for each one, tell me what the first symptom would look like, which command you'd reach for first, and how the error message points to the fix. For anything ngrok-specific, check https://ngrok.com/llms.txt, which links to the ERR_NGROK_* error reference and corrects common stale assumptions about ngrok, instead of guessing at the actual message or code. Ground every failure in something that could actually go wrong in this repository, and end with the handful of commands worth remembering for next time. Structure the explanation in digestible chunks with good pedagogical pacing, and use diagrams wherever they'd help.
```

### 7. How do I access the n8n editor from another computer?

```text
Teach me why I can open n8n at http://localhost:5678 on the machine running Docker but can't use that address from another computer. Start by explaining that localhost always means the machine making the request, then use this repository to show how the `127.0.0.1:5678:5678` binding, host network interfaces, the Compose network, and `n8n:5678` fit together.

Explain the deliberate split between editor and webhook access: I should administer the editor directly where practical, while `N8N_WEBHOOK_URL` keeps the ngrok HTTPS domain as the public address for external triggers and both production and test webhooks. Explain how `N8N_EDITOR_BASE_URL` keeps generated editor links and frontend telemetry proxy URLs on localhost, and why those links require local access or an SSH tunnel. Make clear why ngrok can reach n8n over the Compose network even though the host port is localhost-only, why the editor remains publicly reachable through ngrok, and why keeping routine editor traffic off ngrok preserves its monthly HTTP request allowance.

Then walk me through the right approach for three situations: the same machine, another computer on a trusted local network, and a cloud VM. For both LAN and cloud administration, recommend retaining the localhost binding and show SSH local port forwarding, including where to run the command and which address to open in the browser. Explain the SSH access and available local port requirements. Cover secure cookies on localhost and the Safari caveat. If discussing direct LAN access as an alternative, explain that `5678:5678` publishes on all interfaces and that HTTP access through a LAN IP does not work with the default secure cookies; cover HTTPS and network restrictions without silently disabling cookie security. Explain when to update `N8N_EDITOR_BASE_URL` for a different editor address. Assume I'm new to Docker and networking. Structure the explanation in digestible chunks with good pedagogical pacing, and use diagrams wherever they'd help.
```
