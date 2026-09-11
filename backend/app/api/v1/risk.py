"""Supply Chain Risk & Bottleneck Endpoints (/api/v1/risk)."""

from fastapi import APIRouter
from backend.app.schemas.risk import DisruptionAnalysisRequest, DisruptionAnalysisResponse

router = APIRouter(prefix="/risk", tags=["Risk & Disruption Analytics"])


@router.get("", response_model=DisruptionAnalysisResponse, summary="Get global supply chain risk overview")
async def get_risk_overview():
    """Returns aggregated baseline risk score and critical suppliers."""
    return DisruptionAnalysisResponse(
        supplier_id="sup_network_aggregate",
        risk_level="medium",
        bottleneck_score=0.35,
        estimated_revenue_at_risk=150000.0,
        affected_downstream_products=["Automotive Module Alpha"],
        mitigation_recommendations=["Monitor Tier-2 semiconductor component suppliers."],
    )


@router.post("/analyze-disruption", response_model=DisruptionAnalysisResponse, summary="Simulate supplier failure disruption")
async def analyze_supplier_disruption(payload: DisruptionAnalysisRequest):
    """Simulates multi-tier cascading disruption impact if a designated supplier halts production."""
    days = payload.disruption_duration_days
    risk_level = "critical" if days > 21 else ("high" if days > 10 else "medium")
    bottleneck_score = min(round(0.25 + (days * 0.03), 2), 0.99)
    estimated_revenue = round(days * 45000.0, 2)

    return DisruptionAnalysisResponse(
        supplier_id=payload.supplier_id,
        risk_level=risk_level,
        bottleneck_score=bottleneck_score,
        estimated_revenue_at_risk=estimated_revenue,
        affected_downstream_products=["Automotive Module Alpha", "Electronic Power Unit 4"],
        mitigation_recommendations=[
            "Activate secondary backup supplier in Tier 2 network.",
            "Advance buffer safety stock orders for critical silicon components.",
            "Re-route cross-docking logistics to southern distribution node.",
        ],
    )
