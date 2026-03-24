from realtime_phone_agents.agent.fastrtc_agent import FastRTCAgent
from realtime_phone_agents.agent.tools.property_search import search_hotel_kb_tool
from realtime_phone_agents.infrastructure.superlinked.service import get_knowledge_search_service

get_knowledge_search_service()

agent = FastRTCAgent(
    tools=[search_hotel_kb_tool],
)

agent.stream.ui.launch()
