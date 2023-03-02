# spotify_analysis
analyze spotify data

Packages necessary: sqlite3; Neo4j (need desktop application as well); pandas; copy; statistics; plotly; sklearn; spotipy

OR tap into a local environment using source litEnv/bin/activate This essentially sets up a local environment that allows you to run all the python code without having to download dependencies globally.

For this, you'd need to download virtualenv which you can download using: pip install virtualenv

    first create a spotify developer app on https://developer.spotify.com/ to get login credentials (client_id and client_secret) These credentials are necessary in SpotifyClassDef.py

    You will need to download the desktop application for Neo4j. You should create a database on Neo4j and then add your database information to BuildNetwork.py

    Line to be edited: n4jconn = Neo4jConnection(uri='bolt://localhost:7687', user='neo4j', pwd='password')

    At the bottom of SpotifyClassDef.py a code snippet is available to generate nodes and edges for the Pollen playlist and the song passionfruit by drake

    At the bottom of BuildNetwork.py a code snippet is available to generate nodes and edges for Pollen playlist and the song dum surfer. These nodes and edges are then uploaded to neo4j.

    To Visualize the data go to the neo4j browser and enter cypher command Match (n) Return n

Spotify API reference: https://developer.spotify.com/documentation/web-api/reference/#/operations/get-audio-features



P.S. You can VISUALLY INTERPRET THE DATA GENERATED BELOW USE GEPHI https://gephi.org/

first create a spotify developer app on developer.spotify.com to get login credentials (client_id and client_secret)

At the bottom of SpotifyClassDef.py a code snippet is available to generate nodes and edges for the Pollen playlist and the song passionfruit by drake

The nodes and edges will generate csv files which can be viualized when uploaded into gephi
