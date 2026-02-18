"""
Lead Qualification Agent
Core AI agent for qualifying leads using Claude API
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.db.models import LeadScore


class AgentIntent(str, Enum):
    """Detected intent from lead message."""

    GREETING = "greeting"
    SERVICE_INQUIRY = "service_inquiry"
    PRICING_QUESTION = "pricing_question"
    AVAILABILITY_CHECK = "availability_check"
    APPOINTMENT_REQUEST = "appointment_request"
    COMPLAINT = "complaint"
    GENERAL_QUESTION = "general_question"
    HUMAN_REQUEST = "human_request"
    OFF_TOPIC = "off_topic"
    UNCLEAR = "unclear"


class AgentAction(str, Enum):
    """Actions the agent can take."""

    CONTINUE_CONVERSATION = "continue_conversation"
    REQUEST_INFO = "request_info"
    BOOK_APPOINTMENT = "book_appointment"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    TRANSFER_HOT_LEAD = "transfer_hot_lead"
    ADD_TO_NURTURE = "add_to_nurture"
    END_CONVERSATION = "end_conversation"


@dataclass
class QualificationData:
    """Extracted qualification data from conversation."""

    service_interest: str | None = None
    urgency: str | None = None  # immediate, this_week, this_month, just_looking
    budget_confirmed: bool | None = None
    budget_range: str | None = None
    location: str | None = None
    preferred_contact_time: str | None = None
    decision_maker: bool | None = None
    timeline: str | None = None
    additional_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_interest": self.service_interest,
            "urgency": self.urgency,
            "budget_confirmed": self.budget_confirmed,
            "budget_range": self.budget_range,
            "location": self.location,
            "preferred_contact_time": self.preferred_contact_time,
            "decision_maker": self.decision_maker,
            "timeline": self.timeline,
            "additional_notes": self.additional_notes,
        }


@dataclass
class AgentResponse:
    """Response from the qualification agent."""

    message: str
    intent: AgentIntent
    action: AgentAction
    lead_score: LeadScore
    confidence: float
    qualification_data: QualificationData
    should_escalate: bool = False
    escalation_reason: str | None = None
    tokens_input: int = 0
    tokens_output: int = 0
    processing_time_ms: int = 0
    model_used: str = ""


@dataclass
class ClientConfig:
    """Client-specific configuration for the agent."""

    client_id: UUID
    business_name: str
    industry: str
    services: list[str]
    business_hours: str
    timezone: str
    qualification_questions: list[str]
    hot_lead_triggers: list[str]
    escalation_triggers: list[str]
    language: str = "en"
    tone: str = "professional_friendly"
    custom_instructions: str = ""


@dataclass
class ConversationContext:
    """Context passed to the agent for each message."""

    conversation_id: UUID
    lead_id: UUID
    lead_name: str | None
    lead_phone: str | None
    lead_email: str | None
    channel: str
    message_history: list[dict[str, str]]
    current_qualification: QualificationData
    rag_context: list[str] | None = None


class LeadQualificationAgent:
    """
    AI Agent for qualifying leads using Claude API.
    Handles conversation flow, qualification extraction, and scoring.
    """

    def __init__(self, client_config: ClientConfig):
        self.client_config = client_config
        self.client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )
        self.model = settings.anthropic_model_qualification
        self.max_tokens = settings.anthropic_max_tokens
        self.temperature = settings.anthropic_temperature

    def _build_system_prompt(self, context: ConversationContext) -> str:
        """Build the system prompt with client configuration and context."""

        rag_section = ""
        if context.rag_context:
            rag_section = f"""
## Relevant Knowledge Base Information
Use this information to answer questions accurately:
{chr(10).join(f'- {ctx}' for ctx in context.rag_context)}
"""

        return f"""You are an AI assistant for {self.client_config.business_name}, a {self.client_config.industry} company.

## Your Role
You are the first point of contact for potential customers. Your goals are:
1. Respond helpfully and professionally to inquiries
2. Qualify leads by gathering key information naturally
3. Book appointments when appropriate
4. Identify hot leads for immediate human follow-up
5. Handle common questions using the knowledge base

## Business Information
- Business: {self.client_config.business_name}
- Industry: {self.client_config.industry}
- Services: {', '.join(self.client_config.services)}
- Hours: {self.client_config.business_hours}
- Timezone: {self.client_config.timezone}

## Communication Guidelines
- Tone: {self.client_config.tone}
- Language: {self.client_config.language}
- Be conversational and helpful, not robotic
- Keep responses concise (2-3 sentences max unless explaining something)
- Use the lead's name when known
- Ask one question at a time
- Don't be pushy or salesy

## Qualification Goals
Naturally gather this information during conversation:
{chr(10).join(f'- {q}' for q in self.client_config.qualification_questions)}

## Strict Rules
1. NEVER quote exact prices - say "I'll have our team confirm pricing based on your specific needs"
2. NEVER provide legal, medical, or financial advice
3. NEVER make promises you can't keep
4. If someone asks to speak with a human, acknowledge and escalate immediately
5. If unsure about something, say "Let me have our team follow up on that specific question"
6. Keep personal information secure - don't repeat sensitive details unnecessarily

## Hot Lead Indicators (Flag for immediate attention)
{chr(10).join(f'- {trigger}' for trigger in self.client_config.hot_lead_triggers)}

## Escalation Triggers (Request human handoff)
{chr(10).join(f'- {trigger}' for trigger in self.client_config.escalation_triggers)}

{rag_section}

{self.client_config.custom_instructions}

## Current Lead Context
- Name: {context.lead_name or 'Unknown'}
- Channel: {context.channel}
- Current qualification status: {json.dumps(context.current_qualification.to_dict(), indent=2)}

## Response Format
After your conversational response, provide structured data in this exact JSON format on a new line starting with "###METADATA###":
{{
    "intent": "<greeting|service_inquiry|pricing_question|availability_check|appointment_request|complaint|general_question|human_request|off_topic|unclear>",
    "action": "<continue_conversation|request_info|book_appointment|escalate_to_human|transfer_hot_lead|add_to_nurture|end_conversation>",
    "lead_score": "<hot|warm|cold|unscored>",
    "confidence": <0.0-1.0>,
    "qualification_updates": {{
        "service_interest": "<extracted or null>",
        "urgency": "<immediate|this_week|this_month|just_looking|null>",
        "budget_confirmed": <true|false|null>,
        "budget_range": "<extracted or null>",
        "location": "<extracted or null>",
        "preferred_contact_time": "<extracted or null>",
        "decision_maker": <true|false|null>,
        "timeline": "<extracted or null>",
        "notes": ["<any important notes>"]
    }},
    "should_escalate": <true|false>,
    "escalation_reason": "<reason if should_escalate is true, else null>"
}}
"""

    def _build_messages(
        self, context: ConversationContext, current_message: str
    ) -> list[dict[str, str]]:
        """Build the message history for the API call."""
        messages = []

        # Add conversation history
        for msg in context.message_history[-10:]:  # Last 10 messages for context
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current message
        messages.append({"role": "user", "content": current_message})

        return messages

    def _parse_response(self, raw_response: str, tokens_in: int, tokens_out: int, processing_time: int) -> AgentResponse:
        """Parse the agent's response into structured format."""

        # Split response and metadata
        parts = raw_response.split("###METADATA###")
        message = parts[0].strip()

        # Default values
        intent = AgentIntent.UNCLEAR
        action = AgentAction.CONTINUE_CONVERSATION
        lead_score = LeadScore.UNSCORED
        confidence = 0.5
        qualification_data = QualificationData()
        should_escalate = False
        escalation_reason = None

        # Parse metadata if present
        if len(parts) > 1:
            try:
                metadata = json.loads(parts[1].strip())

                intent = AgentIntent(metadata.get("intent", "unclear"))
                action = AgentAction(metadata.get("action", "continue_conversation"))
                lead_score = LeadScore(metadata.get("lead_score", "unscored"))
                confidence = float(metadata.get("confidence", 0.5))
                should_escalate = metadata.get("should_escalate", False)
                escalation_reason = metadata.get("escalation_reason")

                # Parse qualification updates
                qual_updates = metadata.get("qualification_updates", {})
                qualification_data = QualificationData(
                    service_interest=qual_updates.get("service_interest"),
                    urgency=qual_updates.get("urgency"),
                    budget_confirmed=qual_updates.get("budget_confirmed"),
                    budget_range=qual_updates.get("budget_range"),
                    location=qual_updates.get("location"),
                    preferred_contact_time=qual_updates.get("preferred_contact_time"),
                    decision_maker=qual_updates.get("decision_maker"),
                    timeline=qual_updates.get("timeline"),
                    additional_notes=qual_updates.get("notes", []),
                )
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                # If parsing fails, use defaults but log the error
                print(f"Error parsing agent metadata: {e}")

        return AgentResponse(
            message=message,
            intent=intent,
            action=action,
            lead_score=lead_score,
            confidence=confidence,
            qualification_data=qualification_data,
            should_escalate=should_escalate,
            escalation_reason=escalation_reason,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            processing_time_ms=processing_time,
            model_used=self.model,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def process_message(
        self,
        message: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """
        Process an incoming message and generate a response.

        Args:
            message: The incoming message from the lead
            context: Conversation and lead context

        Returns:
            AgentResponse with message, intent, actions, and qualification data
        """
        start_time = time.time()

        system_prompt = self._build_system_prompt(context)
        messages = self._build_messages(context, message)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages,
            )

            processing_time = int((time.time() - start_time) * 1000)

            # Extract response content
            raw_response = response.content[0].text
            tokens_input = response.usage.input_tokens
            tokens_output = response.usage.output_tokens

            return self._parse_response(
                raw_response,
                tokens_input,
                tokens_output,
                processing_time,
            )

        except anthropic.APIError as e:
            # Log and re-raise for retry
            print(f"Anthropic API error: {e}")
            raise

    async def generate_greeting(self, context: ConversationContext) -> AgentResponse:
        """Generate an initial greeting message for a new conversation."""

        greeting_prompt = f"""Generate a brief, friendly greeting for a new lead contacting {self.client_config.business_name}.
        
The lead reached out via {context.channel}.
{f"Their name is {context.lead_name}." if context.lead_name else "We don't know their name yet."}

Keep it to 1-2 sentences. Be welcoming but not overly enthusiastic. Ask how you can help them today."""

        start_time = time.time()

        response = self.client.messages.create(
            model=settings.anthropic_model_routing,  # Use faster model for simple greeting
            max_tokens=150,
            temperature=0.7,
            messages=[{"role": "user", "content": greeting_prompt}],
        )

        processing_time = int((time.time() - start_time) * 1000)

        return AgentResponse(
            message=response.content[0].text.strip(),
            intent=AgentIntent.GREETING,
            action=AgentAction.CONTINUE_CONVERSATION,
            lead_score=LeadScore.UNSCORED,
            confidence=1.0,
            qualification_data=QualificationData(),
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            processing_time_ms=processing_time,
            model_used=settings.anthropic_model_routing,
        )


class RouterAgent:
    """
    Lightweight agent for routing and simple decisions.
    Uses Claude Haiku for cost efficiency.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )
        self.model = settings.anthropic_model_routing

    async def detect_language(self, text: str) -> str:
        """Detect the language of incoming text."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=10,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": f"What language is this text? Reply with only the ISO 639-1 code (e.g., 'en', 'es', 'ar'): {text}",
                }
            ],
        )
        return response.content[0].text.strip().lower()[:2]

    async def detect_urgency(self, text: str) -> str:
        """Quick urgency detection for prioritization."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=20,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": f"""Classify urgency of this message. Reply with ONLY one word: immediate, soon, later, or unknown.

Message: {text}""",
                }
            ],
        )
        urgency = response.content[0].text.strip().lower()
        if urgency not in ["immediate", "soon", "later", "unknown"]:
            return "unknown"
        return urgency

    async def should_escalate(self, message: str, conversation_length: int) -> tuple[bool, str | None]:
        """Quick check if message needs human escalation."""

        # Rule-based checks first (faster, no API call)
        escalation_keywords = [
            "speak to human",
            "talk to someone",
            "real person",
            "manager",
            "supervisor",
            "complaint",
            "sue",
            "lawyer",
            "attorney",
            "emergency",
        ]

        message_lower = message.lower()
        for keyword in escalation_keywords:
            if keyword in message_lower:
                return True, f"Keyword detected: {keyword}"

        # Check conversation length
        if conversation_length > 15:
            return True, "Long conversation"

        return False, None
