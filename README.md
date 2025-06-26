# My Hive Engine Tokens Snapshot v1.52

The basic functionality: takes a snapshot of a list of Hive Engine tokens and all diesel pools for a given Hive account.

Advanced functionality: automatically generates and saves snapshots (daily, weekly, monthly, quarterly, yearly) of the data collected to be used further by a separate script. Best to be run automatically (see below).

The tool has persistent caching and a 15 minutes expiration time to avoid unneccessary calls to APIs.

## Requirements

* Linux (or not, but you are in charge of making it work)

* Python 3.10+ (only tested with 3.10.12, probably works with lower versions)

* dependencies from `requirements.txt` (installed automatically if you run `setup.sh`)

## Installing dependencies and setting up to run automatically

There are different ways to approach this, depending on what you want to achieve and your OS.

Here's my approach on Linux and using a service and a timer that runs at 8am daily, or whenever there is uptime after that.

There is a setup shell script file created to make things easier: `setup.sh`.

The script automatically deactivates and removes previously set service and timer (if there was one). It also  automatically installs Python dependencies needed to run this tool.

It also creates the service and the timer needed, restarts the deamon and tests to see if the service is working properly at the end. It works for a list of users and associated lists of tokens.

You NEED TO edit the file with your own information for these variables (otherwise it won't work!):
```
SCRIPT_PATH="/home/path-to-project/he-tokens-snapshot.py"  # Shared script location
SNAPSHOTS_BASE_DIR="/home/path-to-project-snapshots"         # Base directory for all snapshots
```

Also, add YOUR list of accounts and their tokens here:
```
# User configuration with custom tokens - MODIFY THIS ASSOCIATIVE ARRAY
# Format: USER_TOKENS["USERNAME"]="token1 token2 token3 ..."
declare -A USER_TOKENS
USER_TOKENS["alice"]="LEO SPS DEC SWAP.HIVE"
USER_TOKENS["bob"]="LEO BEE PIZZA BEED"
USER_TOKENS["charlie"]="SPS DEC VOUCHER CHAOS"
USER_TOKENS["diana"]="LEO BEE SPS DEC SWAP.HIVE PIZZA"
```

Make sure the file has the permission to be executed and that you have admin rights, otherwise you won't be able to set up the service and the timer.

If everything went alright and you received no errors, the script should run every morning at 8am or as soon as the computer is turned on and has access to internet after that, for all users in the list and their associated list of tokens (and all the diesel pools).

Daily, weekly, monthly, quarterly and yearly snapshots are saved under the directory provided for that purpose with a directory structure as follows:
```
|- snapshots
|-- user1
|---- daily
|---- weekly
|-- user2 
|---- daily
|---- weekly
```

You don't want to set up the script to run automatically? Fine. It can be run manually.

## Running manually

Download everything from this repo to new directory on your computer like `MyHiveEngineTokensSnapshot` (or clone the repo). You must meet the requirements above.

Open the Terminal from the new directory.

To run the script in the most basic form, using the default parameters, use this:

`python3 he-tokens-snapshot.py`

If everything is ok, this should work for the account @constant-flux (one of mine) and this list of HE tokens: SWAP.HIVE SWAP.BTC SPS DEC LEO. Both of them can be changed permanently from `config.py`, or can be changed temporarily from the command-line. Just run the script with the `--help` option to see the parameters and examples of usage.

If you want to have the output in a file, you need to redirect it. Here's an example:

`python3 he-tokens-snapshot.py > output.txt`

or, using a different user:

`python3 he-tokens-snapshot.py -u spinvest > output.txt`

**Want to run it manually for a list of accounts?** No problem! Just adapt this shell script to your needs: `multiaccount-manual-run.sh`

## Uninstallation

If you only want the tool prevented to run automatically after you had it set up to run every morning at 8am, you can run `stop-automation.sh` from the script directory.

If you want a complete uninstallation you should use `uninstall.sh`. That should reverse any changes made to your system related to this tool since you decided to create the project directory and copy files from this repo to it and to present. We are talking about the service, timer, Python virtual environment, your snapshot saves (if they are in a subdirectory of the project directory and you don't decide to move them elsewhere for safekeeping), caches, project files and the project directory.  You need to set correct path and dir from your system here too:
```
# Configuration - should match the setup script
SCRIPT_PATH="/home/shared/hive-scripts/he-tokens-snapshot.py"
SNAPSHOTS_BASE_DIR="/home/shared/portfolio-snapshots"
```

Note that I haven't tested the uninstallation, but the script "looks" ok.

## More Info?

Check out my posts on the subject from [https://peakd.com/@gadrian](https://peakd.com/@gadrian)


