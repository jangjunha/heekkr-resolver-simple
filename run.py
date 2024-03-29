import argparse
import asyncio
import concurrent.futures
import os

from grpc.aio import server as create_grpc_server
from heekkr.resolver_pb2_grpc import add_ResolverServicer_to_server
from sentry_sdk import init as init_sentry

from app import Resolver


parser = argparse.ArgumentParser()
parser.add_argument("-b", "--bind", type=str, default="[::]:50051")


async def serve(bind: str):
    server = create_grpc_server(concurrent.futures.ThreadPoolExecutor(max_workers=4))
    add_ResolverServicer_to_server(Resolver(), server)
    server.add_insecure_port(bind)
    await server.start()
    print(f"Server started at {bind}")
    await server.wait_for_termination()


def main():
    args = parser.parse_args()

    if dsn := os.environ.get("SENTRY_DSN"):
        init_sentry(
            dsn=dsn,
            traces_sample_rate=1.0,
            profiles_sample_rate=0.05,
        )

    asyncio.run(serve(args.bind))


if __name__ == "__main__":
    main()
