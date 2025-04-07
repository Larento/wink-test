import asyncio
import statistics
import time
import unittest
from collections import Counter

import httpx

from tests.utils import patch_environ
from wink_test.main import app


def get_random_video_url(index: int):
    return f"http://s1.origin-cluster/video/${index}/file.m3u8"


async def wait_for_balancer_api(client: httpx.AsyncClient):
    for _ in range(5):
        try:
            response = await client.get("/health", timeout=0.5)
            if response.status_code == 200:
                return
        except TimeoutError:
            continue
    raise TimeoutError


class TestBalancerRatio(unittest.IsolatedAsyncioTestCase):
    @patch_environ(BALANCER_CDN_HOST="http://cdn-domain", BALANCER_REDIRECT_RATIO="3:1")
    async def test_ratio(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            redirect_url_counter = Counter({"cdn": 0, "origin-server": 0})

            for i in range(100):
                random_video_url = get_random_video_url(i)

                response = await client.get("/", params={"video": random_video_url})
                assert response.status_code == 301
                assert response.has_redirect_location

                redirect_url = response.headers["location"]
                if redirect_url == random_video_url:
                    redirect_url_counter.update(["origin-server"])
                else:
                    redirect_url_counter.update(["cdn"])

            assert redirect_url_counter["cdn"] == 75
            assert redirect_url_counter["origin-server"] == 25


class TestBalancerRps(unittest.IsolatedAsyncioTestCase):
    async def test_rps(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            await wait_for_balancer_api(client)

            async def make_request(index: int):
                random_video_url = get_random_video_url(index)
                await client.get("/", params={"video": random_video_url})

            rps_values: list[int] = []
            for round_index in range(7):
                number_of_requests = 1000
                tasks = [make_request(i) for i in range(number_of_requests)]
                start_time = time.time()
                await asyncio.gather(*tasks)
                requests_time = time.time() - start_time
                requests_per_second = int(number_of_requests / requests_time)
                rps_values.append(requests_per_second)
                print(
                    f"[Round {round_index}] Balancer handled {number_of_requests} requests in {requests_time * 1000} milliseconds. RPS: {requests_per_second}"
                )
                await asyncio.sleep(0.5)

            median_rps = statistics.median(rps_values)
            print(f"Median PRS: {median_rps}")


if __name__ == "__main__":
    unittest.main()
