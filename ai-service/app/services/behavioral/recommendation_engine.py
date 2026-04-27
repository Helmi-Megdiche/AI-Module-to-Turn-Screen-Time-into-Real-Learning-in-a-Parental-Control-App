from __future__ import annotations

from app.contracts.behavioral import BehavioralAnalysisResponse, RecommendationItem


def _subscore_map(response: BehavioralAnalysisResponse) -> dict[str, float]:
    merged: dict[str, float] = {}
    for sub in response.addiction_subscores:
        merged[sub.name] = float(sub.value)
    for sub in response.wellbeing_subscores:
        merged[sub.name] = float(sub.value)
    return merged


def _item(
    *,
    type_: str,
    severity: str,
    message_fr: str,
    action_payload: dict,
    target_audience: str,
    triggering_subscore: str | None,
    triggering_value: float | None,
) -> RecommendationItem:
    return RecommendationItem.model_validate(
        {
            "type": type_,
            "severity": severity,
            "messageFr": message_fr,
            "actionPayload": action_payload,
            "targetAudience": target_audience,
            "triggeringSubscore": triggering_subscore,
            "triggeringValue": triggering_value,
        }
    )


def _rule_screen_curfew(subscores: dict[str, float]) -> RecommendationItem | None:
    value = subscores.get("nocturnal", 0.0)
    if value <= 0.6:
        return None
    return _item(
        type_="screen_curfew",
        severity="high",
        message_fr="L'usage nocturne est marqué. Une coupure d'écran à partir de 21h aiderait à préserver la qualité du sommeil.",
        action_payload={"mission_trigger": "digital_detox_evening", "curfew_hour": 21},
        target_audience="parent",
        triggering_subscore="nocturnal",
        triggering_value=value,
    )


def _rule_weekly_escalation_alert(subscores: dict[str, float]) -> RecommendationItem | None:
    value = subscores.get("escalation", 0.0)
    if value <= 0.5:
        return None
    return _item(
        type_="weekly_escalation_alert",
        severity="high",
        message_fr="La durée d'usage augmente sensiblement d'une semaine à l'autre. Il peut être utile d'en discuter avec l'enfant et de fixer un palier.",
        action_payload={"mission_trigger": "weekly_usage_conversation"},
        target_audience="parent",
        triggering_subscore="escalation",
        triggering_value=value,
    )


def _rule_daily_limit_reminder(subscores: dict[str, float]) -> RecommendationItem | None:
    value = subscores.get("intensity", 0.0)
    # Threshold aligns with ~1.5x the age-based clinical daily limit (AAP-derived).
    # saturating_score >= 0.55 corresponds to ~1.6x inflection.
    if value <= 0.55:
        return None
    return _item(
        type_="daily_limit_reminder",
        severity="medium",
        message_fr="Le temps d'écran quotidien dépasse les repères recommandés pour cet âge. Envisagez une limite journalière progressive.",
        action_payload={"mission_trigger": "daily_limit_setup"},
        target_audience="parent",
        triggering_subscore="intensity",
        triggering_value=value,
    )


def _rule_session_break(subscores: dict[str, float]) -> RecommendationItem | None:
    value = subscores.get("compulsivity", 0.0)
    # Threshold aligns with saturating_score inflection: compulsivity >= 0.5
    # indicates multiple compulsivity signals at or above clinical levels.
    if value <= 0.5:
        return None
    return _item(
        type_="session_break",
        severity="medium",
        message_fr="De nombreuses ouvertures courtes indiquent un usage fragmenté. Proposer des pauses structurées toutes les 30 minutes peut aider.",
        action_payload={"mission_trigger": "mindful_break", "interval_minutes": 30},
        target_audience="both",
        triggering_subscore="compulsivity",
        triggering_value=value,
    )


def _rule_imbalance_warning(subscores: dict[str, float]) -> RecommendationItem | None:
    value = subscores.get("imbalance", 0.0)
    if value <= 0.7:
        return None
    return _item(
        type_="imbalance_warning",
        severity="medium",
        message_fr="L'équilibre entre écran et signaux protecteurs (contenu éducatif, missions accomplies) paraît fragile. Renforcer les alternatives peut aider à rééquilibrer.",
        action_payload={"mission_trigger": "balance_reinforcement"},
        target_audience="parent",
        triggering_subscore="imbalance",
        triggering_value=value,
    )


def _rule_real_activity_prompt(subscores: dict[str, float]) -> RecommendationItem | None:
    value = subscores.get("real_activity", 0.0)
    if value >= 0.3:
        return None
    return _item(
        type_="real_activity_prompt",
        severity="medium",
        message_fr="Les missions hors écran sont peu accomplies. Proposer une activité concrète courte et valorisante peut relancer la dynamique.",
        action_payload={"mission_trigger": "real_world_short_mission"},
        target_audience="both",
        triggering_subscore="real_activity",
        triggering_value=value,
    )


def _rule_educational_boost(subscores: dict[str, float]) -> RecommendationItem | None:
    content_quality = subscores.get("content_quality", 0.0)
    intensity = subscores.get("intensity", 0.0)
    if not (content_quality < 0.3 and intensity > 0.3):
        return None
    return _item(
        type_="educational_boost",
        severity="low",
        message_fr="Peu de contenus éducatifs sont détectés dans l'usage récent. Ajouter des ressources d'apprentissage adaptées à l'âge peut enrichir l'expérience.",
        action_payload={"mission_trigger": "educational_content_suggestion"},
        target_audience="parent",
        triggering_subscore="content_quality",
        triggering_value=content_quality,
    )


def _rule_family_time_suggestion(subscores: dict[str, float]) -> RecommendationItem | None:
    value = subscores.get("family_interaction", 0.0)
    if value >= 0.3:
        return None
    return _item(
        type_="family_time_suggestion",
        severity="low",
        message_fr="L'engagement autour des missions partagées est faible. Un moment familial court autour d'une activité commune peut renforcer le lien.",
        action_payload={"mission_trigger": "family_activity_suggestion"},
        target_audience="parent",
        triggering_subscore="family_interaction",
        triggering_value=value,
    )


def _rule_balance_celebration(
    response: BehavioralAnalysisResponse,
    has_high_severity: bool,
) -> RecommendationItem | None:
    # 0.70 selects profiles that are clearly in the balanced zone without
    # requiring near-perfect scores. Still prevents false-positive celebration
    # (low/moderate wellbeing never fires).
    if has_high_severity or float(response.wellbeing_score) <= 0.70:
        return None
    return _item(
        type_="balance_celebration",
        severity="positive",
        message_fr="Les indicateurs d'usage sont équilibrés cette semaine. Continuer à valoriser les activités hors écran maintiendra cette dynamique positive.",
        action_payload={},
        target_audience="parent",
        triggering_subscore=None,
        triggering_value=float(response.wellbeing_score),
    )


def generate_recommendations(response: BehavioralAnalysisResponse) -> list[RecommendationItem]:
    """
    Map the scoring output to a list of actionable, French, non-stigmatizing
    recommendations. Pure function, deterministic, no I/O.
    Ordering: high severity first, then medium, low, positive. Positive
    ("balance_celebration") is emitted only when NO high-severity recommendation
    triggered — the two messages are semantically incompatible.
    Word "addiction" (and variants) MUST NEVER appear in message_fr.
    """
    subscores = _subscore_map(response)
    high = [
        _rule_screen_curfew(subscores),
        _rule_weekly_escalation_alert(subscores),
    ]
    medium = [
        _rule_daily_limit_reminder(subscores),
        _rule_session_break(subscores),
        _rule_imbalance_warning(subscores),
        _rule_real_activity_prompt(subscores),
    ]
    low = [
        _rule_educational_boost(subscores),
        _rule_family_time_suggestion(subscores),
    ]
    ordered = [rec for rec in [*high, *medium, *low] if rec is not None]
    has_high = any(rec.severity == "high" for rec in ordered)
    celebration = _rule_balance_celebration(response, has_high)
    if celebration is not None:
        ordered.append(celebration)
    return ordered
