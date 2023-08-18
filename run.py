import argparse
import asyncio
import concurrent.futures
import importlib

from grpc.aio import server as create_grpc_server

from heekkr.resolver_pb2_grpc import add_ResolverServicer_to_server, ResolverServicer


parser = argparse.ArgumentParser()
parser.add_argument("resolver", type=str)
parser.add_argument("-b", "--bind", type=str, default="[::]:50051")


async def serve(service: ResolverServicer, bind: str):
    server = create_grpc_server(concurrent.futures.ThreadPoolExecutor(max_workers=4))
    add_ResolverServicer_to_server(service, server)
    server.add_insecure_port(bind)
    await server.start()
    print(f"Server started at {bind}")
    await server.wait_for_termination()


def main():
    args = parser.parse_args()
    service = getattr(
        importlib.import_module(f".{args.resolver}", "app.resolvers"),
        "Resolver",
    )()
    asyncio.run(serve(service, args.bind))


if __name__ == "__main__":
    main()
