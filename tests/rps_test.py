"""
Тестирование показателя количества запросов в секунду. Для демонстрации того, что сервис может обработать не менее 1000 запросов в секунду вполне подходит.
"""

import asyncio
import itertools
import math
import os
import resource
import statistics
import subprocess
import time
from concurrent import futures

import aiohttp

from tests.utils import external_services, get_random_video_url, wait_for_balancer_api

balancer_host = "127.0.0.1:3000"

balancer_env = {
    **os.environ.copy(),
    "BALANCER_CDN_HOST": "http://cdn-host",
    "BALANCER_REDIRECT_RATIO": "3:1",
    "BALANCER_REDIS_URL": "redis://localhost",
}

balancer_start_cmd = [
    "gunicorn",
    "wink_test.main:app",
    "--bind",
    balancer_host,
    "--workers",
    # 4 ядра * 2 потока + 1 воркер для задач FastAPI
    "9",
    "--worker-class",
    "uvicorn.workers.UvicornWorker",
]


async def make_request(client: aiohttp.ClientSession, index: int):
    random_video_url = get_random_video_url(index + 1)
    response = await client.get("/", params={"video": random_video_url}, allow_redirects=False)
    return response.headers.get("location")


async def make_requests(index_range: range):
    async with aiohttp.ClientSession(base_url=f"http://{balancer_host}", raise_for_status=True) as client:
        await wait_for_balancer_api(client)
        tasks = [make_request(client, i) for i in index_range]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        exc: list[Exception] = []
        for result in results:
            match result:
                case Exception():
                    exc.append(result)
                case _:
                    pass

        if len(exc) / len(results) > 0.1:
            raise ValueError("Too many errors in requests.")


def requests_maker_thread_main(index_range: range):
    asyncio.run(make_requests(index_range))


def main():
    rps_values: list[int] = []

    with subprocess.Popen(
        balancer_start_cmd,
        env=balancer_env,
        shell=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) as balancer_process:
        number_of_requests = 1000
        requests_per_thread = 300
        workers_count = math.ceil(number_of_requests / requests_per_thread)

        with futures.ThreadPoolExecutor(max_workers=workers_count) as executor:
            for round_index in range(1, 11):
                index_ranges = [
                    range(start_index, stop_index)
                    for start_index, stop_index in itertools.pairwise(
                        range(0, number_of_requests + 1, requests_per_thread)
                    )
                ]
                start_time = time.time()

                try:
                    result_futures = [executor.submit(requests_maker_thread_main, x) for x in index_ranges]
                    for fut in futures.as_completed(result_futures):
                        fut.result()
                    exec_time = time.time() - start_time

                    requests_per_second = int(number_of_requests / exec_time)
                    rps_values.append(requests_per_second)

                    print(
                        f"[Round {round_index}] Balancer handled {number_of_requests} requests in {exec_time:.3f} seconds. RPS: {requests_per_second}"
                    )
                except Exception as e:
                    print(f"[Round {round_index}] Round failed - {type(e).__name__}: {e}")
                finally:
                    time.sleep(0.5)

        if len(rps_values) > 0:
            median_rps = statistics.median(rps_values)
            print(f"Median PRS: {median_rps}")
        else:
            print("All rounds failed.")

        print("Killing balancer process...")
        balancer_process.terminate()
        balancer_process.wait()


if __name__ == "__main__":
    # Повышаем лимит открытых соединений, чтобы не было ошибок 'Too many files open'
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    if soft < 1024:
        resource.setrlimit(resource.RLIMIT_NOFILE, (1024, hard))

    with external_services():
        main()
