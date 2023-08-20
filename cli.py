import argparse
import asyncio

from heekkr.resolver_pb2 import GetLibrariesRequest, SearchRequest

from app import Resolver


parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(title="command", dest="command", required=True)

parser_libraries = subparsers.add_parser("libraries")

parser_search = subparsers.add_parser("search")
parser_search.add_argument("keyword")
parser_search.add_argument("-l", "--library-ids", action="append", required=True)


async def main():
    args = parser.parse_args()
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
            async for res in resolver.Search(
                SearchRequest(library_ids=args.library_ids, term=args.keyword),
                None,
            ):
                print(res)


asyncio.run(main())
