"""
AI Lead Qualification Agent Service.
Uses Claude for intelligent lead qualification and conversation handling.
"""
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

import anthropic
from anthropic import AsyncAnthropic
import structlog

from app.core.config import settings
from app.models.models import (
    Lead, Conversation, Message, Client, KnowledgeBaseEntry,
    LeadScore, LeadStatus, MessageRole, HandoffReason, ChannelType
)

logger = structlog.get_logger()


@dataclass
class QualificationResult:
    """Result of lead qualification analysis."""
    score: LeadScore
    score_value: float
    confidence: float
    response_text: str
    intent: str
    entities: Dict[str, Any]
    should_handoff: bool
    handoff_reason: Optional[HandoffReason]
    suggested_status: LeadStatus
    input_tokens: int
    output_tokens: int


@dataclass
class ConversationContext:
    """Context for AI conversation."""
    client: Client
    lead: Lead
    conversation: Conversation
    messages: List[Message]
    knowledge_context: str
    incoming_message: str
    channel: ChannelType


class LeadQualificationAgent:
    """
    AI Agent for lead qualification and conversation handling.
    Uses Claude Sonnet for qualification, Haiku for simple routing.
    """
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.qualification_model = settings.CLAUDE_MODEL_QUALIFICATION
        self.routing_model = settings.CLAUDE_MODEL_ROUTING
        
    def _build_system_prompt(self, client: Client) -> str:
        """Build the system prompt for the AI agent based on client configuration."""
        
        persona_name = client.ai_persona_name or "AI Assistant"
        services = ", ".join(client.services_offered or ["general services"])
        
        system_prompt = f"""You are {persona_name}, a friendly and professional AI assistant for {client.name}.

## YOUR ROLE
You are the first point of contact for potential customers. Your goals are:
1. Respond warmly and professionally to inquiries
2. Understand what service or help the customer needs
3. Gather key qualification information naturally through conversation
4. Score leads based on their readiness to buy/engage
5. Book appointments or hand off hot leads to human agents when appropriate

## BUSINESS INFORMATION
- Company: {client.name}
- Industry: {client.vertical.value if client.vertical else 'service business'}
- Services: {services}
- Business Hours: {json.dumps(client.business_hours) if client.business_hours else 'Standard business hours'}
- Timezone: {client.timezone}

## QUALIFICATION QUESTIONS TO NATURALLY WORK IN
{self._format_qualification_questions(client.qualification_questions)}

## LEAD SCORING CRITERIA
Score leads as HOT, WARM, or COLD based on:

HOT (Score 0.8-1.0):
- Has immediate need (within 1-2 weeks)
- Has budget or decision-making authority
- Engaged and responsive
- Asking specific questions about pricing/scheduling

WARM (Score 0.5-0.79):
- Has need but timeline is 2-4 weeks out
- Gathering information
- Somewhat engaged
- May need more nurturing

COLD (Score 0.0-0.49):
- Just browsing or researching
- No clear timeline
- Price shopping only
- Not responsive or engaged

## RESPONSE GUIDELINES
1. Keep responses concise (2-3 sentences typical, never more than 4)
2. Be conversational and friendly, not robotic
3. Ask only ONE question at a time
4. Use the customer's name if provided
5. Match the customer's communication style (formal/casual)
6. Never make pricing commitments without authorization
7. Never provide legal, medical, or financial advice
8. If asked something you don't know, acknowledge it honestly

## HANDOFF TRIGGERS
Request human handoff when:
- Customer explicitly asks to speak with a human
- You're uncertain how to help (confidence < 70%)
- The lead appears to be high-value
- Conversation exceeds 15 messages without resolution
- Customer expresses strong negative sentiment
- Complex technical or pricing questions arise

## OUTPUT FORMAT
You must respond with valid JSON in this exact format:
{{
    "response_text": "Your natural language response to the customer",
    "intent": "The detected customer intent (e.g., inquiry, pricing_question, appointment_request, complaint, other)",
    "entities": {{
        "name": "Customer name if mentioned",
        "service_needed": "What service they're interested in",
        "timeline": "When they need the service",
        "budget": "Any budget mentioned",
        "location": "Address or area if mentioned",
        "email": "Email if provided",
        "other": "Any other relevant extracted info"
    }},
    "lead_score": 0.0 to 1.0,
    "confidence": 0.0 to 1.0,
    "should_handoff": true/false,
    "handoff_reason": "reason if should_handoff is true, null otherwise",
    "suggested_next_action": "continue_conversation|book_appointment|handoff_to_human|nurture_sequence"
}}

Always respond with valid JSON only, no additional text."""

        return system_prompt
    
    def _format_qualification_questions(self, questions: Optional[List[str]]) -> str:
        """Format qualification questions for the prompt."""
        if not questions:
            return """- What service or help do they need?
- What's their timeline?
- Are they the decision maker?
- What's driving their need?"""
        
        return "\n".join(f"- {q}" for q in questions)
    
    def _build_conversation_history(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Build conversation history for Claude API format."""
        history = []
        for msg in messages:
            if msg.role == MessageRole.LEAD:
                history.append({"role": "user", "content": msg.content})
            elif msg.role in [MessageRole.AI, MessageRole.HUMAN_AGENT]:
                history.append({"role": "assistant", "content": msg.content})
        return history
    
    async def qualify_and_respond(
        self,
        context: ConversationContext
    ) -> QualificationResult:
        """
        Process incoming message and generate qualified response.
        
        Args:
            context: Full conversation context
            
        Returns:
            QualificationResult with response and scoring
        """
        try:
            # Build the prompt
            system_prompt = self._build_system_prompt(context.client)
            
            # Add knowledge context if available
            if context.knowledge_context:
                system_prompt += f"\n\n## RELEVANT KNOWLEDGE BASE CONTEXT\n{context.knowledge_context}"
            
            # Build conversation history
            conversation_history = self._build_conversation_history(context.messages)
            
            # Add the new incoming message
            conversation_history.append({
                "role": "user",
                "content": context.incoming_message
            })
            
            # Call Claude
            response = await self.client.messages.create(
                model=self.qualification_model,
                max_tokens=settings.CLAUDE_MAX_TOKENS,
                temperature=settings.CLAUDE_TEMPERATURE,
                system=system_prompt,
                messages=conversation_history
            )
            
            # Parse the response
            response_text = response.content[0].text
            
            # Extract JSON from response
            result = self._parse_ai_response(response_text)
            
            # Build qualification result
            return QualificationResult(
                score=self._score_to_enum(result.get("lead_score", 0.5)),
                score_value=float(result.get("lead_score", 0.5)),
                confidence=float(result.get("confidence", 0.8)),
                response_text=result.get("response_text", "I apologize, let me connect you with someone who can help."),
                intent=result.get("intent", "unknown"),
                entities=result.get("entities", {}),
                should_handoff=result.get("should_handoff", False),
                handoff_reason=self._parse_handoff_reason(result.get("handoff_reason")),
                suggested_status=self._determine_status(result),
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens
            )
            
        except Exception as e:
            logger.error("AI qualification failed", error=str(e))
            # Return safe fallback
            return QualificationResult(
                score=LeadScore.UNKNOWN,
                score_value=0.5,
                confidence=0.0,
                response_text="Thanks for reaching out! Let me connect you with someone who can help right away.",
                intent="error",
                entities={},
                should_handoff=True,
                handoff_reason=HandoffReason.LOW_CONFIDENCE,
                suggested_status=LeadStatus.NEW,
                input_tokens=0,
                output_tokens=0
            )
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response JSON, handling potential formatting issues."""
        try:
            # Try direct JSON parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            try:
                # Find JSON block
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(response_text[start:end])
            except:
                pass
        
        # Return default structure if parsing fails
        logger.warning("Failed to parse AI response as JSON", response=response_text[:200])
        return {
            "response_text": response_text,
            "intent": "unknown",
            "entities": {},
            "lead_score": 0.5,
            "confidence": 0.5,
            "should_handoff": True,
            "handoff_reason": "parse_error"
        }
    
    def _score_to_enum(self, score: float) -> LeadScore:
        """Convert numeric score to LeadScore enum."""
        if score >= settings.LEAD_SCORE_HOT_THRESHOLD:
            return LeadScore.HOT
        elif score >= settings.LEAD_SCORE_WARM_THRESHOLD:
            return LeadScore.WARM
        else:
            return LeadScore.COLD
    
    def _parse_handoff_reason(self, reason: Optional[str]) -> Optional[HandoffReason]:
        """Parse handoff reason string to enum."""
        if not reason:
            return None
        
        reason_map = {
            "lead_requested": HandoffReason.LEAD_REQUESTED,
            "low_confidence": HandoffReason.LOW_CONFIDENCE,
            "high_value": HandoffReason.HIGH_VALUE,
            "long_conversation": HandoffReason.LONG_CONVERSATION,
            "negative_sentiment": HandoffReason.NEGATIVE_SENTIMENT,
            "complex_query": HandoffReason.COMPLEX_QUERY,
            "escalation": HandoffReason.ESCALATION,
        }
        
        return reason_map.get(reason.lower().replace(" ", "_"), HandoffReason.ESCALATION)
    
    def _determine_status(self, result: Dict[str, Any]) -> LeadStatus:
        """Determine lead status based on AI analysis."""
        next_action = result.get("suggested_next_action", "continue_conversation")
        
        if next_action == "book_appointment":
            return LeadStatus.APPOINTMENT_SCHEDULED
        elif next_action == "handoff_to_human":
            return LeadStatus.HANDED_OFF
        elif next_action == "nurture_sequence":
            return LeadStatus.NURTURE
        elif result.get("lead_score", 0) >= 0.8:
            return LeadStatus.QUALIFIED
        else:
            return LeadStatus.CONTACTED


class QuickRouter:
    """
    Fast routing using Claude Haiku for simple classification tasks.
    Used for quick intent detection and channel routing.
    """
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL_ROUTING
    
    async def classify_intent(self, message: str) -> Tuple[str, float]:
        """
        Quickly classify message intent using Haiku.
        
        Returns:
            Tuple of (intent, confidence)
        """
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=100,
                temperature=0.1,
                system="""Classify the user message intent into one of these categories:
- inquiry: General question about services
- pricing: Asking about costs/pricing
- appointment: Wanting to schedule/book
- complaint: Expressing dissatisfaction
- support: Need help with existing service
- spam: Irrelevant/spam message
- greeting: Just saying hello
- other: Doesn't fit other categories

Respond with JSON only: {"intent": "category", "confidence": 0.0-1.0}""",
                messages=[{"role": "user", "content": message}]
            )
            
            result = json.loads(response.content[0].text)
            return result.get("intent", "other"), result.get("confidence", 0.5)
            
        except Exception as e:
            logger.error("Quick routing failed", error=str(e))
            return "other", 0.0
    
    async def is_spam_or_irrelevant(self, message: str) -> bool:
        """Check if message is spam or irrelevant."""
        intent, confidence = await self.classify_intent(message)
        return intent == "spam" and confidence > 0.8
    
    async def requires_human(self, message: str) -> bool:
        """Check if message likely requires human intervention."""
        keywords = [
            "speak to human", "talk to someone", "real person",
            "manager", "supervisor", "complaint", "sue", "lawyer",
            "urgent", "emergency"
        ]
        message_lower = message.lower()
        return any(kw in message_lower for kw in keywords)


# Export instances
qualification_agent = LeadQualificationAgent()
quick_router = QuickRouter()
