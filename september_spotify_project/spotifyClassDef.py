import spotipy
from spotipy.oauth2 import SpotifyClientCredentials  # To access authorised Spotify data
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.offline as pyo
from sklearn.metrics.pairwise import cosine_similarity
from statistics import mean

# Login credentials

#  visit spotify api website to create an app and recieve a client id and client secret
client_id = '[your client id]'
client_secret = '[your client_secret]'

client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)

sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)  # spotify object to access API

db = sqlite3.connect("song_props.sqlite", detect_types=sqlite3.PARSE_DECLTYPES)

db.execute("CREATE TABLE IF NOT EXISTS song_props (name TEXT PRIMARY KEY NOT NULL, danceability INTEGER NOT NULL,"
           "energy INTEGER NOT NULL, mode INTEGER NOT NULL, valence INTEGER NOT NULL, tempo INTEGER NOT NULL,"
           "uri TEXT NOT NULL, key INTEGER NOT NULL)")


class SpotSuper:

    def __init__(self, name, category, connection):
        self.name = name
        self._category = category
        self._uri = self.search()
        self.connection_cursor = connection.cursor()
        self.cursor = self.connection_cursor
        if self._category == "track":
            self.catalog = None
        else:
            self.catalog = self.track_list()

    def search(self):
        """ Search for either track/playlist/artist item return uri"""

        # TODO my db contains songs how do I get it to return
        #  artist and playlist uris if I already have their songs in the db

        cursor = db.execute(
            "SELECT name, danceability, energy, mode, valence, tempo, uri, key FROM song_props WHERE (name = ?)",
            (self.name,))
        row = cursor.fetchone()
        if row:
            name, danceability, energy, mode, valence, tempo, uri, key = row
            return uri
        else:
            result = sp.search(q=self._category + ':' + self.name, type=self._category)  # search query

            spotify_obj = result[self._category + 's']['items'][0]
            uri = spotify_obj['uri']
            return uri

    def track_list(self):
        """
        Load tracks on playlist OR artist top track into a dictionary

        :return: catalog: dictionary of songs with their uri
        """
        # cursor = db.execute(
        #     "SELECT name, danceability, energy, mode, valence, tempo, uri, key FROM song_props WHERE (name = ?)",
        #     (song_name,))
        # TODO if playlist is already in cache get info from cache!!
        if self._category == "playlist":
            track_list = []
            for item in sp.playlist_items(self._uri)['items']:
                track_list.append((item['track']['name'], item['track']['uri']))
        elif self._category == "artist":
            track_list = []
            for item in sp.artist_top_tracks(self._uri)['tracks'][:50]:
                track_list.append((item['name'], item['uri']))
        else:
            return None

        catalog = {}
        for track in track_list:
            song, uri = track
            catalog.update({song: uri})

        return catalog

    @staticmethod
    def _properties_dict_gen(song_name, song_uri):
        """
        for use in song_properties generates song properties dict and adds to sqlite table 'song_props'

        :return: dictionary containing: name danceability, energy, mode (major/minor), valence, tempo, uri and key
        """
        song_features = sp.audio_features(song_uri)
        # TODO gotta figure out how to get song name
        cursor = db.execute(
            "SELECT name, danceability, energy, mode, valence, tempo, uri, key FROM song_props WHERE (name = ?)",
            (song_name,))

        cursor.execute("INSERT OR IGNORE INTO song_props VALUES(?,?,?,?,?,?,?,?)",
                       (song_name, song_features[0]['danceability'], song_features[0]['energy'],
                        song_features[0]['mode'], song_features[0]['valence'], song_features[0]['tempo'],
                        song_uri, song_features[0]['key']))
        cursor.connection.commit()

        feature_dict = {'name': song_name,
                        'features': {'danceability': song_features[0]['danceability'],
                                     'energy': song_features[0]['energy'],
                                     'mode': song_features[0]['mode'], 'valence': song_features[0]['valence'],
                                     'tempo': song_features[0]['tempo'] / 100,
                                     # divide tempo so it fits with other data
                                     'uri': song_uri,
                                     'key': song_features[0]['key']}}

        # df = pd.json_normalize(data=feature_dict, max_level=1)
        # df = df.set_index('name')
        # df.to_csv("song_properties.csv", mode='a')
        # print(feature_dict)
        return feature_dict

    def song_properties(self, track=None):
        """
        try to get song info from db if not available create gen new entry with _properties_dict_gen()
        SHOULD BE SINGLE SONGS

        :param track: dictionary from multi_song_properties func containing song_name and song_uri

        :return: dictionary containing: name danceability, energy, mode (major/minor), valence, tempo, uri and key
        """
        try:
            if self._category == 'track':
                song_name = self.name
                song_uri = self._uri
            else:
                song_name = track[0]
                song_uri = track[1]
        except AttributeError:
            song_name = track[0]
            song_uri = track[1]

        cursor = db.execute(
            "SELECT name, danceability, energy, mode, valence, tempo, uri, key FROM song_props WHERE (name = ?)",
            (song_name,))
        # cursor = db.execute(
        #     "SELECT name, danceability, energy, mode, valence, tempo, uri, key FROM song_props WHERE (name = ?)",
        #     (self.name,))
        row = cursor.fetchone()
        if row:
            name, danceability, energy, mode, valence, tempo, uri, key = row
            feature_dict = {'name': name,
                            'features': {'danceability': danceability,
                                         'energy': energy,
                                         'mode': mode, 'valence': valence,
                                         'tempo': tempo,
                                         # divide tempo so it fits with other data
                                         'uri': uri,
                                         'key': key}}
            # print("got from cache")
            return feature_dict
        else:
            self._properties_dict_gen(song_name, song_uri)

    def multi_song_properties(self):
        for track in self.catalog.items():
            # print(track)
            self.song_properties(track=track)

    def _prep_feat_list_to_plot(self):
        """prep feature values to plot"""
        feat_dict = self.song_properties()
        song_name = feat_dict['name']
        feat_dict = feat_dict['features']
        del feat_dict['uri']
        del feat_dict['key']
        print(feat_dict)
        categories = ["danceability", "energy", "mode", "valence", "tempo (divided by 100)"]
        categories = [*categories, categories[0]]
        feat_dict['tempo'] = feat_dict['tempo'] / 100  # scale down the tempo so that it is viewable with other data
        feat_dict['mode'] = feat_dict['mode'] / 5  # scale mode (either a value of 0 or 1)
        # so doesn't skew data, but differences still present
        # TODO experiment with above normalizations to make sure that the weighting works
        feat_list = []
        for key in feat_dict.keys():
            feat_list.append(feat_dict[key])
        feat_list = [*feat_list, feat_list[0]]
        return feat_list, song_name, categories

    def graph(self):
        """Plot feature data on radial graph"""
        feat_list, song_name, categories = self._prep_feat_list_to_plot()
        fig = go.Figure(
            data=[
                go.Scatterpolar(r=feat_list, theta=categories, name=song_name),

            ],
            layout=go.Layout(
                title=go.layout.Title(text=self.name.upper()),
                polar={'radialaxis': {'visible': True}},
                showlegend=True
            )
        )
        pyo.plot(fig)

    def overlay(self, other: object):
        """Overlay plots of feature data on radial graph"""
        feat_list, song_name, categories = self._prep_feat_list_to_plot()
        feat_list_2, other_name, _ = other._prep_feat_list_to_plot()

        fig = go.Figure(
            data=[
                go.Scatterpolar(r=feat_list, theta=categories, name=song_name),
                go.Scatterpolar(r=feat_list_2, theta=categories, name=other_name),

            ],
            layout=go.Layout(
                title=go.layout.Title(text="Song Features Comparison"),
                polar={'radialaxis': {'visible': True}},
                showlegend=True
            )
        )
        pyo.plot(fig)

    @staticmethod
    def _prep_feats_for_cosine_similarity(track=None):
        song_name = track['name']
        feat_dict = track['features']
        del feat_dict['uri']

        # categories = ["danceability", "energy", "mode", "valence", "tempo (divided by 100)", "key"]
        # categories = [*categories, categories[0]]
        feat_dict['tempo'] = feat_dict['tempo'] / 100  # scale down the tempo so that it is viewable with other data
        feat_dict['mode'] = feat_dict['mode'] / 4  # scale mode (either a value of 0 or 1)
        feat_dict['key'] = feat_dict['key'] / 12  # scale key (range of 1 to 12) new highest value is 1

        # TODO experiment with above normalizations to make sure that the weighting works
        feat_list = []
        for key in feat_dict.keys():
            feat_list.append(feat_dict[key])
        return feat_list, song_name

    def similarness(self):
        """Take playlist songs from self.catalog get features for all songs, format data then load in pandas df
        ,run cosine similarity to generate edges, print node list and edge list to files 'spot_node.csv' and
        'spot_edge.csv' respectively, in a format usable by gephi.
        """
        data = []
        cleaned_data = []
        for track in self.catalog.items():
            feat_list = self.song_properties(track=track)
            data.append(feat_list)
        for item in data:
            feat_list, song_name = Playlist._prep_feats_for_cosine_similarity(item)
            # feat_list.append(song_name)
            cleaned_data.append(feat_list)
        # print(cleaned_data)
        df = pd.DataFrame(cleaned_data,
                          columns=["danceability", "energy", "mode",
                                   "valence", "tempo (divided by 100)", "key"])

        # print('->')
        pd.set_option("display.max_rows", None, "display.max_columns", None)
        # print(df)
        # node_heat = []
        # label_x = []
        # label_y = []

        edge_weight = ["Weight"]
        source = ["Source"]
        name = ["Label"]
        num_id = ["ID"]
        target = ["Target"]
        for i, row in enumerate(cosine_similarity(df, df)):
            for index, element in enumerate(row):
                if element > .97 and data[i]['name'] != data[index]['name']:
                    edge_weight.append(1/element)
                    source.append(i)
                    target.append(index)
                    if data[i]['name'] not in name:
                        name.append(data[i]['name'])
                        num_id.append(i)

        edge = list(zip(source, target, edge_weight))
        node = list(zip(name, num_id))
        # print(ready)
        with open("spot_edge.csv", 'w') as edges:
            for source, target, weight in edge:
                print("{},{},{}".format(source, target, weight), file=edges)

        with open("spot_node.csv", 'w') as nodes:
            for n_id, label in node:
                print("{},{}".format(n_id, label), file=nodes)

        # Below is heat map code
        #             node_heat.append(element)
        #             label_x.append(data[i]['name'])
        #             label_y.append(data[index]['name'])
        #             print((data[i]['name'], data[index]['name']))
        # fig = go.Figure(data=go.Heatmap(
        #     x=label_x, y=label_y, z=node_heat, hoverongaps=False))
        # fig.show()

    def track_test(self, comp_song: object):
        # TODO write DOCSTRINGS! And fix code redundancy
        """tests how similar a single track is against all the tracks on the playlist"""

        data = []
        cleaned_data = []
        track_props, song_name = Playlist._prep_feats_for_cosine_similarity(comp_song.song_properties())
        for track in self.catalog.items():
            feat_list = self.song_properties(track=track)
            data.append(feat_list)
        for item in data:
            feat_list, song_name = Playlist._prep_feats_for_cosine_similarity(item)
            # feat_list.append(song_name)
            cleaned_data.append(feat_list)

        # print(cleaned_data)
        # print(track_props)
        df = pd.DataFrame(cleaned_data,
                          columns=["danceability", "energy", "mode",
                                   "valence", "tempo (divided by 100)", "key"])

        df2 = pd.DataFrame(track_props).T
        # print('->')
        pd.set_option("display.max_rows", None, "display.max_columns", None)

        df2.columns = ["danceability", "energy", "mode",
                       "valence", "tempo (divided by 100)", "key"]

        edge_weight = ["Weight"]
        source = ["Source"]
        name = ["Label"]
        num_id = ["ID"]
        target = ["Target"]

        for i, row in enumerate(cosine_similarity(df, df2)):
            for index, element in enumerate(row):
                if element > .97 and data[i]['name'] != data[index]['name']:
                    edge_weight.append(1/element)
                    source.append(i)
                    target.append(index)
                    if data[i]['name'] not in name:
                        name.append(data[i]['name'])
                        num_id.append(i)

        edge = list(zip(source, target, edge_weight))
        node = list(zip(name, num_id))
        with open("comparison_edge.csv", 'w') as edges:
            for source, target, weight in edge:
                print("{},{},{}".format(source, target, weight), file=edges)

        with open("comparison_node.csv", 'w') as nodes:
            for n_id, label in node:
                print("{},{}".format(n_id, label), file=nodes)


class Playlist(SpotSuper):
    def __init__(self, name):
        super().__init__(name=name, category="playlist", connection=conn)
        self.mean_feats = self.mean_playlist_feats(self.catalog)

    @staticmethod
    def mean_playlist_feats(dictionary):

        """
        Average track information from playlist tracks. Track must be from self.catalog

        :param dictionary: self.catalog
        :return: dictionary containing danceability, energy, mode (major/minor), valence, tempo, and key
        """
        dance_list = []
        nrg_list = []
        val_list = []
        tempo_list = []

        majmin_count = {'major': 0, 'minor': 0}
        for track in dictionary:
            song_features = sp.audio_features(dictionary[track])
            dance_list.append(song_features[0]['danceability'])
            nrg_list.append(song_features[0]['energy'])
            val_list.append(song_features[0]['energy'])
            tempo_list.append(song_features[0]['tempo'])

            if song_features[0]['mode'] == 0:
                majmin_count['minor'] += 1
            else:
                majmin_count['major'] += 1
            print('.', end='')

        feature_dict = {'danceability': mean(dance_list), 'energy': mean(nrg_list),
                        'mode': majmin_count, 'valence': mean(val_list),
                        'tempo': mean(tempo_list), }
        # print(feature_dict)
        return feature_dict


class Artist(SpotSuper):
    def __init__(self, name):
        super().__init__(name=name, category="artist", connection=conn)


class Track(SpotSuper):
    def __init__(self, name):
        super().__init__(name=name, category="track", connection=conn)


if __name__ == '__main__':

    #  below is sample code analyzing the POLLEN playlist and how Passionfruit relates and its contents

    conn = sqlite3.connect('song_props.sqlite')
    passionfruit = Track("Passionfruit")
    passionfruit.song_properties()

    # dum_surfer = SpotSuper("dum surfer", "track", conn)
    # dum_surfer.song_properties()
    pollen = Playlist("POLLEN")
    pollen.similarness()
    pollen.track_test(passionfruit)

    # drake = Artist("Drake")
    # drake.track_test(passionfruit)
    # dork = SpotSuper("dork", "track", conn)
    # dork.overlay(dum_surfer)
    # i_might = SpotSuper("I Might slip away if I don't feel nothing", "track", conn)
    # thot = SpotSuper("Thot Tactics", "track", conn)
    # i_might.overlay(thot)
    conn.close()

# TODO I want to see the nodes of tracks clustered together and then add a song and see how the clusters are altered

