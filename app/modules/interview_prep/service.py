"""Interview prep service: briefing generation, mock Q&A loop, debrief capture."""

from __future__ import annotations

from app.core.ids import new_id, now_utc
from app.core.llm_client import LLMClient, ModelTier
from app.core.storage import Collections, StorageBackend
from app.prompts import render
from app.schemas.company import CompanyProfile
from app.schemas.interview import (
    InterviewBrief,
    InterviewDebrief,
    LikelyQuestion,
    MockSession,
    MockTurn,
)
from app.schemas.job import JobPosting
from app.schemas.profile import CandidateProfile
from app.schemas.profile import QAItem


def _profile_extract(profile: CandidateProfile) -> str:
    stories = "\n".join(
        f"- id={s.id} | {s.title}: S={s.situation} T={s.task} A={s.action} R={s.result}"
        for s in profile.story_bank
    )
    qa = "\n".join(f"- id={q.id} | Q: {q.question} A: {q.answer}" for q in profile.qa_bank)
    return f"Stories:\n{stories or '(none)'}\n\nQ&A bank:\n{qa or '(none)'}"


def _company_profile_text(company: CompanyProfile | None) -> str:
    if company is None:
        return "(no company profile available)"
    return (
        f"Culture: {company.culture_summary}\nValues: {', '.join(company.values)}\n"
        f"Interview process: {', '.join(company.interview_process)}\n"
        f"Tech stack: {', '.join(company.tech_stack)}"
    )


class InterviewPrepService:
    def __init__(self, storage: StorageBackend, llm: LLMClient) -> None:
        self.storage = storage
        self.llm = llm

    # ---------------------------------------------------------------- briefing
    def build_brief(
        self,
        *,
        profile: CandidateProfile,
        job: JobPosting | None,
        company: CompanyProfile,
    ) -> InterviewBrief:
        prompt = render(
            "interview_brief",
            title=job.title if job else "(role not specified)",
            company=company.name,
            description=job.description[:8000] if job else "(no job description provided)",
            company_profile=_company_profile_text(company),
            profile_extract=_profile_extract(profile),
        )
        fallback = {
            "company_snapshot": company.culture_summary or "",
            "culture_notes": company.values,
            "tech_focus": company.tech_stack,
            "likely_questions": [
                {
                    "question": qa.question,
                    "category": qa.category,
                    "why_likely": "from candidate's own Q&A bank (offline fallback)",
                    "suggested_story_ids": [],
                    "draft_answer": qa.answer,
                }
                for qa in profile.qa_bank[:5]
            ],
            "questions_to_ask": [],
            "preparation_gaps": [],
        }
        fields = self.llm.complete_json(
            system="You build grounded interview briefings as JSON. No invented experience.",
            user=prompt,
            tier=ModelTier.SMART,
            fallback=fallback,
        )
        brief = InterviewBrief(
            id=new_id("brief"),
            profile_id=profile.id,
            job_id=job.id if job else None,
            company=company.name,
            title=job.title if job else None,
            company_snapshot=fields.get("company_snapshot"),
            culture_notes=fields.get("culture_notes") or [],
            tech_focus=fields.get("tech_focus") or [],
            likely_questions=[LikelyQuestion(**q) for q in fields.get("likely_questions") or []],
            questions_to_ask=fields.get("questions_to_ask") or [],
            preparation_gaps=fields.get("preparation_gaps") or [],
        )
        self.storage.put(Collections.INTERVIEWS, brief.id, brief.model_dump(mode="json"))
        return brief

    def get_brief(self, brief_id: str) -> InterviewBrief | None:
        doc = self.storage.get(Collections.INTERVIEWS, brief_id)
        return InterviewBrief(**doc) if doc else None

    def list_briefs(self) -> list[InterviewBrief]:
        return [InterviewBrief(**d) for d in self.storage.list(Collections.INTERVIEWS)]

    # ----------------------------------------------------------- mock interview
    def start_mock_session(self, brief: InterviewBrief, profile: CandidateProfile) -> MockSession:
        first_question = (
            brief.likely_questions[0].question
            if brief.likely_questions
            else "Tell me about yourself."
        )
        session = MockSession(
            id=new_id("mock"),
            brief_id=brief.id,
            profile_id=profile.id,
            company=brief.company,
            turns=[MockTurn(index=0, question=first_question)],
        )
        self._save_session(session)
        return session

    def submit_answer(
        self,
        session: MockSession,
        brief: InterviewBrief,
        profile: CandidateProfile,
        *,
        answer: str,
    ) -> MockSession:
        turn = session.turns[-1]
        turn.answer = answer

        remaining = [q.question for q in brief.likely_questions[len(session.turns) :]]
        prompt = render(
            "mock_feedback",
            title=brief.title or "",
            company=brief.company,
            question=turn.question,
            answer=answer,
            profile_extract=_profile_extract(profile),
            remaining_questions=", ".join(remaining) or "(none planned - wrap up)",
        )
        fallback = {
            "score": 60.0,
            "feedback": "Offline mode: no LLM feedback generated. Configure OPENROUTER_API_KEY.",
            "next_question": remaining[0] if remaining else None,
        }
        fields = self.llm.complete_json(
            system="You score and coach a mock interview answer as JSON.",
            user=prompt,
            tier=ModelTier.SMART,
            fallback=fallback,
        )
        turn.score = fields.get("score")
        turn.feedback = fields.get("feedback")

        next_question = fields.get("next_question") or (remaining[0] if remaining else None)
        if next_question:
            session.turns.append(MockTurn(index=len(session.turns), question=next_question))
        else:
            session.finished = True
            scored = [t.score for t in session.turns if t.score is not None]
            if scored:
                session.overall_feedback = f"Average score: {sum(scored) / len(scored):.1f}/100"

        session.updated_at = now_utc()
        self._save_session(session)
        return session

    def _save_session(self, session: MockSession) -> None:
        self.storage.put(Collections.INTERVIEWS, f"mock_{session.id}", session.model_dump(mode="json"))

    def get_session(self, session_id: str) -> MockSession | None:
        doc = self.storage.get(Collections.INTERVIEWS, f"mock_{session_id}")
        return MockSession(**doc) if doc else None

    # ------------------------------------------------------------------ debrief
    def capture_debrief(
        self,
        *,
        profile: CandidateProfile,
        company: str,
        job_id: str | None,
        round_name: str | None,
        questions_asked: list[str],
        what_went_well: str | None,
        what_to_improve: str | None,
        interviewer_signals: str | None,
        outcome: str | None,
    ) -> tuple[InterviewDebrief, CandidateProfile]:
        prompt = render(
            "debrief_analyze",
            company=company,
            round_name=round_name or "",
            questions_asked=", ".join(questions_asked) or "(none recorded)",
            what_went_well=what_went_well or "",
            what_to_improve=what_to_improve or "",
            interviewer_signals=interviewer_signals or "",
            profile_extract=_profile_extract(profile),
        )
        fallback = {"positioning_advice": "", "new_qa": [], "follow_up_actions": []}
        fields = self.llm.complete_json(
            system="You turn an interview debrief into reusable prep material as JSON.",
            user=prompt,
            tier=ModelTier.FAST,
            fallback=fallback,
        )

        new_qa_items = [
            QAItem(id=new_id("qa"), **qa) for qa in fields.get("new_qa") or []
        ]
        debrief = InterviewDebrief(
            id=new_id("debrief"),
            profile_id=profile.id,
            company=company,
            job_id=job_id,
            round_name=round_name,
            questions_asked=questions_asked,
            what_went_well=what_went_well,
            what_to_improve=what_to_improve,
            interviewer_signals=interviewer_signals,
            outcome=outcome,
            derived_qa_ids=[q.id for q in new_qa_items],
            positioning_advice=fields.get("positioning_advice"),
        )
        self.storage.put(Collections.DEBRIEFS, debrief.id, debrief.model_dump(mode="json"))

        # Feed the new Q&A items back into the candidate's profile (positioning loop).
        profile.qa_bank = profile.qa_bank + new_qa_items
        profile.updated_at = now_utc()
        self.storage.put(Collections.PROFILES, profile.id, profile.model_dump(mode="json"))

        return debrief, profile
