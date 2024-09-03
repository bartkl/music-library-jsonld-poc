import io
import json
import sqlite3

from contextlib import redirect_stdout
from linkml.utils.converter import cli as linkml_convert
from linkml.generators.jsonldcontextgen import ContextGenerator
from pathlib import Path
from pprint import pprint
from pyld import jsonld
from rdflib import Graph

linkml_convert = linkml_convert.callback

LINKML_SCHEMA = Path("schema.yaml")
DATA_DIR = Path("data")
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
DB_FILE = INPUT_DIR / "library.db"


def fetch_albums(conn):
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        select
            a.id,
            albumartist as album_artist,
            album as title,
            genre,
            discogs_albumid as discogs_album_id,
            discogs_artistid as discogs_album_id,
            year,
            original_year,
            comp as is_compilation,
            mb_albumid as musicbrainz_album_id,
            mb_albumartistid as musicbrainz_album_artist_id,
            label,
            country,
            albumtypes as album_types,
            aa.value as rating
        from albums a

        left join album_attributes aa
        on a.id = aa.entity_id
        and aa.key = "rating"

        limit 10
    """)
    albums = [dict(row) for row in cur.fetchall()]

    return albums


def get_albums(conn):
    albums = fetch_albums(conn)
    albums_json = {"albums": albums}

    return albums_json


def convert_to_ld_ttl(json_data, linkml_schema):
    f = io.StringIO()
    with redirect_stdout(f):
        linkml_convert(
            json_data,
            None,
            target_class=None,
            schema=linkml_schema,
            context="",
            input_format="json",
            output_format="ttl",
        )
    ld_ttl_data = f.getvalue()

    return ld_ttl_data


def gen_json_ld_ctx(linkml_schema):
    json_ld_ctx = ContextGenerator(linkml_schema).serialize()

    return json.loads(json_ld_ctx)


def write_data(data, outfile, mode=None, ctx=None):
    with open(outfile, mode="w") as out:
        match mode:
            case "expanded":
                data_expanded = jsonld.expand(data)
                json.dump(data_expanded, out, indent=2)
            case "compacted":
                data_expanded = jsonld.expand(data)
                data_compacted = jsonld.compact(data_expanded, ctx)
                json.dump(data_compacted, out, indent=2)
            case None:  # Regular JSON
                json.dump(data, out, indent=2)
            
        


if __name__ == "__main__":
    conn = sqlite3.connect(DB_FILE)
    albums_json = get_albums(conn)

    albums_ld_ttl = convert_to_ld_ttl(albums_json, str(LINKML_SCHEMA))

    albums_rdf_graph = Graph()
    albums_rdf_graph.parse(data=albums_ld_ttl, format="ttl")

    albums_json_ld_str = albums_rdf_graph.serialize(format="json-ld")
    albums_json_ld = json.loads(albums_json_ld_str)
    albums_json_ld_ctx = gen_json_ld_ctx(LINKML_SCHEMA)

    ### Writing files.

    write_data(albums_json, OUTPUT_DIR / "albums.json")
    write_data(albums_json_ld, OUTPUT_DIR / "albums.ld.expanded.json", mode="expanded")
    write_data(albums_json_ld, OUTPUT_DIR / "albums.ld.compacted.json", mode="compacted", ctx=albums_json_ld_ctx)
