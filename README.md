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

The web version of Digger relies on many files from the main app.  To make
symlinks for these from diggerhub/site/public:
DDR=/Users/theriex/general/dev/digger/docroot  # wherever you put it...
ln -s $DDR/css/digger.css css/digger.css
ln -s $DDR/img/panelsbg.png img/panelsbg.png
ln -s $DDR/img/trash.png img/trash.png
ln -s $DDR/img/trashdis.png img/trashdis.png
ln -s $DDR/img/filteron.png img/filteron.png
ln -s $DDR/img/filteroff.png img/filteroff.png
ln -s $DDR/img/infoact.png img/infoact.png
ln -s $DDR/img/info.png img/info.png
ln -s $DDR/img/albumact.png img/albumact.png
ln -s $DDR/img/album.png img/album.png
ln -s $DDR/img/historyact.png img/historyact.png
ln -s $DDR/img/history.png img/history.png
ln -s $DDR/img/search.png img/search.png
ln -s $DDR/img/arrow12right.png img/arrow12right.png
ln -s $DDR/img/recordcrate.png img/recordcrate.png
ln -s $DDR/img/export.png img/export.png
ln -s $DDR/img/stars18ptCg.png img/stars18ptCg.png
ln -s $DDR/img/stars18ptC.png img/stars18ptC.png
ln -s $DDR/img/panface.png img/panface.png
ln -s $DDR/img/panback.png img/panback.png
ln -s $DDR/img/comment.png img/comment.png
ln -s $DDR/img/commentact.png img/commentact.png
ln -s $DDR/img/tunefork.png img/tunefork.png
ln -s $DDR/img/skip.png img/skip.png
ln -s $DDR/img/ranger.png img/ranger.png
ln -s $DDR/img/vknob.png img/vknob.png
ln -s $DDR/img/hknob.png img/hknob.png

