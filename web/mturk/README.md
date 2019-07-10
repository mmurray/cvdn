This directory contains the code and resources to run a multiplayer Mechanical Turk interface for collecting Cooperative Visual Navigation Dialog data.


**Setting Up the Server**

Host the `mturk/` directory on a PHP enabled web server.

For permissions, the `mturk/` directory and everything under it can be set to the web server group,
(e.g., `www-data` on some servers).
Permissions `drwxrwsr-x` should be set to directories `www/client` and `www/log`.
For regular files and scripts,  `-rw-rwxr--` should do.

Launch the server from `scripts/` with

```bash
python Server.py --client_dir ../www/client/ --log_dir ../www/log/
```

This will spin forever, pairing turkers to one another and facilitating communication between the two client browser
instances (e.g., chat texts, navigation actions).

Navigate via web browser to `[your server and path]/www/index.php` in two tabs to connect
with yourself and simulate two turkers.

**Docker**

If you have docker installed you can use the included shell scripts to launch the server components.

Build docker images:
```bash
./docker/build.sh
```

Run Apache/PHP with the `www` directory:
```bash
./docker/run_www.sh
```

Run the Python server:
```bash
./docker/run_server.sh
```

Run both in the background (useful for production):
```bash
./docker/run_prod.sh
``` 

**Matterport Data**

If using docker, set the environment variable `MATTERPORT_DATA_PATH` to the location of your copy of the matterport dataset and everything else will be wired up through mounted volumes.

If not using docker, you need to create symlinks for the following data paths:
- ../../tasks/R2R/data -> www/R2R_data
- ../../connectivity -> www/connectivity
- {your matterport data path} -> www/data

**The Gist**

Each client is assigned a unique id when they connect to the index page by PHP.
This id is used to identify the user on the python server side as well.

The client communicates to the python server by writing files to `client/[uid].client.json` which
specify actions like chatting and registering new users with the server.

The serve communicates with the client by writing files to `client/[uid].server.json` which specify
interface actions like showing/hiding chat and navigation elements and enabling/disabling components, as well
as forwarding chat messages from one client to the other.
