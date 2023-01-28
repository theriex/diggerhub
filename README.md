# diggerhub
Sync hub and home for digger app.

DiggerHub saves updated account and song info sent from the Digger app.  It
serves as a backup data repository, and provides automatic synchronization
so you can run Digger on different devices and keep all your ratings and
last played times up to date.

In the Digger app, a song rating can be accessed by all users authorized in
the app installation.  On DiggerHub, all song ratings are specific to a
DiggerHub account.

## Development

cd build
node makelinks.js

cd site
../dloc/run.sh
mysql.server start
http://localhost:8080

