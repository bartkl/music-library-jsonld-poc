import json
from pyld import jsonld
import sqlite3


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
    """)
    albums = {"albums": [dict(row) for row in cur.fetchall()]}

    return albums


def get_albums(conn):
    albums = fetch_albums(conn)
    type_ =  "schema:MusicRelease"  # TODO: Obtain from JSON Schema in OpenAPI spec (or LinkML schema)

    for album in albums["albums"]:
        album["type"] = type_

    return albums


if __name__ == "__main__":
    conn = sqlite3.connect("data/library.db")
    albums = get_albums(conn)

    # Write albums data in plain JSON.
    with open("response.json", mode="w") as f:
        json.dump(albums, f)

    # LD stuff

    with open("response.ld.json", mode="r") as f:
        albums_ld = json.load(f)

    with open("albums.context.ld.json") as f:
        albums_context = json.load(f)

    expanded = jsonld.expand({"@context": albums_context["@context"], **albums_ld})
    print(json.dumps(expanded))

    # print(json.dumps(albums_ld["@context"]))

    # compacted = jsonld.compact(albums_ld, albums_ld["@context"])
    # print(json.dumps(compacted))
