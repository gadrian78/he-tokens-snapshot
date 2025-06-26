# Make sure this shell script has the permission to be executed.
 
# Run it from the directory where you installed the Hive Engine Tokens Snapshots tool.

# Change USERNAMEn and LIST_TOKENS_FOR_USERNAMEn placeholders below to your own Hive accounts and the list of tokens associated with each user.

# Run script for USERNAME1
/usr/bin/python3 ./he-tokens-snapshot.py -u USERNAME1 -t LIST_TOKENS_FOR_USERNAME1 --quiet
# Run script for USERNAME2
/usr/bin/python3 ./he-tokens-snapshot.py -u USERNAME2 -t LIST_TOKENS_FOR_USERNAME2 --quiet
# Run script for USERNAME3
/usr/bin/python3 ./he-tokens-snapshot.py -u USERNAME3 -t LIST_TOKENS_FOR_USERNAME3 --quiet

# Add more or remove the unnecessary as needed based on the number of accounts you want tracked every day.
# !! Note that the more accounts you track and the longer the list of tokens the more time it takes to process them !!

echo "Manual run of Hive Engine Tokens Snapshot completed for the accounts provided." # you can list your accounts in the final message if you want to.
echo

