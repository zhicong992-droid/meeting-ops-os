from __future__ import annotations

from enum import Enum
from typing import TypedDict

from pydantic import BaseModel, Field


class MeetingStatus(str, Enum):
    CREATED = "created"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    ACTION_EXTRACTING = "action_extracting"
    INSIGHT_ANALYZING = "insight_analyzing"
    FOLLOWING_UP = "following_up"
    COMPLETED = "completed"
    FAILED = "failed"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class TranscriptSegment(BaseModel):
    speaker: str = "Unknown"
    text: str = ""
    start: float = 0.0
    end: float = 0.0
    confidence: float = 0.0


class TranscriptResult(BaseModel):
    meeting_id: str
    segments: list[TranscriptSegment] = Field(default_factory=list)
    language: str = "zh"
    duration_seconds: float = 0.0
    full_text: str = ""


class TopicSummary(BaseModel):
    title: str
    discussion_points: list[str] = Field(default_factory=list)
    participants: list[str] = Field(default_factory=list)
    conclusion: str = ""


class MeetingSummary(BaseModel):
    title: str
    date: str = ""
    participants: list[str] = Field(default_factory=list)
    topics: list[TopicSummary] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class ActionItem(BaseModel):
    assignee: str
    task: str
    deadline: str = ""
    priority: Priority = Priority.MEDIUM
    context: str = ""
    jira_issue_key: str | None = None
    feishu_task_id: str | None = None


class ActionResult(BaseModel):
    meeting_id: str
    action_items: list[ActionItem] = Field(default_factory=list)
    sync_status: dict[str, str] = Field(default_factory=dict)


class SpeakerStats(BaseModel):
    speaker: str
    speaking_duration: float = 0.0
    speaking_ratio: float = 0.0
    word_count: int = 0
    segment_count: int = 0


class MeetingInsight(BaseModel):
    meeting_id: str
    overall_sentiment: SentimentType = SentimentType.NEUTRAL
    sentiment_score: float = 0.5
    speaker_stats: list[SpeakerStats] = Field(default_factory=list)
    efficiency_score: float = 5.0
    keywords: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class FollowUpResult(BaseModel):
    meeting_id: str
    summary_sent: bool = False
    recipients: list[str] = Field(default_factory=list)
    jira_issues_created: list[str] = Field(default_factory=list)
    feishu_tasks_created: list[str] = Field(default_factory=list)
    reminders_scheduled: int = 0
    report_url: str = ""


class MeetingState(TypedDict, total=False):
    meeting_id: str
    status: MeetingStatus
    audio_data: bytes
    transcript: TranscriptResult
    transcript_text: str
    summary: MeetingSummary
    actions: ActionResult
    insights: MeetingInsight
    followup: FollowUpResult
    errors: list[str]


def create_initial_state(meeting_id: str, audio_data: bytes = b"") -> MeetingState:
    return {
        "meeting_id": meeting_id,
        "status": MeetingStatus.CREATED,
        "audio_data": audio_data,
        "errors": [],
    }
