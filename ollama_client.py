"""
M.E.R.C.Y Ollama Client
Handles AI model communication with conversation history - ASYNC VERSION
"""
import aiohttp
import asyncio
import json
from typing import List, Dict, Optional
from bot_config import OLLAMA_URL, MODEL_NAME

class OllamaClient:
    """Async client for communicating with Ollama AI model"""

    def __init__(self, model: str = MODEL_NAME, timeout: int = 120):
        self.model = model
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.conversation_history: Dict[int, List[Dict]] = {}

    def get_conversation(self, user_id: int) -> List[Dict]:
        """Get conversation history for user"""
        return self.conversation_history.get(user_id, [])

    def add_to_conversation(self, user_id: int, role: str, content: str):
        """Add message to conversation history"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []

        self.conversation_history[user_id].append({
            "role": role,
            "content": content
        })

        # Keep only last 10 messages for context (reduced from higher limits)
        if len(self.conversation_history[user_id]) > 10:
            self.conversation_history[user_id] = self.conversation_history[user_id][-10:]

    def clear_conversation(self, user_id: int):
        """Clear conversation history"""
        if user_id in self.conversation_history:
            self.conversation_history[user_id] = []

    async def generate_response(self, user_id: int, message: str, system_prompt: str) -> Optional[str]:
        """Generate AI response with conversation context - ASYNC"""
        try:
            # Build messages array with system prompt and history
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history
            history = self.get_conversation(user_id)
            messages.extend(history)

            # Add current message
            messages.append({"role": "user", "content": message})

            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "num_predict": 500,  # REDUCED from 2000 for faster responses
                    "num_ctx": 4096,     # Context window size
                    "top_k": 40,
                    "top_p": 0.9
                }
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(OLLAMA_URL, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        bot_response = result.get("message", {}).get("content", "")

                        # Save to conversation history
                        self.add_to_conversation(user_id, "user", message)
                        self.add_to_conversation(user_id, "assistant", bot_response)

                        return bot_response
                    else:
                        error_text = await response.text()
                        return f"Sorry, I got a {response.status} error. Let me try again?"

        except aiohttp.ClientConnectorError:
            return "I can't reach my brain right now! Is Ollama running? Try: ollama serve"
        except asyncio.TimeoutError:
            return "I'm taking too long to think... maybe we should talk about something simpler?"
        except Exception as e:
            return f"Oops! Something went wrong: {str(e)}"

    async def generate_with_memory(self, user_id: int, message: str, system_prompt: str,
                            memory_context: str = "") -> Optional[str]:
        """Generate response with memory context - ASYNC"""
        enhanced_prompt = system_prompt

        if memory_context:
            enhanced_prompt += f"\n\nCONTEXT ABOUT YOUR FRIEND:\n{memory_context}"

        return await self.generate_response(user_id, message, enhanced_prompt)
