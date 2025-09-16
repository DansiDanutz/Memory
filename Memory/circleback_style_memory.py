"""
Circleback-Style Memory System for Memory Bot
Implements transcript processing, action extraction, and memory delivery
Based on analysis of Circleback's approach
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Use existing configured services
from dotenv import load_dotenv
import anthropic
from azure.cognitiveservices.speech import SpeechConfig, AudioConfig, SpeechRecognizer

load_dotenv()


# Data Models based on Circleback structure
@dataclass
class ActionItem:
    """Action item extracted from conversation"""
    id: str
    description: str
    assignee: Optional[str]
    deadline: Optional[datetime]
    status: str = "incomplete"
    created_at: datetime = None
    priority: str = "normal"

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now()


@dataclass
class ConversationMemory:
    """Structured memory from a conversation"""
    id: str
    timestamp: datetime
    duration: int  # seconds
    participants: List[str]

    # Content sections
    overview: str
    transcript: str
    notes: Dict[str, Any]
    action_items: List[ActionItem]
    decisions: List[str]
    topics: List[str]

    # Metadata
    source: str  # WhatsApp, Voice, Meeting, etc.
    tags: List[str]
    importance: int = 3  # 1-5 scale


class CirclebackProcessor:
    """Process conversations into structured memories like Circleback"""

    def __init__(self):
        self.claude_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.azure_key = os.getenv("AZURE_SPEECH_KEY")
        self.azure_region = os.getenv("AZURE_SPEECH_REGION")

        # Initialize Claude
        if self.claude_key:
            self.claude = anthropic.Anthropic(api_key=self.claude_key)

    def process_transcript(self, raw_transcript: str, metadata: Dict = None) -> ConversationMemory:
        """
        Process raw transcript into structured memory
        Mimics Circleback's approach
        """

        # Extract structured information using Claude
        structured_data = self._extract_structure(raw_transcript)

        # Create memory object
        memory = ConversationMemory(
            id=f"conv_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            duration=metadata.get("duration", 0) if metadata else 0,
            participants=self._extract_participants(raw_transcript),
            overview=structured_data["overview"],
            transcript=raw_transcript,
            notes=structured_data["notes"],
            action_items=structured_data["action_items"],
            decisions=structured_data["decisions"],
            topics=structured_data["topics"],
            source=metadata.get("source", "unknown") if metadata else "unknown",
            tags=self._generate_tags(structured_data),
            importance=self._calculate_importance(structured_data)
        )

        return memory

    def _extract_structure(self, transcript: str) -> Dict:
        """Extract structure using Claude (like Circleback's AI)"""

        if not self.claude_key:
            # Fallback if no Claude API
            return self._basic_extraction(transcript)

        prompt = f"""Analyze this conversation transcript and extract structured information.

Transcript:
{transcript}

Please extract and format:

1. OVERVIEW (2-3 sentence summary of the conversation)

2. ACTION ITEMS (things people need to do)
Format each as:
- Description
- Who is responsible (if mentioned)
- Deadline (if mentioned)
- Priority (high/normal/low based on context)

3. KEY DECISIONS (important decisions made)

4. MAIN TOPICS (topics discussed)

5. DETAILED NOTES (organized by topic, like meeting minutes)

Return as JSON with keys: overview, action_items, decisions, topics, notes"""

        try:
            response = self.claude.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            content = response.content[0].text

            # Try to parse as JSON
            try:
                return json.loads(content)
            except:
                # If not valid JSON, do basic parsing
                return self._parse_text_response(content)

        except Exception as e:
            print(f"Claude extraction failed: {e}")
            return self._basic_extraction(transcript)

    def _basic_extraction(self, transcript: str) -> Dict:
        """Basic extraction without AI"""

        lines = transcript.split('\n')

        return {
            "overview": f"Conversation from {datetime.now().strftime('%Y-%m-%d')}. {len(lines)} exchanges recorded.",
            "action_items": self._extract_basic_actions(transcript),
            "decisions": [],
            "topics": self._extract_topics(transcript),
            "notes": {"raw_content": transcript[:1000]}
        }

    def _extract_basic_actions(self, text: str) -> List[ActionItem]:
        """Extract action items using keywords"""

        actions = []
        keywords = ["will", "need to", "should", "must", "todo", "action", "follow up", "remind"]

        lines = text.lower().split('\n')
        for i, line in enumerate(lines):
            for keyword in keywords:
                if keyword in line:
                    actions.append(ActionItem(
                        id=f"action_{i}",
                        description=lines[i][:100],  # First 100 chars
                        assignee=None,
                        deadline=None
                    ))
                    break

        return actions[:10]  # Limit to 10 actions

    def _extract_participants(self, transcript: str) -> List[str]:
        """Extract participant names"""
        # Simple extraction - look for name patterns
        # In production, use speaker diarization
        participants = []

        # Look for "Name:" pattern
        import re
        pattern = r'^([A-Z][a-z]+):'
        matches = re.findall(pattern, transcript, re.MULTILINE)
        participants = list(set(matches))

        if not participants:
            participants = ["User", "Assistant"]

        return participants

    def _extract_topics(self, text: str) -> List[str]:
        """Extract main topics discussed"""
        # Simple keyword extraction
        # In production, use NLP topic modeling

        topics = []

        # Common topic indicators
        topic_keywords = {
            "meeting": "Meetings & Scheduling",
            "project": "Project Discussion",
            "budget": "Budget & Finance",
            "deadline": "Deadlines & Timeline",
            "plan": "Planning",
            "review": "Review & Feedback",
            "launch": "Product Launch",
            "customer": "Customer Relations",
            "team": "Team Coordination"
        }

        text_lower = text.lower()
        for keyword, topic in topic_keywords.items():
            if keyword in text_lower:
                topics.append(topic)

        return list(set(topics))[:5]  # Max 5 topics

    def _generate_tags(self, structured_data: Dict) -> List[str]:
        """Generate searchable tags"""
        tags = []

        # Add topic-based tags
        tags.extend([t.lower().replace(" ", "-") for t in structured_data.get("topics", [])])

        # Add action-based tags
        if structured_data.get("action_items"):
            tags.append("has-actions")

        if structured_data.get("decisions"):
            tags.append("has-decisions")

        # Add date tag
        tags.append(datetime.now().strftime("%Y-%m-%d"))

        return list(set(tags))

    def _calculate_importance(self, structured_data: Dict) -> int:
        """Calculate importance score (1-5)"""
        score = 3  # Default

        # Increase for action items
        if len(structured_data.get("action_items", [])) > 3:
            score += 1

        # Increase for decisions
        if structured_data.get("decisions"):
            score += 1

        # Check for urgent keywords
        overview = structured_data.get("overview", "").lower()
        if any(word in overview for word in ["urgent", "important", "critical", "deadline"]):
            score += 1

        return min(score, 5)

    def _parse_text_response(self, text: str) -> Dict:
        """Parse text response when JSON parsing fails"""

        result = {
            "overview": "",
            "action_items": [],
            "decisions": [],
            "topics": [],
            "notes": {}
        }

        sections = text.split('\n\n')
        for section in sections:
            section_lower = section.lower()

            if "overview" in section_lower or "summary" in section_lower:
                result["overview"] = section.split('\n', 1)[-1] if '\n' in section else section

            elif "action" in section_lower:
                lines = section.split('\n')[1:]  # Skip header
                for line in lines:
                    if line.strip() and line.strip()[0] in '-•*':
                        result["action_items"].append(ActionItem(
                            id=f"action_{len(result['action_items'])}",
                            description=line.strip()[1:].strip(),
                            assignee=None,
                            deadline=None
                        ))

            elif "decision" in section_lower:
                lines = section.split('\n')[1:]
                result["decisions"] = [l.strip()[1:].strip() for l in lines
                                      if l.strip() and l.strip()[0] in '-•*']

            elif "topic" in section_lower:
                lines = section.split('\n')[1:]
                result["topics"] = [l.strip()[1:].strip() for l in lines
                                   if l.strip() and l.strip()[0] in '-•*']

        return result


class MemoryDeliverySystem:
    """Deliver memories in Circleback style"""

    def format_for_whatsapp(self, memory: ConversationMemory) -> str:
        """Format memory for WhatsApp delivery"""

        message = f"""*📝 Conversation Summary*
{datetime.now().strftime('%B %d, %Y at %I:%M %p')}

*Overview:*
{memory.overview}

*Participants:* {', '.join(memory.participants)}
*Duration:* {memory.duration // 60} minutes
"""

        # Add action items if present
        if memory.action_items:
            message += "\n*✅ Action Items:*\n"
            for action in memory.action_items[:5]:  # Limit to 5
                assignee = f" (@{action.assignee})" if action.assignee else ""
                deadline = f" - Due: {action.deadline.strftime('%b %d')}" if action.deadline else ""
                message += f"• {action.description}{assignee}{deadline}\n"

        # Add decisions if present
        if memory.decisions:
            message += "\n*🎯 Key Decisions:*\n"
            for decision in memory.decisions[:3]:
                message += f"• {decision}\n"

        # Add topics
        if memory.topics:
            message += f"\n*📌 Topics:* {', '.join(memory.topics[:5])}"

        # Add search tip
        message += "\n\n_💡 Tip: Ask me about this conversation anytime!_"

        return message[:1000]  # WhatsApp limit

    def format_for_email(self, memory: ConversationMemory) -> Dict[str, str]:
        """Format memory for email delivery (HTML)"""

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">📝 Conversation Summary</h2>
            <p style="color: #7f8c8d;">{memory.timestamp.strftime('%B %d, %Y at %I:%M %p')}</p>

            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #2c3e50; margin-top: 0;">Overview</h3>
                <p>{memory.overview}</p>
            </div>

            <div style="margin: 20px 0;">
                <p><strong>Participants:</strong> {', '.join(memory.participants)}</p>
                <p><strong>Duration:</strong> {memory.duration // 60} minutes</p>
            </div>
        """

        if memory.action_items:
            html_content += """
            <div style="margin: 20px 0;">
                <h3 style="color: #27ae60;">✅ Action Items</h3>
                <ul>
            """
            for action in memory.action_items:
                assignee = f" (Assigned to: {action.assignee})" if action.assignee else ""
                deadline = f" - Due: {action.deadline.strftime('%B %d, %Y')}" if action.deadline else ""
                status_color = "#e74c3c" if action.status == "incomplete" else "#27ae60"

                html_content += f"""
                <li style="margin: 10px 0;">
                    <span style="color: {status_color};">●</span>
                    {action.description}{assignee}{deadline}
                </li>
                """

            html_content += "</ul></div>"

        if memory.decisions:
            html_content += """
            <div style="margin: 20px 0;">
                <h3 style="color: #3498db;">🎯 Key Decisions</h3>
                <ul>
            """
            for decision in memory.decisions:
                html_content += f"<li style='margin: 5px 0;'>{decision}</li>"
            html_content += "</ul></div>"

        if memory.topics:
            html_content += f"""
            <div style="margin: 20px 0;">
                <h3 style="color: #9b59b6;">📌 Topics Discussed</h3>
                <p>{', '.join(memory.topics)}</p>
            </div>
            """

        html_content += """
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ecf0f1;">
                <p style="color: #7f8c8d; font-size: 12px;">
                    Generated by Memory Bot |
                    <a href="#" style="color: #3498db;">View Full Transcript</a> |
                    <a href="#" style="color: #3498db;">Search Past Conversations</a>
                </p>
            </div>
        </body>
        </html>
        """

        return {
            "subject": f"Conversation Summary - {memory.timestamp.strftime('%b %d, %Y')}",
            "html": html_content,
            "text": self.format_for_text(memory)
        }

    def format_for_text(self, memory: ConversationMemory) -> str:
        """Plain text format"""

        text = f"""CONVERSATION SUMMARY
{memory.timestamp.strftime('%B %d, %Y at %I:%M %p')}
{'=' * 50}

OVERVIEW:
{memory.overview}

PARTICIPANTS: {', '.join(memory.participants)}
DURATION: {memory.duration // 60} minutes
"""

        if memory.action_items:
            text += "\nACTION ITEMS:\n"
            for i, action in enumerate(memory.action_items, 1):
                text += f"{i}. {action.description}\n"
                if action.assignee:
                    text += f"   Assigned to: {action.assignee}\n"
                if action.deadline:
                    text += f"   Due: {action.deadline.strftime('%B %d, %Y')}\n"

        if memory.decisions:
            text += "\nKEY DECISIONS:\n"
            for decision in memory.decisions:
                text += f"- {decision}\n"

        if memory.topics:
            text += f"\nTOPICS: {', '.join(memory.topics)}\n"

        return text


# Example usage
def demo_circleback_style():
    """Demonstrate Circleback-style processing"""

    # Sample transcript
    sample_transcript = """
Sarah: Good morning everyone! Let's discuss the product launch timeline.

John: Hi Sarah! I've reviewed the development schedule. We can have the MVP ready by January 15th.

Sarah: That's great John. What about the marketing materials?

Emma: I'll have the marketing kit ready by January 10th. We need to finalize the color scheme though.

John: I suggest we go with the blue gradient we discussed last week.

Sarah: Agreed on the blue gradient. Emma, can you send me the mockups by tomorrow?

Emma: Sure, I'll send them by end of day tomorrow.

Sarah: Perfect. John, we also need to schedule user testing. Can you coordinate with the QA team?

John: I'll set up testing sessions for the week of January 8th.

Sarah: Excellent. Let's plan for a soft launch on January 15th and full launch on January 22nd.

John: Sounds good. I'll update the project timeline.

Emma: I'll prepare the announcement emails and social media posts.

Sarah: Great! Let's meet again next Monday to review progress. Thanks everyone!
"""

    # Process the transcript
    processor = CirclebackProcessor()
    memory = processor.process_transcript(
        sample_transcript,
        metadata={
            "source": "Team Meeting",
            "duration": 900  # 15 minutes
        }
    )

    # Format for delivery
    delivery = MemoryDeliverySystem()

    print("=" * 70)
    print("CIRCLEBACK-STYLE MEMORY PROCESSING DEMO")
    print("=" * 70)

    print("\n[WhatsApp Format]")
    print("-" * 40)
    print(delivery.format_for_whatsapp(memory))

    print("\n[Email Subject]")
    print("-" * 40)
    email_data = delivery.format_for_email(memory)
    print(email_data["subject"])

    print("\n[Plain Text Format]")
    print("-" * 40)
    print(delivery.format_for_text(memory)[:500] + "...")

    print("\n[Memory Object]")
    print("-" * 40)
    print(f"ID: {memory.id}")
    print(f"Participants: {memory.participants}")
    print(f"Topics: {memory.topics}")
    print(f"Action Items: {len(memory.action_items)}")
    print(f"Importance: {memory.importance}/5")
    print(f"Tags: {memory.tags}")


if __name__ == "__main__":
    demo_circleback_style()