import logging
import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from ...core.parsers.base import BlockedError
from ...core.parsers.html_parsers import SuperJobHTMLParser

logger = logging.getLogger('celery.module.vacancies_parser.superjob.html')


class SuperJobHTMLParserOverride(SuperJobHTMLParser):
    """
    Переопределение HTML-парсера SuperJob на уровне superjob-модуля.

    Использует устойчивое извлечение по href-шаблону вместо нестабильных CSS-классов.
    """

    _VACANCY_LINK_RE = re.compile(r"^/vakansii/[^?#]+\.html(?:[?#].*)?$")
    _VACANCY_LINK_ANY_RE = re.compile(r"(/vakansii/[^\"'<>\\s]+\\.html(?:\\?[^\"'<>\\s]*)?)")
    _VACANCY_ABSOLUTE_RE = re.compile(r"https?://www\\.superjob\\.ru(/vakansii/[^\"'<>\\s]+\\.html(?:\\?[^\"'<>\\s]*)?)")
    _VACANCY_ID_RE = re.compile(r"-([0-9]+)\.html(?:[?#].*)?$")
    _VACANCY_ID_OLD_RE = re.compile(r"/vakansii/([0-9]+)\.html(?:[?#].*)?$")
    _BLOCK_MARKERS = ("captcha", "cloudflare", "access denied", "forbidden", "bot")

    def validate_config(self, config: Dict[str, Any]) -> bool:
        max_pages = config.get('max_pages')
        if max_pages is not None:
            try:
                if int(max_pages) < 1:
                    return False
            except (TypeError, ValueError):
                return False
        return True

    def discover_items(self, config: Dict[str, Any]) -> List[Dict[str, str]]:
        logger.info("[HTML][SuperJob] Старт discovery c config=%s", config)
        items: List[Dict[str, str]] = []
        seen_ids: Set[str] = set()

        page = 1
        try:
            max_pages = int(config.get("max_pages", 10))
        except (TypeError, ValueError):
            max_pages = 10

        while page <= max_pages:
            try:
                search_url = self._build_search_url(config, page)
                logger.info("[HTML][SuperJob] Запрос страницы %s: %s", page, search_url)
                response = self._make_request(search_url)
                html_text = response.text
                lower_text = html_text.lower()
                if any(marker in lower_text for marker in self._BLOCK_MARKERS):
                    raise BlockedError(f"Обнаружены признаки блокировки на странице {page}")

                logger.debug(
                    "[HTML][SuperJob] Страница %s: status=%s, html_len=%s",
                    page,
                    response.status_code,
                    len(html_text),
                )
                soup = self._parse_html(html_text)

                page_links = self._extract_vacancy_links(soup, html_text)
                logger.info("[HTML][SuperJob] Найдено ссылок на странице %s: %s", page, len(page_links))
                if not page_links:
                    logger.info("[HTML][SuperJob] Ссылки не найдены на странице %s, завершаем", page)
                    break

                for vacancy_url in page_links:
                    vacancy_id = self._extract_vacancy_id(vacancy_url)
                    if not vacancy_id or vacancy_id in seen_ids:
                        continue

                    seen_ids.add(vacancy_id)
                    items.append(
                        {
                            "source_item_id": vacancy_id,
                            "url": urljoin(self.BASE_URL, vacancy_url),
                        }
                    )

                page += 1
            except BlockedError as exc:
                logger.error("[HTML][SuperJob] Блокировка при парсинге страницы %s: %s", page, exc)
                break
            except Exception as exc:
                logger.error(
                    "[HTML][SuperJob] Ошибка на странице %s: %s",
                    page,
                    exc,
                    exc_info=True,
                )
                break

        logger.info("[HTML][SuperJob] Discovery завершён: %s вакансий", len(items))
        return items

    def parse_item(self, item_id: str, url: str) -> Dict[str, Any]:
        """
        Worker-фаза: парсит одну вакансию.

        В orchestration пайплайне вызывается parser.parse_item(...), поэтому
        для HTML режима делегируем в fetch_item.
        """
        return self.fetch_item(item_id, {})

    def _build_search_url(self, config: Dict[str, Any], page: int) -> str:
        params: Dict[str, Any] = {"page": page - 1}
        keywords = (
            config.get("keywords")
            or config.get("keyword")
            or config.get("text")
            or config.get("query")
        )
        if keywords:
            params["keywords"] = str(keywords).strip()
        return f"{self.BASE_URL}/vakansii/?{urlencode(params, doseq=True)}"

    def _extract_vacancy_links(self, soup: BeautifulSoup, html_text: str) -> List[str]:
        links: List[str] = []
        seen: Set[str] = set()

        # Селектор 1: прямые ссылки на вакансии
        for anchor in soup.select("a[href]"):
            href = anchor.get("href")
            if not isinstance(href, str):
                continue
            if self._VACANCY_LINK_RE.match(href) and href not in seen:
                links.append(href)
                seen.add(href)

        # Селектор 2: абсолютные URL в атрибутах
        for anchor in soup.select("a[href*='superjob.ru/vakansii/']"):
            href = anchor.get("href")
            if not isinstance(href, str):
                continue
            for match in self._VACANCY_ABSOLUTE_RE.findall(href):
                if match not in seen:
                    links.append(match)
                    seen.add(match)

        # Селектор 3: fallback по сырому HTML (в т.ч. JS/JSON блобы)
        for match in self._VACANCY_LINK_ANY_RE.findall(html_text):
            if match not in seen:
                links.append(match)
                seen.add(match)

        return links

    def _extract_vacancy_id(self, vacancy_url: str) -> Optional[str]:
        match = self._VACANCY_ID_RE.search(vacancy_url)
        if match:
            return match.group(1)

        old_match = self._VACANCY_ID_OLD_RE.search(vacancy_url)
        if old_match:
            return old_match.group(1)

        fallback = vacancy_url.split("/vakansii/")[-1].split(".html")[0]
        return fallback if fallback.isdigit() else None
