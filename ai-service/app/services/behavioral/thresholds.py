"""
Clinical thresholds and sub-score weights for the Behavioral Intelligence module (AI-07).

All constants below are sourced from published pediatric / addiction literature. Values
are intentionally conservative and auditable — never tune them from benchmark results;
tune the scoring saturation curves in the scorers instead.

Sources
-------
1. American Academy of Pediatrics (AAP). "Media and Young Minds." Pediatrics, 2016;
   and AAP "Beyond screen time" family media plan update, 2023.
   https://www.aap.org/en/patient-care/media-and-children/

2. World Health Organization (WHO). "Guidelines on physical activity, sedentary
   behaviour and sleep for children under 5 years of age." Geneva: WHO, 2019.
   ISBN 978-92-4-155053-6.

3. American Academy of Sleep Medicine (AASM). "Recommended Amount of Sleep for
   Pediatric Populations: A Consensus Statement." J Clin Sleep Med, 2016.
   https://aasm.org/

4. Panova T., Carbonell X. "Is smartphone addiction really an addiction?"
   Journal of Behavioral Addictions, 2018 Jun 1;7(2):252-259.
   doi:10.1556/2006.7.2018.49

5. Kwon M., Lee J.-Y., Won W.-Y., et al. "Development and Validation of a
   Smartphone Addiction Scale (SAS)." PLoS ONE, 2013;8(2):e56936.
   doi:10.1371/journal.pone.0056936
"""

from __future__ import annotations

from typing import Final


# === Daily screen-time limits by age bracket (minutes) ===
# Sources: (1) AAP 2016/2023, (2) WHO 2019.
# Reading: key is inclusive age range [lo, hi]; value is recommended daily maximum.
AGE_SCREEN_TIME_MAX_MINUTES: Final[dict[tuple[int, int], int]] = {
    (2, 5): 60,
    (6, 12): 120,
    (13, 18): 180,
}


# === Nocturnal usage window ===
# Source: (3) AASM pediatric sleep consensus — sustained evening/night screen exposure
# suppresses melatonin and delays sleep onset.
NOCTURNAL_WINDOW_START_HOUR: Final[int] = 22  # 22:00 local
NOCTURNAL_WINDOW_END_HOUR: Final[int] = 7  # 07:00 local (exclusive)
NOCTURNAL_CRITICAL_MINUTES: Final[int] = 30  # clinically concerning threshold / night


# === Compulsivity thresholds ===
# Source: (4) Panova & Carbonell 2018 — phone "checking" compulsivity correlates with
# very high daily session counts and short "stub" sessions.
COMPULSIVITY_SESSION_COUNT_THRESHOLD: Final[int] = 50
COMPULSIVITY_SHORT_SESSION_SEC: Final[int] = 30


# === Escalation threshold ===
# Source: (5) Kwon et al. 2013 (SAS) — sustained week-over-week growth is an
# escalation indicator; 20 % weekly slope is used as the concerning cut-off.
ESCALATION_WEEKLY_SLOPE_THRESHOLD: Final[float] = 0.2


# === Sub-score weights — global addiction score (must sum to 1.0) ===
ADDICTION_WEIGHTS: Final[dict[str, float]] = {
    "intensity": 0.25,
    "compulsivity": 0.20,
    "nocturnal": 0.20,
    "escalation": 0.20,
    "imbalance": 0.15,
}


# === Sub-score weights — global wellbeing score (must sum to 1.0) ===
WELLBEING_WEIGHTS: Final[dict[str, float]] = {
    "screen_balance": 0.20,
    "content_quality": 0.25,
    "real_activity": 0.20,
    "sleep": 0.20,
    "family_interaction": 0.15,
}


# === Fallback thresholds for out-of-bracket ages ===
_ADOLESCENT_FALLBACK_MINUTES: Final[int] = 180  # used for 18+
_UNDER_TWO_MINUTES: Final[int] = 0  # WHO: no screen time under 2y


def get_age_screen_threshold(age_years: int) -> int:
    """
    Clinical daily screen-time limit (minutes) for a given age.

    Brackets follow AAP/WHO guidance. Ages below 2 return ``0`` (WHO: no recommended
    screen time). Ages above 18 fall back to the adolescent bracket (no pediatric
    guideline exists past 18, but the module targets minors so adolescent limits are
    the safest continuation).

    Args:
        age_years: Integer age in years; negative values are clamped to the under-2
            fallback.

    Returns:
        int: Recommended daily maximum screen time in minutes.
    """
    if age_years < 2:
        return _UNDER_TWO_MINUTES
    for (lo, hi), minutes in AGE_SCREEN_TIME_MAX_MINUTES.items():
        if lo <= age_years <= hi:
            return minutes
    return _ADOLESCENT_FALLBACK_MINUTES
