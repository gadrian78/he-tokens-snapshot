# Hive Portfolio Tracker v1.61

The basic functionality: takes a snapshot of a list of Hive Engine tokens, all diesel pools, and all layer 1 holdings for a given Hive account.

Advanced functionality: automatically generates and saves snapshots (daily, weekly, monthly, quarterly, yearly) of the data collected to be used further by a separate script. Best to be run automatically (see below).

  * The tool has persistent caching and a 15 minutes expiration time to avoid unneccessary calls to APIs.

## Author

Created by [https://peakd.com/@gadrian](https://peakd.com/@gadrian) in June-July 2025.

## License

Feel free to use or modify it, as long as you keep the author note(s) and the same open-source, free-to-use and modify license.

## Requirements

* Linux (or not, but you are in charge of making it work)

* Python 3.10+ (only tested with 3.10.12, probably works with lower versions)

* dependencies from `requirements.txt` (installed automatically if you run `setup.sh`)

## Configuration and Installation

Download everything from this repo to a new directory on your computer.

The next step is to configure the tool for your installation.

Configuration is made from `config.sh`. Every option is explained there.

You MUST set:
* `SCRIPT_PATH`
* `SNAPSHOTS_BASE_DIR`
* `USER_TOKENS`

Everything else should work with default settings.

If you don't want `setup.sh` to make Hive Portfolio Tracker run daily based on the settings in config, set `AUTO_SETUP_SERVICE` to `false`, and run `setup-service.sh` when you want it to run automatically, and `stop-automation.sh` when you want it to stop.

Run `setup.sh` after updating `config.sh`. That will set up Python's virtual environment, install dependencies, create some needed directories, and, if `AUTO_SETUP_SERVICE` is true (it is by default), it will set up the tool to run daily.

On default settings, the script should run every morning at 8am or as soon as the computer is turned on and has access to internet after that, for all users in the list and their associated list of tokens (and all the diesel pools and layer 1 holdings).

Daily, weekly, monthly, quarterly and yearly snapshots are saved under the directory provided for that purpose with a directory structure as follows:
```
|- SNAPSHOTS_BASE_DIR
|-- user1
|---- daily
|---- weekly
|-- user2 
|---- daily
|---- weekly
```

## Running the Tool Manually

There are different ways to run the Hive Portfolio Tracker manually.

Before I decribe them, note that in the previous section I described the semi-automated way to run it, setting up automation and stopping it at will.

Let's see what are the manual ways to use the tool.

First of all, another helper script makes it easy if you want to run the tool on occasions for a list of accounts and associted tokens.
That is `take-snapshot-multiple-accounts.sh`. Customize it with your own accounts and tokens, and run it when you want!

If you want to run the tool for one account at a time, the Python script to run is `take-snapshot.py` (used by all other methods above).

Without any parameters it uses the account and tokens set in `modules/config.py`. If you only have one account to track, just modify the info there.

If you want to use the tool for different accounts, note that it has the command-line arguments `-u username` and `-t list-of-tokens-separated-by-spaces`.
You can use `--help` for help on the available options.

If you want to have the output in a file to consult it later in a pretty visual form, you need to redirect it. Here's an example:

`./venv/python take-snapshot.py > output.txt`

## Uninstallation

If you want a complete uninstallation of Hive Portfolio Tracker, you should use `uninstall.sh`. That should remove any data from your system related to Hive Portfolio Tracker tool since you decided to create the project directory and copy files from this repo to it until present. We are talking about the systemd service, timer (if you ever set the tool to run daily), Python virtual environment, your snapshot saves (if they are in a subdirectory of the project directory and you haven't decided to move them elsewhere for safekeeping), caches, project files and the project directory.

The uninstallation script uses the same variables you set in the `config.sh` script, so it should work fine. I tested it on my system and it works - nothing left.

**The script needs your confirmation twice to continue, once at the beginning, and second on removing files. If you want to keep anything (like snapshots), it's advisable to do it before you run the uninstalation script, but certainly before you confirm it.**

## More Info?

Check out my posts on the subject from [https://peakd.com/@gadrian](https://peakd.com/@gadrian)


