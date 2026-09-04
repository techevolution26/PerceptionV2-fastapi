from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str
    price_cents: int
    currency: str
    interval: str
    analytics_enabled: bool
    max_topics: int
    verification_included: bool
    trial_days: int


class SubscriptionOut(BaseModel):
    id: int | None = None
    status: str
    plan: PlanOut | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    trial_ends_at: datetime | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    analytics_enabled: bool = False
    max_topics: int = 0
    verification_included: bool = False


class TrialRequest(BaseModel):
    plan_code: str


class CheckoutOut(BaseModel):
    plan: PlanOut
    checkout_required: bool = True
    provider: str = "stripe"
    checkout_url: str
    checkout_session_id: str
    trial_days: int = 0
    message: str


class BillingPortalOut(BaseModel):
    provider: str = "stripe"
    portal_url: str


class BillingInvoiceOut(BaseModel):
    id: str
    number: str | None = None
    status: str | None = None
    currency: str | None = None
    amount_due: int = 0
    amount_paid: int = 0
    hosted_invoice_url: str | None = None
    invoice_pdf: str | None = None
    created_at: datetime | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None


class AnalyticsTopicOut(BaseModel):
    topic_id: int
    topic_name: str
    perception_count: int
    likes: int
    comments: int
    views: int
    shares: int
    interactions: int
    engagement_rate: float
    signal_strength: float
    signal_score: float = 0.0
    unique_participants: int = 0
    previous_perception_count: int = 0
    growth_rate: float = 0.0
    momentum: str = "stable"
    evidence_level: str = "insufficient"


class AnalyticsGeoOut(BaseModel):
    country_code: str
    perception_count: int
    interactions: int
    engagement_rate: float = 0.0
    share_of_perceptions: float


class AnalyticsInsightOut(BaseModel):
    kind: str
    title: str
    detail: str
    confidence: str


class AnalyticsTrendPoint(BaseModel):
    date: str
    perceptions: int
    interactions: int


class AnalyticsOpportunityOut(BaseModel):
    topic_id: int
    topic_name: str
    reason: str
    signal_strength: float
    signal_score: float = 0.0
    growth_rate: float
    sample_size: int
    unique_participants: int = 0
    evidence_level: str




class AnalyticsRelationshipOut(BaseModel):
    topic_a_id: int
    topic_a_name: str
    topic_b_id: int
    topic_b_name: str
    shared_participants: int
    participant_overlap: float
    relationship_strength: float
    evidence_level: str


class AnalyticsGeoTopicOut(BaseModel):
    topic_id: int
    topic_name: str
    country_code: str
    perception_count: int
    share_of_topic: float
    signal_score: float
    evidence_level: str

class AnalyticsOverviewOut(BaseModel):
    period_days: int
    sample_size: int
    unique_participants: int
    total_perceptions: int
    total_likes: int
    total_comments: int
    total_views: int
    total_shares: int
    total_interactions: int
    engagement_rate: float
    geographic_coverage: int
    primary_topic_id: int | None = None
    primary_topic_name: str | None = None
    strongest_topic: AnalyticsTopicOut | None = None
    emerging_topic: AnalyticsTopicOut | None = None
    activity_baseline_daily: float = 0.0
    activity_current_daily: float = 0.0
    activity_anomaly: str = "normal"
    insights: list[AnalyticsInsightOut] = Field(default_factory=list)
    topics: list[AnalyticsTopicOut]
    geography: list[AnalyticsGeoOut]
    trend: list[AnalyticsTrendPoint]
    opportunities: list[AnalyticsOpportunityOut]
    methodology: list[str]


class AnalyticsEventRequest(BaseModel):
    perception_id: int
    event_type: str


class AnalyticsProfileUpdate(BaseModel):
    professional_focus: str | None = None
    profession: str | None = None
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    region: str | None = None
    city: str | None = None
    primary_analytics_topic_id: int | None = None
    analytics_specialties: list[int] = Field(default_factory=list, max_length=100)


class PerceptionAnalyticsOut(BaseModel):
    perception_id: int
    period_days: int
    created_at: datetime
    topic_id: int | None
    likes: int
    comments: int
    views: int
    shares: int
    unique_participants: int
    engagement_rate: float
    daily_activity: list[dict]
    top_countries: list[dict]
    methodology: list[str]
