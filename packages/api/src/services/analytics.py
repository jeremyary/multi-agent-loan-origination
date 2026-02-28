# This project was developed with assistance from AI tools.
"""Analytics service for CEO executive dashboard.

Computes pipeline summary, denial trends, and LO performance metrics
by querying existing Application, Decision, and AuditEvent tables.
All functions are pure async queries -- no side effects.
"""

import logging
from datetime import UTC, datetime, timedelta

from db import Application, Decision
from db.enums import ApplicationStage, DecisionType, LoanType
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.analytics import (
    DenialReason,
    DenialTrendPoint,
    DenialTrends,
    LOPerformanceRow,
    LOPerformanceSummary,
    PipelineSummary,
    StageCount,
    StageTurnTime,
)

logger = logging.getLogger(__name__)

# Stage transitions used for turn time calculations.
# Each tuple is (from_stage, to_stage) representing a meaningful transition.
_TURN_TIME_TRANSITIONS: list[tuple[ApplicationStage, ApplicationStage]] = [
    (ApplicationStage.APPLICATION, ApplicationStage.UNDERWRITING),
    (ApplicationStage.UNDERWRITING, ApplicationStage.CONDITIONAL_APPROVAL),
    (ApplicationStage.CONDITIONAL_APPROVAL, ApplicationStage.CLEAR_TO_CLOSE),
    (ApplicationStage.CLEAR_TO_CLOSE, ApplicationStage.CLOSED),
]


async def get_pipeline_summary(
    session: AsyncSession,
    days: int = 90,
) -> PipelineSummary:
    """Compute pipeline summary metrics.

    Args:
        session: Database session.
        days: Time range in days for historical metrics (turn times, pull-through).

    Returns:
        PipelineSummary with stage counts, pull-through rate, and turn times.
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=days)

    # Stage distribution -- all current applications
    stage_stmt = select(Application.stage, func.count(Application.id)).group_by(Application.stage)
    stage_result = await session.execute(stage_stmt)
    stage_counts = [StageCount(stage=row[0].value, count=row[1]) for row in stage_result.all()]

    total = sum(sc.count for sc in stage_counts)

    # Pull-through rate: closed / total initiated in period
    initiated_stmt = select(func.count(Application.id)).where(Application.created_at >= cutoff)
    initiated_result = await session.execute(initiated_stmt)
    initiated = initiated_result.scalar() or 0

    closed_stmt = select(func.count(Application.id)).where(
        Application.stage == ApplicationStage.CLOSED,
        Application.updated_at >= cutoff,
    )
    closed_result = await session.execute(closed_stmt)
    closed = closed_result.scalar() or 0

    pull_through = (closed / initiated * 100) if initiated > 0 else 0.0

    # Average days to close (applications that reached closed in period)
    avg_close_stmt = select(
        func.avg(func.extract("epoch", Application.updated_at - Application.created_at) / 86400.0)
    ).where(
        Application.stage == ApplicationStage.CLOSED,
        Application.updated_at >= cutoff,
    )
    avg_close_result = await session.execute(avg_close_stmt)
    avg_days_raw = avg_close_result.scalar()
    avg_days_to_close = round(float(avg_days_raw), 1) if avg_days_raw is not None else None

    # Turn times per stage transition
    # We approximate using audit events that record stage changes.
    # Since audit_events track each stage transition with timestamps, we use
    # the application's updated_at as a proxy for the latest transition.
    # For MVP, we compute from (created_at -> closed updated_at) overall
    # and use a simplified per-stage approach based on stage ordering.
    turn_times = await _compute_turn_times(session, cutoff)

    return PipelineSummary(
        total_applications=total,
        by_stage=stage_counts,
        pull_through_rate=round(pull_through, 1),
        avg_days_to_close=avg_days_to_close,
        turn_times=turn_times,
        time_range_days=days,
        computed_at=now,
    )


async def _compute_turn_times(
    session: AsyncSession,
    cutoff: datetime,
) -> list[StageTurnTime]:
    """Compute average turn times between stage transitions using audit events.

    Looks for pairs of audit events with event_type='stage_transition' that
    record the from/to stages in event_data. Falls back to empty list if
    no stage transition events exist (pre-Phase 5 data).
    """
    from db import AuditEvent

    turn_times: list[StageTurnTime] = []

    for from_stage, to_stage in _TURN_TIME_TRANSITIONS:
        # Find audit events where the application transitioned TO to_stage
        # The event_data should contain {"from_stage": ..., "to_stage": ...}
        # We pair these with the timestamp of the previous stage entry.

        # Approach: for each application that has reached to_stage, find the
        # time between the stage_transition event TO from_stage and TO to_stage.
        to_events = (
            select(
                AuditEvent.application_id,
                AuditEvent.timestamp.label("to_ts"),
            )
            .where(
                AuditEvent.event_type == "stage_transition",
                AuditEvent.timestamp >= cutoff,
                AuditEvent.event_data["to_stage"].as_string() == to_stage.value,
            )
            .subquery("to_events")
        )

        from_events = (
            select(
                AuditEvent.application_id,
                AuditEvent.timestamp.label("from_ts"),
            )
            .where(
                AuditEvent.event_type == "stage_transition",
                AuditEvent.event_data["to_stage"].as_string() == from_stage.value,
            )
            .subquery("from_events")
        )

        avg_stmt = (
            select(
                func.avg(
                    func.extract("epoch", to_events.c.to_ts - from_events.c.from_ts) / 86400.0
                ),
                func.count(),
            )
            .select_from(to_events)
            .join(
                from_events,
                to_events.c.application_id == from_events.c.application_id,
            )
            .where(to_events.c.to_ts > from_events.c.from_ts)
        )

        result = await session.execute(avg_stmt)
        row = result.one()
        avg_days = row[0]
        sample = row[1] or 0

        if avg_days is not None and sample > 0:
            turn_times.append(
                StageTurnTime(
                    from_stage=from_stage.value,
                    to_stage=to_stage.value,
                    avg_days=round(float(avg_days), 1),
                    sample_size=sample,
                )
            )

    return turn_times


async def get_denial_trends(
    session: AsyncSession,
    days: int = 90,
    product: str | None = None,
) -> DenialTrends:
    """Compute denial rate metrics.

    Args:
        session: Database session.
        days: Time range in days.
        product: Optional loan type filter (e.g. 'conventional_30').

    Returns:
        DenialTrends with overall rate, time-based trend, and top reasons.
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=days)

    # Base query: decisions in the time range, optionally filtered by product
    base_filter = [Decision.created_at >= cutoff]
    needs_app_join = False
    if product:
        try:
            loan_type = LoanType(product)
        except ValueError:
            valid = [lt.value for lt in LoanType]
            raise ValueError(f"Unknown product '{product}'. Valid: {valid}") from None
        base_filter.append(Application.loan_type == loan_type)
        needs_app_join = True

    def _base_stmt(extra_filters: list | None = None):
        """Build a count(Decision.id) statement with optional join and filters."""
        stmt = select(func.count(Decision.id))
        if needs_app_join:
            stmt = stmt.join(Application, Decision.application_id == Application.id)
        all_filters = base_filter + (extra_filters or [])
        return stmt.where(*all_filters)

    # Total decisions and denials
    total_result = await session.execute(_base_stmt())
    total_decisions = total_result.scalar() or 0

    denial_result = await session.execute(
        _base_stmt([Decision.decision_type == DecisionType.DENIED])
    )
    total_denials = denial_result.scalar() or 0

    overall_rate = (total_denials / total_decisions * 100) if total_decisions > 0 else 0.0

    # Trend: monthly for 90+ days, weekly for shorter periods
    use_monthly = days >= 60
    trend = await _compute_denial_trend(
        session, base_filter, cutoff, now, use_monthly, needs_app_join
    )

    # Top denial reasons from denial_reasons JSONB
    top_reasons = await _compute_top_denial_reasons(session, base_filter, needs_app_join)

    # Denial rate by product (only when no product filter applied)
    by_product: dict[str, float] | None = None
    if not product:
        by_product = await _compute_denial_by_product(session, cutoff)

    return DenialTrends(
        overall_denial_rate=round(overall_rate, 1),
        total_decisions=total_decisions,
        total_denials=total_denials,
        trend=trend,
        top_reasons=top_reasons,
        by_product=by_product,
        time_range_days=days,
        computed_at=now,
    )


async def _compute_denial_trend(
    session: AsyncSession,
    base_filter: list,
    cutoff: datetime,
    now: datetime,
    monthly: bool,
    needs_app_join: bool = False,
) -> list[DenialTrendPoint]:
    """Compute denial rate trend over time."""
    if monthly:
        period_expr = func.to_char(Decision.created_at, "YYYY-MM")
    else:
        period_expr = func.concat("Week ", func.extract("week", Decision.created_at).cast(str))

    stmt = select(
        period_expr.label("period"),
        func.count(Decision.id).label("total"),
        func.count(
            case(
                (Decision.decision_type == DecisionType.DENIED, Decision.id),
            )
        ).label("denials"),
    )
    if needs_app_join:
        stmt = stmt.join(Application, Decision.application_id == Application.id)
    stmt = stmt.where(*base_filter).group_by(period_expr).order_by(period_expr)

    result = await session.execute(stmt)
    points = []
    for row in result.all():
        total = row[1] or 0
        denials = row[2] or 0
        rate = (denials / total * 100) if total > 0 else 0.0
        points.append(
            DenialTrendPoint(
                period=row[0],
                denial_rate=round(rate, 1),
                denial_count=denials,
                total_decided=total,
            )
        )
    return points


async def _compute_top_denial_reasons(
    session: AsyncSession,
    base_filter: list,
    needs_app_join: bool = False,
) -> list[DenialReason]:
    """Extract top 5 denial reasons from the denial_reasons JSONB field.

    Reasons appearing in fewer than 3 decisions are aggregated into 'Other'.
    """
    # Get all denial decisions with their reasons
    stmt = select(Decision.denial_reasons)
    if needs_app_join:
        stmt = stmt.join(Application, Decision.application_id == Application.id)
    stmt = stmt.where(*base_filter, Decision.decision_type == DecisionType.DENIED).where(
        Decision.denial_reasons.isnot(None)
    )
    result = await session.execute(stmt)

    # Count each reason across all denials
    reason_counts: dict[str, int] = {}
    for (reasons_json,) in result.all():
        if isinstance(reasons_json, list):
            for reason in reasons_json:
                r = str(reason).strip()
                if r:
                    reason_counts[r] = reason_counts.get(r, 0) + 1
        elif isinstance(reasons_json, str):
            r = reasons_json.strip()
            if r:
                reason_counts[r] = reason_counts.get(r, 0) + 1

    if not reason_counts:
        return []

    # Aggregate reasons with < 3 occurrences into "Other"
    other_count = 0
    main_reasons: dict[str, int] = {}
    for reason, count in reason_counts.items():
        if count < 3:
            other_count += count
        else:
            main_reasons[reason] = count

    if other_count > 0:
        main_reasons["Other"] = main_reasons.get("Other", 0) + other_count

    total = sum(main_reasons.values())

    # Sort by count descending, take top 5
    sorted_reasons = sorted(main_reasons.items(), key=lambda x: x[1], reverse=True)[:5]

    return [
        DenialReason(
            reason=reason,
            count=count,
            percentage=round(count / total * 100, 1) if total > 0 else 0.0,
        )
        for reason, count in sorted_reasons
    ]


# Active pipeline stages (not terminal)
_ACTIVE_STAGES = frozenset(
    {
        ApplicationStage.APPLICATION,
        ApplicationStage.PROCESSING,
        ApplicationStage.UNDERWRITING,
        ApplicationStage.CONDITIONAL_APPROVAL,
        ApplicationStage.CLEAR_TO_CLOSE,
    }
)


async def get_lo_performance(
    session: AsyncSession,
    days: int = 90,
    product: str | None = None,
) -> LOPerformanceSummary:
    """Compute per-LO performance metrics for CEO dashboard.

    Args:
        session: Database session.
        days: Time range for closed/denied metrics.
        product: Optional loan type filter.

    Returns:
        LOPerformanceSummary with one row per loan officer.
    """
    from db import Condition

    now = datetime.now(UTC)
    cutoff = now - timedelta(days=days)

    # Validate product filter early
    loan_type_filter = None
    if product:
        try:
            loan_type_filter = LoanType(product)
        except ValueError:
            valid = [lt.value for lt in LoanType]
            raise ValueError(f"Unknown product '{product}'. Valid: {valid}") from None

    # Build optional product filter clause
    product_clause = []
    if loan_type_filter:
        product_clause = [Application.loan_type == loan_type_filter]

    # Get all LOs that have any assigned applications
    lo_stmt = (
        select(Application.assigned_to)
        .where(Application.assigned_to.isnot(None), *product_clause)
        .group_by(Application.assigned_to)
    )
    lo_result = await session.execute(lo_stmt)
    lo_ids = [row[0] for row in lo_result.all()]

    rows: list[LOPerformanceRow] = []
    for lo_id in lo_ids:
        lo_filter = [Application.assigned_to == lo_id, *product_clause]

        # Active count (current pipeline, not time-filtered)
        active_stmt = select(func.count(Application.id)).where(
            *lo_filter, Application.stage.in_(_ACTIVE_STAGES)
        )
        active_result = await session.execute(active_stmt)
        active_count = active_result.scalar() or 0

        # Closed count (in time period)
        closed_stmt = select(func.count(Application.id)).where(
            *lo_filter,
            Application.stage == ApplicationStage.CLOSED,
            Application.updated_at >= cutoff,
        )
        closed_result = await session.execute(closed_stmt)
        closed_count = closed_result.scalar() or 0

        # Total initiated by this LO (in time period) for pull-through
        initiated_stmt = select(func.count(Application.id)).where(
            *lo_filter, Application.created_at >= cutoff
        )
        initiated_result = await session.execute(initiated_stmt)
        initiated = initiated_result.scalar() or 0

        pull_through = (closed_count / initiated * 100) if initiated > 0 else 0.0

        # Denial rate: denied / total decided (in time period)
        decided_stmt = (
            select(func.count(Decision.id))
            .join(Application, Decision.application_id == Application.id)
            .where(
                Application.assigned_to == lo_id,
                Decision.created_at >= cutoff,
                *([Application.loan_type == loan_type_filter] if loan_type_filter else []),
            )
        )
        decided_result = await session.execute(decided_stmt)
        total_decided = decided_result.scalar() or 0

        denied_stmt = (
            select(func.count(Decision.id))
            .join(Application, Decision.application_id == Application.id)
            .where(
                Application.assigned_to == lo_id,
                Decision.created_at >= cutoff,
                Decision.decision_type == DecisionType.DENIED,
                *([Application.loan_type == loan_type_filter] if loan_type_filter else []),
            )
        )
        denied_result = await session.execute(denied_stmt)
        total_denied = denied_result.scalar() or 0

        denial_rate = (total_denied / total_decided * 100) if total_decided > 0 else 0.0

        # Avg days Application -> Underwriting (from audit events)
        avg_to_uw = await _lo_avg_turn_time(
            session,
            lo_id,
            cutoff,
            ApplicationStage.APPLICATION,
            ApplicationStage.UNDERWRITING,
            product_clause,
        )

        # Avg days conditions issued -> cleared (from Condition timestamps)
        avg_cond_stmt = (
            select(
                func.avg(
                    func.extract("epoch", Condition.updated_at - Condition.created_at) / 86400.0
                )
            )
            .join(Application, Condition.application_id == Application.id)
            .where(
                Application.assigned_to == lo_id,
                Condition.status == "cleared",
                Condition.updated_at >= cutoff,
                *([Application.loan_type == loan_type_filter] if loan_type_filter else []),
            )
        )
        avg_cond_result = await session.execute(avg_cond_stmt)
        avg_cond_raw = avg_cond_result.scalar()
        avg_cond = round(float(avg_cond_raw), 1) if avg_cond_raw is not None else None

        rows.append(
            LOPerformanceRow(
                lo_id=lo_id,
                lo_name=None,  # LO names come from Keycloak, not in DB
                active_count=active_count,
                closed_count=closed_count,
                pull_through_rate=round(pull_through, 1),
                avg_days_to_underwriting=avg_to_uw,
                avg_days_conditions_to_cleared=avg_cond,
                denial_rate=round(denial_rate, 1),
            )
        )

    return LOPerformanceSummary(
        loan_officers=rows,
        time_range_days=days,
        computed_at=now,
    )


async def _lo_avg_turn_time(
    session: AsyncSession,
    lo_id: str,
    cutoff: datetime,
    from_stage: ApplicationStage,
    to_stage: ApplicationStage,
    product_clause: list,
) -> float | None:
    """Avg days between two stage transitions for a specific LO's applications."""
    from db import AuditEvent

    to_events = (
        select(
            AuditEvent.application_id,
            AuditEvent.timestamp.label("to_ts"),
        )
        .join(Application, AuditEvent.application_id == Application.id)
        .where(
            AuditEvent.event_type == "stage_transition",
            AuditEvent.timestamp >= cutoff,
            AuditEvent.event_data["to_stage"].as_string() == to_stage.value,
            Application.assigned_to == lo_id,
            *product_clause,
        )
        .subquery("to_events")
    )

    from_events = (
        select(
            AuditEvent.application_id,
            AuditEvent.timestamp.label("from_ts"),
        )
        .where(
            AuditEvent.event_type == "stage_transition",
            AuditEvent.event_data["to_stage"].as_string() == from_stage.value,
        )
        .subquery("from_events")
    )

    avg_stmt = (
        select(func.avg(func.extract("epoch", to_events.c.to_ts - from_events.c.from_ts) / 86400.0))
        .select_from(to_events)
        .join(from_events, to_events.c.application_id == from_events.c.application_id)
        .where(to_events.c.to_ts > from_events.c.from_ts)
    )

    result = await session.execute(avg_stmt)
    avg_raw = result.scalar()
    return round(float(avg_raw), 1) if avg_raw is not None else None


async def _compute_denial_by_product(
    session: AsyncSession,
    cutoff: datetime,
) -> dict[str, float]:
    """Compute denial rate per product type."""
    stmt = (
        select(
            Application.loan_type,
            func.count(Decision.id).label("total"),
            func.count(
                case(
                    (Decision.decision_type == DecisionType.DENIED, Decision.id),
                )
            ).label("denials"),
        )
        .join(Application, Decision.application_id == Application.id)
        .where(Decision.created_at >= cutoff)
        .where(Application.loan_type.isnot(None))
        .group_by(Application.loan_type)
    )

    result = await session.execute(stmt)
    by_product: dict[str, float] = {}
    for row in result.all():
        loan_type = row[0]
        total = row[1] or 0
        denials = row[2] or 0
        if total > 0:
            by_product[loan_type.value] = round(denials / total * 100, 1)

    return by_product
