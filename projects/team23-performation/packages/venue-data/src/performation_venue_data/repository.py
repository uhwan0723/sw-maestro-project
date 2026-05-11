from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from performation_domain import VenueInfo


DATA_PATH = Path(__file__).resolve().parent / "data" / "venues.json"


@dataclass(frozen=True)
class VenueMatch:
  venue: VenueInfo
  alias: str


@dataclass(frozen=True)
class VenueAlias:
  venue: VenueInfo
  alias: str
  normalized_alias: str


class VenueRepository:
  def __init__(self, venues: list[VenueInfo]) -> None:
    self._venues = venues
    self._aliases = _build_alias_index(venues)

  @classmethod
  def from_json(cls, path: Path = DATA_PATH) -> "VenueRepository":
    payload = json.loads(path.read_text(encoding="utf-8"))
    return cls([VenueInfo.model_validate(item) for item in payload["venues"]])

  def list_venues(self) -> list[VenueInfo]:
    return list(self._venues)

  def find_by_query(self, query: str) -> VenueInfo | None:
    match = self.find_match_by_query(query)
    return match.venue if match is not None else None

  def find_match_by_query(self, query: str) -> VenueMatch | None:
    matches = self.find_matches_by_query(query)
    matched_venue_names = {match.venue.name for match in matches}
    if len(matched_venue_names) != 1:
      return None
    return matches[0]

  def find_matches_by_query(self, query: str) -> list[VenueMatch]:
    normalized = _normalize_for_match(query)
    matches: list[VenueMatch] = []
    matched_venue_names: set[str] = set()
    for venue_alias in self._aliases:
      if venue_alias.venue.name in matched_venue_names:
        continue
      if venue_alias.normalized_alias in normalized:
        matches.append(VenueMatch(venue=venue_alias.venue, alias=venue_alias.alias))
        matched_venue_names.add(venue_alias.venue.name)
    return matches


@lru_cache(maxsize=1)
def get_default_repository() -> VenueRepository:
  return VenueRepository.from_json()


def _normalize_for_match(value: str) -> str:
  return re.sub(r"[\W_]+", "", value.casefold())


def _build_alias_index(venues: list[VenueInfo]) -> list[VenueAlias]:
  aliases: list[VenueAlias] = []
  seen: set[tuple[str, str]] = set()
  for venue in venues:
    for alias in [venue.name, *venue.aliases]:
      normalized_alias = _normalize_for_match(alias)
      key = (venue.name, normalized_alias)
      if not normalized_alias or key in seen:
        continue
      aliases.append(
        VenueAlias(
          venue=venue,
          alias=alias,
          normalized_alias=normalized_alias,
        )
      )
      seen.add(key)
  return sorted(aliases, key=lambda item: len(item.normalized_alias), reverse=True)
