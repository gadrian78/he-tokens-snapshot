# Make sure this shell script has the permission to be executed.
 
# Run it from the directory where you installed the Hive Portfolio Tracker tool.

# Change USERNAMEn and LIST_TOKENS_FOR_USERNAMEn placeholders below to your own Hive accounts and the list of tokens associated with each user.

# If you haven't created a Python virtual environment by running setup.sh, make sure you have dependencies installed wherever Python is ran from.

# Run script for USERNAME1
echo "Taking snapshot for account: USERNAME1"
./venv/bin/python3 ./take-snapshot.py -u USERNAME1 -t LIST_TOKENS_FOR_USERNAME1 --quiet
sleep 5
# Run script for USERNAME2
echo "Taking snapshot for account: USERNAME2"
./venv/bin/python3 ./take-snapshot.py -u USERNAME2 -t LIST_TOKENS_FOR_USERNAME2 --quiet
sleep 5
# Run script for USERNAME3
echo "Taking snapshot for account: USERNAME3"
./venv/bin/python3 ./take-snapshot.py -u USERNAME3 -t LIST_TOKENS_FOR_USERNAME3 --quiet
#sleep 5 // un-comment if you add more accounts

# Add more or remove the unnecessary as needed based on the number of accounts you want tracked every day.
# !! Note that the more accounts you track and the longer the list of tokens the more time it takes to process them !!

echo "Manual run of Hive Portfolio Tracker completed for the accounts provided." # you can list your accounts in the final message if you want to.
echo

