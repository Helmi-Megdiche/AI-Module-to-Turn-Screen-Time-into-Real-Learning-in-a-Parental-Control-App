from __future__ import annotations

from dataclasses import dataclass

from app.contracts.behavioral import BehavioralAnalysisResponse, MissionSuggestion


@dataclass(frozen=True)
class _MissionCatalogEntry:
    triggering_subscore: str
    subscore_kind: str
    min_age: int
    max_age: int
    description_fr: str


@dataclass(frozen=True)
class _MissionCandidate:
    severity: float
    entry: _MissionCatalogEntry
    raw_value: float


_MISSION_CATALOG: tuple[_MissionCatalogEntry, ...] = (
    _MissionCatalogEntry(
        triggering_subscore="nocturnal",
        subscore_kind="addiction",
        min_age=6,
        max_age=18,
        description_fr="Pose ton téléphone à 21h ce soir et lis 15 minutes avant de dormir.",
    ),
    _MissionCatalogEntry(
        triggering_subscore="nocturnal",
        subscore_kind="addiction",
        min_age=12,
        max_age=18,
        description_fr="Mets ton téléphone en mode avion une heure avant de dormir cette semaine.",
    ),
    _MissionCatalogEntry(
        triggering_subscore="intensity",
        subscore_kind="addiction",
        min_age=6,
        max_age=18,
        description_fr="Fais une pause sans écran d'une heure cet après-midi.",
    ),
    _MissionCatalogEntry(
        triggering_subscore="intensity",
        subscore_kind="addiction",
        min_age=9,
        max_age=18,
        description_fr="Choisis une activité hors écran que tu aimes et accorde-lui 45 minutes aujourd'hui.",
    ),
    _MissionCatalogEntry(
        triggering_subscore="compulsivity",
        subscore_kind="addiction",
        min_age=6,
        max_age=18,
        description_fr="Pose ton téléphone dans une autre pièce pendant 2 heures.",
    ),
    _MissionCatalogEntry(
        triggering_subscore="escalation",
        subscore_kind="addiction",
        min_age=9,
        max_age=18,
        description_fr="Essaie de réduire ton temps d'écran de 30 minutes par rapport à hier.",
    ),
    _MissionCatalogEntry(
        triggering_subscore="real_activity",
        subscore_kind="wellbeing",
        min_age=6,
        max_age=12,
        description_fr="Va jouer dehors ou bouger pendant 30 minutes aujourd'hui.",
    ),
    _MissionCatalogEntry(
        triggering_subscore="real_activity",
        subscore_kind="wellbeing",
        min_age=12,
        max_age=18,
        description_fr="Fais une activité physique de 30 minutes aujourd'hui (vélo, marche, sport).",
    ),
    _MissionCatalogEntry(
        triggering_subscore="family_interaction",
        subscore_kind="wellbeing",
        min_age=6,
        max_age=18,
        description_fr="Passe le dîner en famille ce soir, sans téléphone à table.",
    ),
    _MissionCatalogEntry(
        triggering_subscore="family_interaction",
        subscore_kind="wellbeing",
        min_age=6,
        max_age=12,
        description_fr="Propose un jeu de société à un membre de ta famille pour 30 minutes.",
    ),
    _MissionCatalogEntry(
        triggering_subscore="sleep",
        subscore_kind="wellbeing",
        min_age=6,
        max_age=18,
        description_fr="Couche-toi 30 minutes plus tôt ce soir et laisse ton téléphone hors de la chambre.",
    ),
    _MissionCatalogEntry(
        triggering_subscore="content_quality",
        subscore_kind="wellbeing",
        min_age=9,
        max_age=18,
        description_fr="Choisis une vidéo ou un livre éducatif et passes-y 20 minutes aujourd'hui.",
    ),
)


def _addiction_map(response: BehavioralAnalysisResponse) -> dict[str, float]:
    return {sub.name: float(sub.value) for sub in response.addiction_subscores}


def _wellbeing_map(response: BehavioralAnalysisResponse) -> dict[str, float]:
    return {sub.name: float(sub.value) for sub in response.wellbeing_subscores}


def _difficulty_for_severity(severity: float) -> str:
    if severity < 0.6:
        return "easy"
    if severity < 0.8:
        return "medium"
    return "hard"


def _points_for_difficulty(difficulty: str) -> int:
    return {"easy": 10, "medium": 20, "hard": 30}[difficulty]


def generate_missions(
    response: BehavioralAnalysisResponse,
    age_years: int,
) -> list[MissionSuggestion]:
    """
    Generate up to two diversified child-facing missions.

    Rules:
    - addiction severity uses raw subscore value;
    - wellbeing severity uses (1 - raw subscore value);
    - candidates under 0.5 severity are skipped;
    - at most one selected mission per triggering_subscore.
    """
    addiction_map = _addiction_map(response)
    wellbeing_map = _wellbeing_map(response)

    candidates: list[_MissionCandidate] = []
    for entry in _MISSION_CATALOG:
        if not (entry.min_age <= age_years <= entry.max_age):
            continue
        if entry.subscore_kind == "addiction":
            raw_value = addiction_map.get(entry.triggering_subscore)
            if raw_value is None:
                continue
            severity = raw_value
        else:
            raw_value = wellbeing_map.get(entry.triggering_subscore)
            if raw_value is None:
                continue
            severity = 1.0 - raw_value
        if severity < 0.5:
            continue
        candidates.append(
            _MissionCandidate(
                severity=severity,
                entry=entry,
                raw_value=raw_value,
            )
        )

    candidates.sort(key=lambda c: c.severity, reverse=True)

    selected: list[_MissionCandidate] = []
    seen_subscores: set[str] = set()
    for candidate in candidates:
        if candidate.entry.triggering_subscore in seen_subscores:
            continue
        selected.append(candidate)
        seen_subscores.add(candidate.entry.triggering_subscore)
        if len(selected) == 2:
            break

    missions: list[MissionSuggestion] = []
    for candidate in selected:
        difficulty = _difficulty_for_severity(candidate.severity)
        missions.append(
            MissionSuggestion.model_validate(
                {
                    "descriptionFr": candidate.entry.description_fr,
                    "difficulty": difficulty,
                    "points": _points_for_difficulty(difficulty),
                    "triggeringSubscore": candidate.entry.triggering_subscore,
                    "triggeringValue": candidate.raw_value,
                    "targetAudience": "child",
                }
            )
        )
    return missions
