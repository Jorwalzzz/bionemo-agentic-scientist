"""
Unit tests for the Swarm Message Bus and Agent Council Protocol.
"""
from src.bus.message_bus import SwarmMessageBus
from src.models import CouncilMessage

def test_publish_and_subscribe_topic():
    bus = SwarmMessageBus()
    received_vetoes = []

    def on_veto(msg: CouncilMessage):
        received_vetoes.append(msg)

    bus.subscribe("VETO", on_veto)

    bus.publish("critic", "Dr. Marcus", "⚖️", "CLEARANCE", "Molecule approved")
    assert len(received_vetoes) == 0

    bus.publish("critic", "Dr. Marcus", "⚖️", "VETO", "Flagged for toxicity", {"molecule": "MOL-1"})
    assert len(received_vetoes) == 1
    assert received_vetoes[0].metadata["molecule"] == "MOL-1"
    assert len(bus.active_vetoes) == 1

def test_global_listener_and_summary():
    bus = SwarmMessageBus()
    all_msgs = []

    bus.add_global_listener(lambda m: all_msgs.append(m))

    bus.publish("scout", "Dr. Cynthia", "🎯", "TARGET_RESOLVED", "Target ready")
    bus.publish("chemist", "Dr. Aris", "🧪", "PROPOSAL", "Generated 5 candidates")
    bus.publish("docker", "Dr. Elena", "⚡", "DOCKING_RESULT", "Affinity -10.1 kcal/mol")

    assert len(all_msgs) == 3
    summary = bus.get_council_summary()
    assert summary["total_messages"] == 3
    assert len(summary["recent_dialogues"]) == 3
