"""Core port interfaces."""

from src.core.ports.evaluator_port import EvaluatorPort
from src.core.ports.output_port import OutputPort
from src.core.ports.scraper_port import ScraperPort

__all__ = ["ScraperPort", "EvaluatorPort", "OutputPort"]
