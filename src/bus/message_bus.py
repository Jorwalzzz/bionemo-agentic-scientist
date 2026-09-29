"""
Agentic BioNeMo - Asynchronous Swarm Message Bus
Manages inter-agent communication, topic routing, debate history, and real-time streaming hooks.
"""
from typing import Callable, List, Dict, Any, Optional
import time
from datetime import datetime
from src.models import CouncilMessage

class SwarmMessageBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[CouncilMessage], None]]] = {}
        self.global_listeners: List[Callable[[CouncilMessage], None]] = []
        self.history: List[CouncilMessage] = []
        self.active_vetoes: List[CouncilMessage] = []
        self.clearances: List[CouncilMessage] = []

    def subscribe(self, topic: str, callback: Callable[[CouncilMessage], None]):
        """Subscribe to a specific message intent/topic."""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)

    def add_global_listener(self, callback: Callable[[CouncilMessage], None]):
        """Subscribe to all messages published across the entire swarm."""
        self.global_listeners.append(callback)

    def publish(
        self,
        agent_id: str,
        persona_name: str,
        avatar: str,
        intent: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CouncilMessage:
        """Publish a structured council message to the swarm."""
        now_str = datetime.now().strftime("%H:%M:%S")
        msg = CouncilMessage(
            agent_id=agent_id,
            persona_name=persona_name,
            avatar=avatar,
            intent=intent,
            content=content,
            metadata=metadata or {},
            timestamp=time.time(),
            timestamp_str=now_str
        )
        
        self.history.append(msg)
        
        if intent == "VETO":
            self.active_vetoes.append(msg)
        elif intent == "CLEARANCE":
            self.clearances.append(msg)

        # Notify topic-specific subscribers
        if intent in self.subscribers:
            for cb in self.subscribers[intent]:
                try:
                    cb(msg)
                except Exception as e:
                    print(f"Error in subscriber callback for {intent}: {e}")

        # Notify global listeners (e.g. UI WebSocket / SSE stream)
        for g_cb in self.global_listeners:
            try:
                g_cb(msg)
            except Exception as e:
                print(f"Error in global listener callback: {e}")

        return msg

    def get_council_summary(self) -> Dict[str, Any]:
        """Returns consolidated council statistics."""
        return {
            "total_messages": len(self.history),
            "veto_count": len(self.active_vetoes),
            "clearance_count": len(self.clearances),
            "last_action": self.history[-1].intent if self.history else "IDLE",
            "recent_dialogues": [
                {
                    "agent_id": m.agent_id,
                    "persona": m.persona_name,
                    "avatar": m.avatar,
                    "intent": m.intent,
                    "content": m.content,
                    "time": m.timestamp_str
                }
                for m in self.history[-12:]
            ]
        }

    def clear(self):
        """Reset the message bus for a new campaign."""
        self.history.clear()
        self.active_vetoes.clear()
        self.clearances.clear()
