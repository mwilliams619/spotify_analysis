from neo4j import GraphDatabase
import spotifyClassDef
import sqlite3


class Neo4jConnection:

    def __init__(self, uri, user, pwd):
        self.__uri = uri
        self.__user = user
        self.__pwd = pwd
        self.__driver = None
        try:
            self.__driver = GraphDatabase.driver(self.__uri, auth=(self.__user, self.__pwd))
        except Exception as e:
            print("Failed to create the driver:", e)

    def close(self):
        if self.__driver is not None:
            self.__driver.close()

    def query(self, query, parameters=None, db=None):
        assert self.__driver is not None, "Driver not initialized!"
        session = None
        response = None
        try:
            session = self.__driver.session(database=db) if db is not None else self.__driver.session()
            response = list(session.run(query, parameters))
        except Exception as e:
            print("Query failed:", e)
        finally:
            if session is not None:
                session.close()
        return response


n4jconn = Neo4jConnection(uri='bolt://localhost:7687', user='neo4j', pwd='pass')


def _clean_genre(genre):
    genre = genre.strip('[]')
    genre = genre.replace("'", "")
    genre = list(genre.split(", "))
    for i, item in enumerate(genre):
        if ' ' in item:
            item = item.replace(' ', '_')
            genre[i] = item
    cleaned_genre = str(genre).strip('[]')
    cleaned_genre = cleaned_genre.replace("'", "")
    cleaned_genre = cleaned_genre.replace("&", "n")
    cleaned_genre = cleaned_genre.replace('-', '_')
    cleaned_genre = cleaned_genre.replace(',', ':')
    if cleaned_genre == "":
        cleaned_genre = "NULL"
    return cleaned_genre


def _clean_name(label):
    label = label.replace("'", "")
    return label


def plot_network(playlist, song, conn=n4jconn):
    _comparison_track = spotifyClassDef.Track(song)
    # TODO need to get edges for all the songs in playlists rn its just finding the similarities between the one comp
    #  track and the playlist

    # this generates edges for your playlist against a comparison track
    edges, nodes = spotifyClassDef.Playlist(playlist).track_test(comp_song=_comparison_track)

    # this generates edges for your playlist among the songs in your playlist
    edges1, nodes1 = spotifyClassDef.Playlist(playlist).similarness()
    edges = edges + edges1
    transaction_execution_commands = []
    # This portion adds nodes
    for node in nodes:
        label, num_id, dance, energy, mode, valence, bpm, key, popularity, genre = node
        if label == "Label":
            continue
        else:
            genre = _clean_genre(genre)
            label = _clean_name(label)
            create_statement = "CREATE (n" + str(num_id) + ":" + genre + \
                               "{name: '" + str(label) + "' , danceability: " + str(dance) + ", energy: " + str(
                                energy) + ", id: " + str(num_id) + \
                               ", mode: " + str(mode) + ", valence: " + str(valence) + ", tempo: " + str(bpm) + \
                               ", song_key: " + str(key) + ", popularity: " + str(popularity) + "})"
            transaction_execution_commands.append(create_statement)

    # TODO fix the relationships
    for edge in edges:
        source, target, edge_weight = edge
        if source == "Source":
            continue
        else:
            relation_statement = "MATCH (a) MATCH (b) " \
                                 "WHERE a.id =" + str(source) + " AND b.id =" + str(target) +\
                " CREATE (a)-[:Similar {weight:" + str(edge_weight) + "}] -> (b)" +\
                " CREATE (b)-[:Similar {weight:" + str(edge_weight) + "}] -> (a)"
            transaction_execution_commands.append(relation_statement)

    transaction_execution_commands.append("MATCH (n) RETURN n")

    for i in transaction_execution_commands:
        print(i)
        conn.query(i)


plot_network("Pollen", "Dum Surfer")
# TODO fix the neo4j plotting issues
