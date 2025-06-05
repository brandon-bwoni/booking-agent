from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from tools import create_and_save_booking, read_slots_tool, update_booking_tool

from llm.llm import llm_model
from llm.context_manager import trim_messages

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
agent_tools = {
    "create_booking": tool(create_and_save_booking),
    "check_availability": tool(read_slots_tool),
    "update_booking": tool(update_booking_tool)
}

model = llm_model.bind_tools(agent_tools)

async def booking_agent(state: AgentState) -> AgentState:
    """
    Booking agent that handles appointment scheduling and management.
    """
    # System message with detailed booking capabilities
    system_message = SystemMessage(content="""You are an intelligent booking assistant designed to help users schedule and manage appointments efficiently. 

    Tools available:
    1. create_booking(user_id: str, description: str, parsed_time: str) -> Creates new bookings
    2. check_availability(provider_id: str, requested_time: datetime) -> Checks slot availability
    3. update_booking(booking_id: str, status: str, new_time: Optional[datetime], reason: Optional[str]) -> Updates bookings

    Process Steps:
    1. For new bookings:
      - Ask for preferred date/time
      - Use check_availability to verify slot
      - Get user_id and description
      - Confirm all details with user
      - Use create_booking to finalize

    2. For updates:
      - Get booking_id from user
      - For rescheduling: check_availability first
      - Use update_booking with appropriate status
      - Confirm changes with user

    Validation Rules:
      - Description must be 10-500 characters
      - Times must be in ISO format
      - Valid statuses: PENDING, CONFIRMED, CANCELLED, RESCHEDULED

    Always:
      - Be concise and clear
      - Proactively check for conflicts
      - Suggest alternatives for unavailable slots
      - Confirm all actions before execution
      """)

    # Trim messages to fit context window
    state["messages"] = trim_messages(state["messages"], max_tokens=4000)
  
    # Initial greeting for new conversations
    if not state["messages"]:
        return {"messages": [
            system_message,
            AIMessage(content="Hello! I'm your booking assistant. How may I assist you today?")
        ]}

    # Prepare conversation history
    all_messages = [system_message] + list(state["messages"])
    
    # Get model response
    response = await model.invoke(all_messages)

    # Handle tool calls
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_names = [tc.name for tc in response.tool_calls]
        print(f"🔧 Using tools: {', '.join(tool_names)}")
        
        # Execute tools and get results
        tool_results = []
        for tool_call in response.tool_calls:
            if tool_call.name in agent_tools:
                result = agent_tools[tool_call.name](**tool_call.args)
                tool_results.append(ToolMessage(
                    tool_call_id=tool_call.id,
                    content=str(result)
                ))

        # Add tool results to conversation
        return {"messages": list(state["messages"]) + [response] + tool_results}

    # Return updated conversation state
    return {"messages": list(state["messages"]) + [response]}

def should_continue(state: AgentState) -> str:
    """
    Check if we should end the conversation based on booking completion or user request.
    
    Returns:
        str: "continue" to keep conversation going, "end" to terminate
    """
    messages = state["messages"]
    if not messages:
        return "continue"
    
    # Check the most recent messages
    for message in reversed(messages):
        # End if booking was successfully created
        if (isinstance(message, ToolMessage) and
            any(success_indicator in message.content.lower() 
                for success_indicator in ["booking confirmed", "successfully saved", "booking id"])
           ):
            return "end"
        
        # End if booking was cancelled/rescheduled
        if (isinstance(message, ToolMessage) and
            any(update_indicator in message.content.lower()
                for update_indicator in ["cancelled", "rescheduled", "updated to"])
           ):
            return "end"
        
        # End if user explicitly wants to end
        if (isinstance(message, HumanMessage) and
            any(exit_phrase in message.content.lower()
                for exit_phrase in ["goodbye", "thank you", "that's all", "exit"])
           ):
            return "end"
    
    return "continue"

# Update the graph to use the should_continue function
graph_builder = StateGraph(AgentState)
graph_builder.add_node("booking_agent", booking_agent)
graph_builder.add_edge(START, "booking_agent")
graph_builder.add_conditional_edges(
    "booking_agent",
    should_continue,
    {
        "continue": "booking_agent",
        "end": END
    }
)

graph = graph_builder.compile(checkpointer=MemorySaver())