import argparse
import asyncio
import importlib

from heekkr.resolver_pb2 import SearchRequest
from heekkr.resolver_pb2_grpc import ResolverServicer


parser = argparse.ArgumentParser()
parser.add_argument("-r", "--resolvers", action="append", required=True)
subparsers = parser.add_subparsers(title="command", dest="command", required=True)

parser_libraries = subparsers.add_parser("libraries")

parser_search = subparsers.add_parser("search")
parser_search.add_argument("keyword")
parser_search.add_argument("-l", "--library-ids", action="append", required=True)


async def main():
    args = parser.parse_args()
    resolvers: list[ResolverServicer] = [
        getattr(importlib.import_module(f".{rs}", "app.resolvers"), "Resolver")()
        for rs in args.resolvers
    ]

    match args.command:
        case "libraries":
            for resolver in resolvers:
                resp = await resolver.GetLibraries(None, None)
                for lib in resp.libraries:
                    print(f"{lib.id:16s} : {lib.name}")
        case "search":
            for resolver in resolvers:
                async for res in resolver.Search(
                    SearchRequest(library_ids=args.library_ids, term=args.keyword),
                    None,
                ):
                    print(res)


asyncio.run(main())
