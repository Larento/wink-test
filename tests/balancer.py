import unittest
from collections import Counter

import httpx

from tests.utils import get_random_video_url, patch_environ
from wink_test.main import app


class TestBalancerRatio(unittest.IsolatedAsyncioTestCase):
    """
    Тестирование распределения запросов на соответствие настроенному отношению редиректов на CDN/origin сервера.
    """

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


if __name__ == "__main__":
    unittest.main()
