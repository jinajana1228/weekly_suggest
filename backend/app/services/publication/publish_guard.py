"""발행 게이트 — 발행 조건 충족 여부 검사.

발행 조건:
  1. 종목 수 >= MIN_PUBLISH_STOCKS (기본 5)
  2. 모든 review_item이 APPROVED 상태
  3. 종목당 data_quality_flag_count <= MAX_DATA_QUALITY_FLAGS (기본 3)
  4. 이미 PUBLISHED 상태인 에디션은 재발행 불가 (overwrite 방지)
"""
from dataclasses import dataclass, field
from typing import Optional

from app.core.config import settings
from app.storage.state_store import state_store


@dataclass
class GuardResult:
    can_publish: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        lines = [f"can_publish={self.can_publish}"]
        for issue in self.issues:
            lines.append(f"  [BLOCK] {issue}")
        for warn in self.warnings:
            lines.append(f"  [WARN]  {warn}")
        return "\n".join(lines)


def check_publish_guard(
    task_id: str,
    report_id: str,
    min_stocks: Optional[int] = None,
    max_flags: Optional[int] = None,
    allow_overwrite: bool = False,
    require_narrative: Optional[bool] = None,
) -> GuardResult:
    """
    발행 가능 여부 검사.

    Parameters
    ----------
    task_id          : 대상 review_task ID
    report_id        : 대상 report_id
    min_stocks       : 최소 종목 수 (None이면 settings.MIN_PUBLISH_STOCKS 사용)
    max_flags        : 종목당 최대 플래그 수 (None이면 settings.MAX_DATA_QUALITY_FLAGS 사용)
    allow_overwrite  : True이면 이미 PUBLISHED 상태여도 허용
    require_narrative: None이면 settings.NARRATIVE_REQUIRE_FOR_PUBLISH 사용
    """
    _min = min_stocks if min_stocks is not None else settings.MIN_PUBLISH_STOCKS
    _max_flags = max_flags if max_flags is not None else settings.MAX_DATA_QUALITY_FLAGS
    _require_narrative = (
        require_narrative
        if require_narrative is not None
        else settings.NARRATIVE_REQUIRE_FOR_PUBLISH
    )

    issues: list[str] = []
    warnings: list[str] = []

    # 1. 에디션 중복 발행 방지
    if not allow_overwrite:
        current_status = state_store.get_edition_status(report_id)
        if current_status == "PUBLISHED":
            issues.append(
                f"에디션 {report_id}은 이미 PUBLISHED 상태입니다. "
                "재발행하려면 allow_overwrite=True를 사용하세요."
            )

    # 2. 태스크 존재 확인
    task = state_store.get_task(task_id)
    if not task:
        issues.append(f"태스크 {task_id}를 찾을 수 없습니다.")
        return GuardResult(can_publish=False, issues=issues, warnings=warnings)

    review_items = task.get("review_items", [])

    # 3. 최소 종목 수
    approved_items = [i for i in review_items if i["review_status"] == "APPROVED"]
    if len(approved_items) < _min:
        issues.append(
            f"APPROVED 종목이 {len(approved_items)}개입니다. "
            f"최소 {_min}개 필요."
        )

    # 4. 전체 APPROVED 여부
    non_approved = [
        i["ticker"] for i in review_items if i["review_status"] != "APPROVED"
    ]
    if non_approved:
        issues.append(
            f"미승인 종목이 있습니다: {', '.join(non_approved)}"
        )

    # 5. 데이터 품질 플래그 임계
    over_threshold = [
        i["ticker"]
        for i in review_items
        if i.get("data_quality_flag_count", 0) > _max_flags
    ]
    if over_threshold:
        issues.append(
            f"데이터 품질 플래그 초과 종목: {', '.join(over_threshold)} "
            f"(임계: {_max_flags}개)"
        )

    # 6. 경고: FLAGGED 이력이 있지만 최종 APPROVED인 종목
    high_flag_approved = [
        i["ticker"]
        for i in review_items
        if i["review_status"] == "APPROVED" and i.get("data_quality_flag_count", 0) > 0
    ]
    if high_flag_approved:
        warnings.append(
            f"플래그 이력 있는 종목(APPROVED): {', '.join(high_flag_approved)}"
        )

    # 7. LLM narrative 미생성 종목 (NARRATIVE_REQUIRE_FOR_PUBLISH=True 시 차단)
    not_narrative_approved = [
        i["ticker"]
        for i in review_items
        if not i.get("llm_narrative_approved", False)
    ]
    if not_narrative_approved:
        if _require_narrative:
            issues.append(
                f"LLM narrative 미승인 종목: {', '.join(not_narrative_approved)}. "
                "NARRATIVE_REQUIRE_FOR_PUBLISH=False로 변경하거나 narrative를 먼저 생성/승인하세요."
            )
        else:
            warnings.append(
                f"LLM narrative 미생성/미승인 종목: {', '.join(not_narrative_approved)} "
                "(현재 발행 차단 안 함 — NARRATIVE_REQUIRE_FOR_PUBLISH=True로 필수화 가능)"
            )

    return GuardResult(
        can_publish=len(issues) == 0,
        issues=issues,
        warnings=warnings,
    )
