from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4",
    streaming=True,  
    callbacks=[StreamingStdOutCallbackHandler()],
    timeout=30,  
    max_retries=2,  
    verbose=True  
)


prompt_template = ChatPromptTemplate.from_messages([
    ("system", """You are a booking assistant that helps users schedule appointments.
    Your responses should be:
    1. Concise and clear
    2. Focused on booking-related tasks
    3. Proactive in suggesting solutions
    4. Professional in tone
    
    {system_message}
    """),
    MessagesPlaceholder(variable_name="messages"),
    ("system", "Remember to validate all inputs and confirm details before making changes.")
])


llm_model = prompt_template | llm

# Error handling for production
def get_llm_response(messages, system_message=""):
    try:
        return llm_model.invoke({
            "messages": messages,
            "system_message": system_message
        })
    except Exception as e:
        print(f"Error in LLM response: {str(e)}")
        return None