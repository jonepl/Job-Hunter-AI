"""ScraperFactory — builds scraper adapter instances from ScraperName values."""

from src.adapters.scrapers.jsearch import JSearchScraper
from src.adapters.scrapers.linkedin import LinkedInScraper
from src.core.domain.scraper_name import ScraperName
from src.core.ports.scraper_port import ScraperPort


def build_scrapers(active: list[ScraperName]) -> list[ScraperPort]:
    """Build and return scraper instances for the given list of ScraperNames.

    Order of returned scrapers matches the order of the input list.

    Args:
        active: List of ScraperName values identifying which scrapers to build.

    Returns:
        List of ScraperPort instances, one per active scraper name.
    """
    scrapers: list[ScraperPort] = []
    for name in active:
        if name == ScraperName.LINKEDIN:
            scrapers.append(LinkedInScraper())
        elif name == ScraperName.INDEED:
            scrapers.append(JSearchScraper(platform="indeed"))
        elif name == ScraperName.GLASSDOOR:
            scrapers.append(JSearchScraper(platform="glassdoor"))
        elif name == ScraperName.ZIPRECRUITER:
            scrapers.append(JSearchScraper(platform="ziprecruiter"))
    return scrapers
