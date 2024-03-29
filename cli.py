import argparse
import asyncio
import logging
import pathlib
import pickle

from heekkr.resolver_pb2 import GetLibrariesRequest, SearchRequest

from app import Resolver


parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", action="store_true")
subparsers = parser.add_subparsers(title="command", dest="command", required=True)

parser_libraries = subparsers.add_parser("libraries")

parser_search = subparsers.add_parser("search")
parser_search.add_argument("keyword")
parser_search.add_argument("-l", "--library-ids", action="append", required=True)
parser_search.add_argument("--export", type=pathlib.Path)


async def main():
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    resolver = Resolver()

    match args.command:
        case "libraries":
            resp = await resolver.GetLibraries(GetLibrariesRequest(), None)
            for lib in resp.libraries:
                coordinate = (
                    f"({lib.coordinate.latitude:.6f}, {lib.coordinate.longitude:.6f})"
                    if lib.coordinate
                    else ""
                )
                print(f"{lib.id:16s} : {lib.name}  {coordinate}")
        case "search":
            entities = []
            async for res in resolver.Search(
                SearchRequest(library_ids=args.library_ids, term=args.keyword),
                None,
            ):
                print(res)
                entities += res.entities
            if args.export:
                with open(args.export, "wb") as f:
                    pickle.dump(entities, f)


asyncio.run(main())
