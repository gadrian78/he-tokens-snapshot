# My Hive Engine Tokens Snapshot v1.32

Takes a snapshot of a list of Hive Engine tokens and all diesel pools for a given Hive account.

# How to use?

Download the Python files from this repo. You must have Python installed on your computer. I have Python 3.10.12, haven't tested with anything else.

You need to install dependencies, if you don't have them. For Python 3, in Linux this should do it (you need to research for another OS - for example, ask an AI):

`pip3 install hiveengine, prettytable, requests`

To run the script in the most basic form, using the default parameters, you use this (from the folder where you saved the script):

`python3 he-tokens-snapshot.py`

If everything is ok, this should work for a test account @constant-flux and this list of HE tokens: SWAP.HIVE SWAP.BTC, SPS DEC LEO. Both of them can be changed permanently from `config.py`, or can be changed temporarily from the command-line. Just run the script with the `--help` option to see the parameters and examples of usage.

If you want to have the output in a file, you need to redirect it. Here's an example:

`python3 he-tokens-snapshot.py > output.txt`

or, using a different user:

`python3 he-tokens-snapshot.py -u spinvest > output.txt`
