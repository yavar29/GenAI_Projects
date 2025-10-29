import json
from openai import OpenAI
from app.core.prompts import build_system_prompt
from app.core.personas import persona_manager
from app.tools import record_user_details, record_unknown_question, kb_search

class Assistant:
    def __init__(self, name: str, summary_text: str, linkedin_text: str, model: str, persona: str = "professional"):
        self.client = OpenAI()
        self.name = name
        self.model = model
        self.summary_text = summary_text
        self.linkedin_text = linkedin_text
        self.current_persona = persona
        self.system_prompt = self._build_system_prompt(persona)
        self.tools = [
            {"type": "function", "function": record_user_details.schema},
            {"type": "function", "function": record_unknown_question.schema},
            {"type": "function", "function": kb_search.schema},
        ]
    
    def _build_system_prompt(self, persona: str) -> str:
        """Build system prompt for the specified persona"""
        return persona_manager.build_system_prompt(
            persona, self.name, self.summary_text, self.linkedin_text
        )
    
    def switch_persona(self, persona: str):
        """Switch to a different persona"""
        self.current_persona = persona
        self.system_prompt = self._build_system_prompt(persona)
        print(f"[Assistant] Switched to {persona} persona")
    
    def get_current_persona_info(self):
        """Get information about the current persona"""
        return persona_manager.get_persona(self.current_persona)

    def _handle_tool_calls(self, tool_calls):
        msgs = []
        for tc in tool_calls:
            tool_name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            if tool_name == record_user_details.schema["name"]:
                res = record_user_details.record_user_details(**args)
            elif tool_name == record_unknown_question.schema["name"]:
                res = record_unknown_question.record_unknown_question(**args)
            elif tool_name == kb_search.schema["name"]:
                res = kb_search.kb_search(**args)
            else:
                res = {"error": f"Unknown tool {tool_name}"}
            msgs.append({"role": "tool", "content": json.dumps(res), "tool_call_id": tc.id})
        return msgs

    def chat(self, message: str, history: list[dict]):
        messages = [{"role": "system", "content": self.system_prompt}] + history + [{"role": "user", "content": message}]
        
        # Enhanced search strategy - try multiple approaches
        search_attempts = 0
        max_search_attempts = 3
        
        while True:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                temperature=0.2
            )
            choice = resp.choices[0]
            
            if choice.finish_reason == "tool_calls":
                tool_msgs = self._handle_tool_calls(choice.message.tool_calls)
                messages.append(choice.message)
                messages.extend(tool_msgs)
                
                # Check if we got good search results, if not, try alternative search
                search_attempts += 1
                if search_attempts < max_search_attempts:
                    # Check if the search results are sufficient
                    last_tool_msg = tool_msgs[-1] if tool_msgs else None
                    if last_tool_msg and "kb_search" in last_tool_msg.get("content", ""):
                        try:
                            import json
                            tool_result = json.loads(last_tool_msg["content"])
                            matches = tool_result.get("matches", [])
                            if not matches or (matches and all(match.get("score", 0) < 0.7 for match in matches)):
                                # Add a message to try alternative search
                                messages.append({
                                    "role": "assistant", 
                                    "content": "The search didn't find relevant information. Let me try a different search approach."
                                })
                                continue
                        except:
                            pass
                
                continue
            return choice.message.content
