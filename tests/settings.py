import unittest
from fractions import Fraction

from pydantic import HttpUrl, ValidationError

from tests.utils import patch_environ
from wink_test.balancer import parse_redirect_ratio
from wink_test.settings import Settings


class TestSettingsWithPythonValues(unittest.TestCase):
    """
    Настройки устанавливаются из значений Python.
    """

    def test_well_formed_values(self):
        settings = Settings(cdn_host=HttpUrl("http://cdn-domain"), redirect_ratio=parse_redirect_ratio("10:1"))
        self.assertEqual(settings.cdn_host.host, "cdn-domain")
        self.assertEqual(settings.redirect_ratio, Fraction(10, 1))

    def test_ill_formed_value_for_cdn_host(self):
        with self.assertRaises(ValidationError):
            Settings(cdn_host=HttpUrl("123456789"), redirect_ratio=parse_redirect_ratio("10:1"))

    def test_non_http_cdn_host(self):
        with self.assertRaises(ValidationError):
            Settings(cdn_host=HttpUrl("ftp://cdn-domain"), redirect_ratio=parse_redirect_ratio("10:1"))

    def test_ill_formed_value_for_redirect_ratio(self):
        with self.assertRaises(ValidationError):
            Settings(cdn_host=HttpUrl("123456789"), redirect_ratio=parse_redirect_ratio("abcdef"))

    def test_negative_cdn_redirect_count(self):
        with self.assertRaises(ValidationError):
            Settings(cdn_host=HttpUrl("http://cdn-domain"), redirect_ratio=parse_redirect_ratio("-10:1"))

    def test_negative_origin_servers_redirect_count(self):
        with self.assertRaises(ValidationError):
            Settings(cdn_host=HttpUrl("http://cdn-domain"), redirect_ratio=parse_redirect_ratio("10:-1"))


class TestSettingsFromEnv(unittest.TestCase):
    """
    Настройки устанавливаются из значений переменных окружения.
    """

    @patch_environ(BALANCER_CDN_HOST="http://cdn-domain", BALANCER_REDIRECT_RATIO="10:1")
    def test_well_formed_values(self):
        settings = Settings()  # type: ignore
        self.assertEqual(settings.cdn_host.host, "cdn-domain")
        self.assertEqual(settings.redirect_ratio, Fraction(10, 1))

    @patch_environ(BALANCER_CDN_HOST="123456789", BALANCER_REDIRECT_RATIO="10:1")
    def test_ill_formed_value_for_cdn_host(self):
        with self.assertRaises(ValueError):
            Settings()  # type: ignore

    @patch_environ(BALANCER_CDN_HOST="ftp://cdn-domain", BALANCER_REDIRECT_RATIO="10:1")
    def test_non_http_cdn_host(self):
        with self.assertRaises(ValueError):
            Settings()  # type: ignore

    @patch_environ(BALANCER_CDN_HOST="http://cdn-domain", BALANCER_REDIRECT_RATIO="abcdef")
    def test_ill_formed_value_for_redirect_ratio(self):
        with self.assertRaises(ValidationError):
            Settings()  # type: ignore

    @patch_environ(BALANCER_CDN_HOST="http://cdn-domain", BALANCER_REDIRECT_RATIO="-10:1")
    def test_negative_cdn_redirect_count(self):
        with self.assertRaises(ValidationError):
            Settings()  # type: ignore

    @patch_environ(BALANCER_CDN_HOST="http://cdn-domain", BALANCER_REDIRECT_RATIO="10:-1")
    def test_negative_origin_servers_redirect_count(self):
        with self.assertRaises(ValidationError):
            Settings()  # type: ignore


if __name__ == "__main__":
    unittest.main()
