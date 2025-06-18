# My Hive Engine Tokens Snapshot v1.0

A Python-based script which takes in a Hive username and a list of Hive Engine tokens arguments (with default values if not provided), and generates a table with this information:
* symbol
* liquid holdings
* staked holdings
* delegated (away) holdings
* total holdings
* price of token in HIVE
* price (USD)
* 24h volume
* USD value of the token holdings
* HIVE value of the token holdings
* BTC value of the token holdings
* Totals in USD, HIVE, and BTC

The script also shows the account for which it was run, the list of tokens, and the date and time of taking the snapshot.

Also, the HIVEBTC, HIVEUSD and BTCUSD prices are mentioned at the end, based on the values reported by the Coingecko API.

# How to use?

Download the script from this repo. You must have Python installed on your computer. I have Python 3.10.12, haven't tested with anything else.

You need to install dependencies, if you don't have them. For Python 3, in Linux this should do it (you need to research for another OS - for example, ask an AI):

`pip3 install hiveengine, prettytable, requests`

To run the script in the most basic form, using the default parameters, you use this (from the folder where you saved the script):

`python3 he-tokens-snapshot.py`

If everything is ok, this should work for my account @gadrian and this list of HE tokens: SWAP.HIVE SPS DEC LEO. Both of them can be changed permanently from within the script (somewhere at the top, easy to find), or can be changed temporarily from the command-line. Just run the script with the `--help` option to see the parameters and examples of usage.

If you want to have the output in a file, you need to redirect it. Here's an example:

`python3 he-tokens-snapshot.py > output.txt`

or, using a different user:

`python3 he-tokens-snapshot.py -u spinvest > output.txt`
